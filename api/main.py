import psycopg2
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sys
import os

# Add scripts folder to path so we can import the friend's logic engine
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from recommender_engine import recommend_products_hybrid, embedding_model, create_user_text

app = FastAPI(title="Gift Recommender API", description="AI powered gift engine")

# CORS for frontend connectivity
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AI Embedding Configuration is handled directly inside recommender_engine.py now
print("Booting Gift Engine API...")

# PostgreSQL Connection settings
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = "5432"
DB_NAME = "gift_recommender"
DB_USER = "gift_admin"
DB_PASS = "secure_password_123"

def get_db():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS
    )

# ===== PRE-COMPUTED CATEGORY HIERARCHY CACHE =====
# This runs ONCE at server startup, materializing the recursive tree into a Python dict.
# Eliminates the need for expensive per-request recursive CTEs.
CATEGORY_CACHE = {}  # {category_id: {"full_path": "Main > Sub > Leaf", "path_parts": ["Main", "Sub", "Leaf"]}}

def build_category_cache():
    """Walk the category parent_id tree once and cache full paths."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, name, parent_id FROM categories")
        rows = cur.fetchall()
        conn.close()
        
        # Build adjacency map
        nodes = {}
        for cid, name, parent_id in rows:
            nodes[str(cid)] = {"name": name, "parent_id": str(parent_id) if parent_id else None}
        
        # Walk up the tree for each node to build full paths
        cache = {}
        for cid, node in nodes.items():
            parts = [node["name"]]
            current = node
            while current["parent_id"] and current["parent_id"] in nodes:
                current = nodes[current["parent_id"]]
                parts.insert(0, current["name"])
            cache[cid] = {
                "full_path": " > ".join(parts),
                "path_parts": parts
            }
        
        print(f"Category cache built: {len(cache)} categories with full hierarchy paths.")
        return cache
    except Exception as e:
        print(f"Warning: Could not build category cache: {e}")
        return {}

CATEGORY_CACHE = build_category_cache()

from typing import List, Optional, Dict, Any

# Models
class RecommendRequest(BaseModel):
    answers: Dict[str, Any]
    budget: Optional[float] = None

def parse_questions_md():
    questions = []
    current_q = None
    
    questions_path = os.path.join(os.path.dirname(__file__), "..", "docs", "questions.md")
    with open(questions_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("## Soru"):
                if current_q:
                    questions.append(current_q)
                title = line.split(":", 1)[-1].strip() if ":" in line else line.replace("## Soru", "").strip()
                # Basic ID generation based on the title
                q_id = "".join(e for e in title.split("(")[0] if e.isalnum() or e.isspace()).strip().replace(" ", "_").lower()
                current_q = {
                    "id": q_id,
                    "title": title,
                    "options": []
                }
            elif line.startswith("- ") and current_q:
                current_q["options"].append(line[2:].strip())
                
    if current_q:
        questions.append(current_q)
        
    return questions

@app.get("/api/questions")
def get_questions():
    """Serves the interactive questionnaire UI directly from the BA's markdown file."""
    return parse_questions_md()


