import psycopg2
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sys
import os

# Add scripts folder to path so we can import the enhanced recommender engine
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from recommender_engine import (
    recommend_products_hybrid, 
    embedding_model, 
    create_user_text,
    build_enriched_user_profile  # NEW: Profile enrichment
)

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
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "gift_recommender")
DB_USER = os.getenv("DB_USER", "gift_admin")
DB_PASS = os.getenv("DB_PASS", "secure_password_123")

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
    Enhanced endpoint using build_enriched_user_profile:
    - Relationship-aware scoring
    - Personality & lifestyle matching
    - Confidence scores
    - Rich Turkish explanations
    """
    import re
    
    print(f"\n🎯 Processing recommendation request...")
    
    # 1. BUILD ENRICHED USER PROFILE (new v2 feature)
    user_profile = build_enriched_user_profile(req.answers)
    
    # Override budget with slider if provided
    if req.budget and req.budget > 0:
        user_profile["budget"] = req.budget
        if user_profile.get("budget_min", 0) > user_profile["budget"]:
            user_profile["budget_min"] = 0
    
    print(f"✓ User Profile Built:")
    print(f"  - Relationship: {user_profile.get('relationship', 'N/A')}")
    print(f"  - Budget: {user_profile.get('budget_min', 0)} - {user_profile.get('budget', 50000)} TL")
    print(f"  - Color Personality: {user_profile.get('color_personality', 'N/A')}")
    print(f"  - Lifestyle: {user_profile.get('lifestyle', 'N/A')}")
    print(f"  - Zodiac: {user_profile.get('zodiac', 'N/A')}")
    print(f"  - Interests: {user_profile.get('interests', [])[:5]}")
    print(f"  - Specific Needs: {user_profile.get('specific_needs', [])[:3]}")

    
    try:
        conn = get_db()
        with conn.cursor() as cur:
            # Build semantic text for database pre-filtering
            user_text = create_user_text(user_profile)
            prompt_embedding = embedding_model.encode([user_text])[0].tolist()
            
            # Query: Fetch candidates within budget with embedding pre-filter
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
            
            # Apply budget constraints
            budget_max = user_profile.get("budget", 50000)
            budget_min = user_profile.get("budget_min", 0)
            
            if budget_max and budget_max < 50000:
                query += " AND p.price_sale <= %s"
                params.append(budget_max)
            if budget_min and budget_min > 0:
                query += " AND p.price_sale >= %s"
                params.append(budget_min)
            
            # Keyword priority boost for interests
            interests_list = user_profile.get("interests", []) or []
            order_cases = []
            
            for word in interests_list[:8]:  # Limit to top 8 to avoid huge query
                str_word = str(word)
                if len(str_word) > 2:
                    clean_word = str_word.replace("'", "").lower()
                    order_cases.append(f"p.name ILIKE '%%{clean_word}%%'")
            
            if len(order_cases) > 0:
                case_stmt = " + ".join([f"(CASE WHEN {c} THEN 1.0 ELSE 0.0 END)" for c in order_cases])
                sql_addition = f" ORDER BY ({case_stmt}) DESC, pe.embedding <=> %s::vector LIMIT 1000"
                query = query + sql_addition
            else:
                query = query + " ORDER BY pe.embedding <=> %s::vector LIMIT 1000"
            
            params.append(str(prompt_embedding))
            
            cur.execute(query, tuple(params))
            db_rows = cur.fetchall()
            
            print(f"✓ Fetched {len(db_rows)} candidates from database")
        
        conn.close()
        
        # Transform database rows to product objects
        unique_products = []
        seen = set()
        
        for row in db_rows:
            pid, title, price, category_id, brand, rating, reviews, photo, url, discount = row
            key = (title, price)
            if key not in seen:
                seen.add(key)
                
                cat_info = CATEGORY_CACHE.get(str(category_id), {})
                category_path = cat_info.get("full_path", "")
                category_parts = cat_info.get("path_parts", [])
                
                tags = []
                for part in category_parts:
                    tags.append(str(part).lower())
                if brand:
                    tags.append(str(brand).lower())
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
        
        print(f"✓ Prepared {len(unique_products)} products")
        
        # Execute ENHANCED hybrid recommender
        print(f"🚀 Running enhanced hybrid recommender...")
        eng_recommendations = recommend_products_hybrid(user_profile, unique_products, top_n=limit)
        
        print(f"✓ Generated {len(eng_recommendations)} recommendations")
        
        # Format results with confidence scores and rich explanations
        final_results = []
        for r in eng_recommendations:
            orig = next((item for item in unique_products if item["product_id"] == r["product_id"]), None)
            
            # Build rich Turkish rationale
            reasons = r.get("reasons", [])
            rationale_text = " · ".join(reasons) if reasons else "AI analiz sonucu önerildi"
            
            confidence = r.get("confidence", 0.5)
            score = r.get("final_score", 0)
            
            final_results.append({
            "product_id": str(r["product_id"]),
            "title": str(r["title"]),
            "price": float(r["price"]),
            "brand": str(orig["_brand"]) if orig and orig["_brand"] else "Premium",
            "category": str(orig["category"]) if orig else "",
            "photo_url": str(orig["_photo_url"]) if orig and orig["_photo_url"] else "",
            "product_url": str(orig["_product_url"]) if orig and orig["_product_url"] else "#",
            "score": float(r.get("final_score", 0)),
            "confidence": float(r.get("confidence", 0.5)),
            "rationale": str(rationale_text),
            "metadata": {
                "rule_score": float(r.get("rule_score", 0)),
                "embedding_score": float(r.get("embedding_score", 0)),
                "reasons": [str(x) for x in reasons]
            }
        })
        
        print(f"✓ Formatted {len(final_results)} results\n")
        
        return {
            "status": "success",
            "recommendations": final_results,
            "profile_summary": {
                "relationship": user_profile.get("relationship", ""),
                "occasion": user_profile.get("occasion", ""),
                "budget": f"{user_profile.get('budget_min', 0):.0f} - {user_profile.get('budget', 50000):.0f} TL",
                "personality": user_profile.get("color_personality", ""),
                "lifestyle": user_profile.get("lifestyle", ""),
                "zodiac": user_profile.get("zodiac", "")
            }
        }
    
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