@app.post("/api/recommend")
def get_recommendations(req: RecommendRequest, limit: int = 10):
    """
    Ingests frontend answers, maps them to the friend's strict user_profile,
    pulls a large candidate pool from pgvector database, and executes 
    the rule-based categorization logic (recommender_engine.py).
    """
    import re
    
    # ===== BUDGET RESOLUTION =====
    # Extract BOTH lower and upper bounds from the price range
    # "2.500 - 5.000 TL" → budget_min=2500, budget_max=5000
    resolved_budget_min = 0
    resolved_budget_max = None
    
    # First: Check if any questionnaire answer contains a budget range
    for key, val in req.answers.items():
        v_str = str(val[0]) if isinstance(val, list) else str(val)
        cleaned = v_str.replace('.', '')  # Remove Turkish thousand separator dots
        
        # Match "500 - 1.000 TL", "2.500 - 5.000 TL" etc.
        budget_match = re.search(r'(\d+)\s*-\s*(\d+)\s*TL', cleaned)
        if budget_match:
            resolved_budget_min = float(budget_match.group(1))
            resolved_budget_max = float(budget_match.group(2))
            break
        # Handle "5.000 TL ve üzeri" — no upper limit
        budget_match2 = re.search(r'(\d+)\s*TL\s*ve\s*üzeri', cleaned)
        if budget_match2:
            resolved_budget_min = float(budget_match2.group(1))
            resolved_budget_max = 50000.0  # No real cap
            break
    
    # Slider value overrides the questionnaire — slider only sets upper bound
    if req.budget and req.budget > 0:
        resolved_budget_max = req.budget
        # If slider is used, keep min from questionnaire or default to 0
        if resolved_budget_min > resolved_budget_max:
            resolved_budget_min = 0
    
    # Final fallback
    if not resolved_budget_max:
        resolved_budget_max = 50000.0
    
    print(f"[BUDGET] Range: {resolved_budget_min} - {resolved_budget_max} TL (slider: {req.budget})")
    
    # 1. Map raw answers to explicit User Profile expected by recommender_engine
    user_profile = {
        "relationship": "",
        "budget": resolved_budget_max,
        "budget_min": resolved_budget_min,
        "occasion": "",
        "interests": [],
        "preferred_colors": [],
        "optional_features": {}
    }

    # Words that should ONLY set the relationship field, never enter interests
    # This prevents "anne" from matching "Anne Bebek Bakım Çantası" products
    RELATIONSHIP_WORDS = {"anne", "baba", "kardeş", "eş", "partner", "sevgili", 
                          "arkadaş", "patron", "yönetici", "öğretmen", "akademisyen",
                          "tanıdık", "kendime"}
    OCCASION_WORDS = {"doğum günü", "yıl dönümü", "sevgililer günü", "anneler günü",
                      "babalar günü", "yılbaşı", "mezuniyet", "yeni ev", "geçmiş olsun",
                      "özür dileme", "içimden geldi"}

    # Extract all Algoritma tags into interests to feed the categorization logic bonus
    for key, val in req.answers.items():
        if isinstance(val, list):
            vals = val
        else:
            vals = [val]
            
        for v in vals:
            v_lower = str(v).lower()
            
            # SKIP budget answers — they pollute interests with "tl", "500" etc.
            if re.search(r'\d+\s*-\s*\d+\s*tl', v_lower) or 'tl ve üzeri' in v_lower:
                continue
            
            # Check if this is a relationship answer — set relationship but DON'T add to interests
            is_relationship = any(rw in v_lower for rw in RELATIONSHIP_WORDS)
            if is_relationship:
                user_profile["relationship"] = v
            
            # Check if this is an occasion answer
            is_occasion = any(ow in v_lower for ow in OCCASION_WORDS)
            if is_occasion:
                user_profile["occasion"] = v
                
            # If the user selected colors (Soru 7)
            if "siyah" in v_lower or "gri" in v_lower or "antrasit" in v_lower:
                user_profile["preferred_colors"].extend(["siyah", "gri"])
            if "sarı" in v_lower or "neon" in v_lower or "kırmızı" in v_lower:
                user_profile["preferred_colors"].extend(["sarı", "kırmızı", "neon"])
            if "pastel" in v_lower or "lila" in v_lower or "pembe" in v_lower:
                user_profile["preferred_colors"].extend(["pembe", "lila", "soft"])
            if "toprak" in v_lower or "ahşap" in v_lower:
                user_profile["preferred_colors"].extend(["kahverengi", "ahşap", "doğal"])

            # Map the AI Algorithm tags explicitly mapped in questions.md
            match = re.search(r'\(Algoritma:\s*(.*?)\)', v)
            if match:
                tags = [t.strip().lower() for t in match.group(1).split(',')]
                user_profile["interests"].extend(tags)
            elif not is_relationship and not is_occasion:
                # Only add generic words if they're NOT relationship/occasion answers
                clean_v = re.sub(r'\(.*?\)', '', v).strip().lower()
                if len(clean_v) > 2:
                    user_profile["interests"].append(clean_v)

    # Convert the rigorously built user_profile into a sentence for AI postgres pre-filtering
    user_text = create_user_text(user_profile)
    prompt_embedding = embedding_model.encode([user_text])[0].tolist()

    try:
        conn = get_db()
        with conn.cursor() as cur:
            # ===== STAGE 1: Simple flat query — category hierarchy is resolved via CATEGORY_CACHE =====
            query = """
                SELECT 
                    p.id, 
                    p.name AS title, 
                    p.price_sale AS price, 
                    p.category_id,
                    b.name AS brand, 
                    p.rating, 
                    p.review_count,
                    p.photo_url,
                    p.product_url,
                    p.discount_pct
                FROM products p
                JOIN product_embeddings pe ON p.id = pe.product_id
                LEFT JOIN brands b ON p.brand_id = b.id
                WHERE p.is_active = TRUE
            """
            params = []

            # Apply BOTH lower and upper budget constraints from the price range
            if resolved_budget_max and resolved_budget_max < 50000:
                query = query + " AND p.price_sale <= %s "
                params.append(resolved_budget_max)
            if resolved_budget_min and resolved_budget_min > 0:
                query = query + " AND p.price_sale >= %s "
                params.append(resolved_budget_min)
                
            # ===== STAGE 2: ILIKE keyword priority boost =====
            order_cases = []
            interests_list = user_profile.get("interests", []) or []
            
            for word in interests_list:
                str_word = str(word)
                if len(str_word) > 3:
                    clean_word = str_word.replace("'", "")
                    order_cases.append(f"p.name ILIKE '%%{clean_word}%%'")
                    
            if len(order_cases) > 0:
                case_stmt = " + ".join([f"(CASE WHEN {c} THEN 1.0 ELSE 0.0 END)" for c in order_cases])
                sql_addition = f" ORDER BY ({case_stmt}) DESC, pe.embedding <=> %s::vector LIMIT 800;"
                query = query + sql_addition
            else:
                query = query + " ORDER BY pe.embedding <=> %s::vector LIMIT 800;"

            params.append(str(prompt_embedding))

            cur.execute(query, tuple(params))
            db_rows = cur.fetchall()

        conn.close()

        # ===== STAGE 3: Transform with CACHED category hierarchy =====
        unique_products = []
        seen = set()

        for row in db_rows:
            pid, title, price, category_id, brand, rating, reviews, photo, url, discount = row
            key = (title, price)
            if key not in seen:
                seen.add(key)
                
                # Look up the full category tree from the pre-computed cache
                cat_info = CATEGORY_CACHE.get(str(category_id), {})
                category_path = cat_info.get("full_path", "")
                category_parts = cat_info.get("path_parts", [])
                
                # Inject ALL levels of the category hierarchy into tags
                tags = []
                for part in category_parts:
                    tags.append(str(part).lower())
                if brand: 
                    tags.append(str(brand).lower())
                # Add individual words from the product title for deeper matching
                if title:
                    for word in str(title).lower().split():
                        if len(word) > 3:
                            tags.append(word)
                
                unique_products.append({
                    "product_id": str(pid),
                    "title": str(title),
                    "price": float(price) if price else 0.0,
                    "category": category_path,
                    "tags": tags,
                    "attributes": {},
                    "average_rating": float(rating) if rating else 0.0,
                    "rating_count": int(reviews) if reviews else 0,
                    "popularity_score": float(rating) if rating else 0.0,
                    "discount_pct": float(discount) if discount else 0.0,
                    "relationship": [],
                    "occasion": [],
                    "_photo_url": photo,
                    "_product_url": url,
                    "_brand": brand,
                    "_category_path": category_path
                })

        # 4. Execute the actual Custom Hybrid Script!
        print(f"Passing {len(unique_products)} Candidate Products & Profile: {user_profile} to Custom Engine.")
        eng_recommendations = recommend_products_hybrid(user_profile, unique_products, top_n=limit)

        # 5. Format the results back strictly to what the Frontend expects
        final_results = []
        for r in eng_recommendations:
            # Find the original object to get our frontend metadata back
            orig = next((item for item in unique_products if item["product_id"] == r["product_id"]), None)
            
            # Build rich Turkish rationale from the friend's English reason tags
            reasons = r.get("reasons", [])
            tr_parts = []
            for reason in reasons:
                rl = reason.lower()
                if "within budget" in rl:
                    tr_parts.append("💰 Bütçene uygun")
                elif "matches interest" in rl or "category match" in rl:
                    tr_parts.append("🎯 İlgi alanlarıyla eşleşiyor")
                elif "matches color" in rl:
                    tr_parts.append("🎨 Renk tercihine uygun")
                elif "popular" in rl:
                    tr_parts.append("⭐ Popüler ve yüksek puanlı")
                else:
                    tr_parts.append(f"✓ {reason}")
            
            score_val = r.get("final_score", 0)
            if score_val > 0.6:
                tr_parts.insert(0, "🔥 Yüksek eşleşme")
            
            rationale_text = " · ".join(tr_parts) if tr_parts else "AI analiz sonucu önerildi"
            
            final_results.append({
                "product_id": r["product_id"],
                "title": r["title"],
                "price": r["price"],
                "brand": orig["_brand"] if orig else 'Premium Partner',
                "category": orig["category"] if orig else '',
                "photo_url": orig["_photo_url"] if orig else '',
                "product_url": orig["_product_url"] if orig else '#',
                "score": score_val,
                "rationale": rationale_text
            })

        return {"status": "success", "recommendations": final_results}

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
