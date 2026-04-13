import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

#embedding için
from sentence_transformers import SentenceTransformer
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")


user_profile = {          #Anketten geliyor
    "relationship": "parent",
    "budget": 500,
    "occasion": "birthday",
    "interests": ["bebek", "çocuk", "giyim"],
    "preferred_colors": [],
    "optional_features": {}
}

########################## RULE - BASED ################################
WEIGHTS = {                        
    "budget_match": 3,
    "interest_match": 2,
    "color_match": 1,
    "popular_product": 1,
    "category_hierarchy": 3,   # NEW: Full category path matching
    "title_keyword": 2,        # NEW: Product title keyword matching
    "discount_bonus": 1,       # NEW: Discounted products get a bonus
    "tfidf_similarity": 5      #Değişebilir daha dengeli olması için belki 4 
}
#SKORLAMAK İÇİN FONKSİYON
def score_product(user, product):
    score = 0
    reasons = []

    # 1. Budget check
    if product["price"] <= user["budget"]:  #User'dan nasıl alındığına göre değişebilir 
        score += WEIGHTS["budget_match"]
        reasons.append("within budget")
    else:
        return -1, ["over budget"]

    # 2. Interest match (set intersection on tags)
    user_interests = set(user.get("interests", []))
    product_tags = set(product.get("tags", []))

    matches = user_interests & product_tags
    if matches:
        score += len(matches) * WEIGHTS["interest_match"]
        reasons.append(f"matches interests: {', '.join(list(matches)[:3])}")

    # 2.5 Category hierarchy depth-weighted matching
    # The full category path is now injected into the product (e.g. "süpermarket > kahve çay > Filtre Kahve")
    # We check each level: leaf match = 3pts, sub match = 2pts, main match = 1pt
    category_path = product.get("category", "").lower()
    category_match_found = False
    for interest in user_interests:
        if interest in category_path:
            # Check depth: if it matches the last segment (leaf), give max points
            path_segments = [s.strip() for s in category_path.split(">")]
            if len(path_segments) >= 3 and interest in path_segments[-1].lower():
                score += WEIGHTS["category_hierarchy"]  # Leaf match = full bonus
                reasons.append(f"leaf category match: {interest}")
            elif len(path_segments) >= 2 and interest in path_segments[-2].lower():
                score += WEIGHTS["category_hierarchy"] - 1  # Sub match
                reasons.append(f"sub-category match: {interest}")
            else:
                score += 1  # Main category match = minimal
                reasons.append(f"main category match: {interest}")
            category_match_found = True
            break
    
    # 2.7 Title keyword matching - direct word matching against product name
    if not category_match_found:
        product_title_lower = product.get("title", "").lower()
        for interest in user_interests:
            if len(interest) > 3 and interest in product_title_lower:
                score += WEIGHTS["title_keyword"]
                reasons.append(f"title match: {interest}")
                break

    # 3. Color match (optional bonus)
    preferred_colors = set(c.lower() for c in user.get("preferred_colors", []))   
    product_color = product.get("attributes", {}).get("renk", "").lower()

    if product_color and product_color in preferred_colors:
        score += WEIGHTS["color_match"]
        reasons.append(f"matches color: {product_color}")
    
    # Also check if color keywords appear in product title or tags
    if preferred_colors and not product_color:
        title_lower = product.get("title", "").lower()
        tag_text = " ".join(product.get("tags", []))
        for color in preferred_colors:
            if color in title_lower or color in tag_text:
                score += WEIGHTS["color_match"]
                reasons.append(f"color in title: {color}")
                break

    # 4. Popularity bonus
    if product.get("popularity_score", 0) > 4:
        score += WEIGHTS["popular_product"]
        reasons.append("popular product")
    
    # 5. Discount bonus — products with significant discounts get priority
    discount = product.get("discount_pct", 0)
    if discount and discount > 20:
        score += WEIGHTS["discount_bonus"]
        reasons.append(f"discounted {int(discount)}%")

    return score, reasons

#TOP N = 5 ÜRÜN RECCOMENDLİYORUZ
def recommend_products(user, products, top_n=5):
    results = []

    for product in products:
        score, reasons = score_product(user, product)

        if score >= 0:       #UYMAYANLAR -1 ALDI 
            results.append({
                "product_id": product["product_id"],
                "title": product["title"],
                "price": product["price"],
                "score": score,
                "reasons": reasons
            })

    # skor'a göre sırala
    results.sort(key=lambda x: x["score"], reverse=True)

    return results[:top_n]


#TEXTLERDE SADECE STRINGLER VAR BUDGET , RANKING ETC. RULE-BASED LAYER'INDA 
def create_product_text(product):
    parts = []

    parts.append(product.get("title", ""))
    parts.append(product.get("category", ""))

    parts.extend(product.get("tags", []))
    parts.extend(product.get("relationship", []))
    parts.extend(product.get("occasion", []))

    for value in product.get("attributes", {}).values():
        parts.append(str(value))

    return " ".join(parts).lower()

def create_user_text(user):
    parts = []

    parts.extend(user.get("interests", []))
    parts.extend(user.get("preferred_colors", []))

    parts.append(user.get("relationship", ""))
    parts.append(user.get("occasion", ""))

    return " ".join(parts).lower()

def transform_product(row):        #ŞU ANLIK ELİMİZDE OLAN KOLONLARLA SADECE SONRA DEĞİŞEBİLİR PROJECT OBJESİNE ÇEVİRİYORUZ
    return {
        "product_id": row.name,
        "title": str(row.get("name", "")),
        "price": float(row.get("price_sale", 0)),
        "category": str(row.get("leaf_category", "")),
        "tags": [
            str(row.get("main_category", "")),
            str(row.get("sub_category", "")),
            str(row.get("leaf_category", "")),
            str(row.get("brand", ""))
        ],
        "attributes": {},
        "average_rating": float(row.get("rating", 0)) if pd.notna(row.get("rating", 0)) else 0.0,
        "rating_count": 0,
        "comment_count": int(row.get("review_count", 0)) if pd.notna(row.get("review_count", 0)) else 0,
        "popularity_score": float(row.get("rating", 0)) if pd.notna(row.get("rating", 0)) else 0.0,
        "relationship": [],
        "occasion": []
    }

############################ TF - IDF ##################################
def calculate_tfidf_similarity(user, products):
    user_text = create_user_text(user)
    product_texts = [create_product_text(product) for product in products]

    all_texts = [user_text] + product_texts

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(all_texts)

    user_vector = tfidf_matrix[0:1]
    product_vectors = tfidf_matrix[1:]

    similarities = cosine_similarity(user_vector, product_vectors)[0]

    return similarities

##Recommender hybrid## - RULE + EMBEDDING - 
def recommend_products_hybrid(user, products, top_n=5):
    results = []
    similarities = calculate_embedding_similarity(user, products)

    for product, sim in zip(products, similarities):
        rule_score, reasons = score_product(user, product)

        if rule_score >= 0:
            normalized_rule = float(rule_score / 10)
            embedding_score = float(sim)

            final_score = float(0.6 * normalized_rule + 0.4 * embedding_score)    ##to ensure balanced recommendations(we can change later)

            results.append({
                "product_id": product["product_id"],
                "title": product["title"],
                "price": product["price"],
                "_brand": product.get("_brand", ""),
                "_category_path": product.get("_category_path", ""),
                "rule_score": rule_score,
                "embedding_score": round(embedding_score, 3),
                "final_score": round(final_score, 3),
                "reasons": reasons
            })

    results.sort(key=lambda x: x["final_score"], reverse=True)
    
    # ===== DIVERSITY FILTER: Max 2 per brand AND max 2 per leaf category =====
    # Prevents 5x same brand (e.g., 5x Bofigo) AND 5x same category (e.g., 5x Parfüm)
    diverse_results = []
    brand_counts = {}
    category_counts = {}
    for r in results:
        # Brand check
        brand = r.get("_brand", "unknown") or "unknown"
        brand_key = str(brand).lower().strip()
        brand_counts[brand_key] = brand_counts.get(brand_key, 0) + 1
        if brand_counts[brand_key] > 2:
            continue
        
        # Category check — use the leaf category (last part of path)
        cat_path = r.get("_category_path", "")
        leaf_cat = cat_path.split(" > ")[-1].strip().lower() if " > " in str(cat_path) else str(cat_path).lower().strip()
        if leaf_cat:
            category_counts[leaf_cat] = category_counts.get(leaf_cat, 0) + 1
            if category_counts[leaf_cat] > 2:
                continue
        
        diverse_results.append(r)
        if len(diverse_results) >= top_n:
            break
    
    return diverse_results

############################## EMBEDDING ################################
def calculate_embedding_similarity(user, products):
    user_text = create_user_text(user)
    product_texts = [create_product_text(p) for p in products]

    user_embedding = embedding_model.encode([user_text])
    product_embeddings = embedding_model.encode(product_texts)

    similarities = cosine_similarity(user_embedding, product_embeddings)[0]

    return similarities

if __name__ == "__main__":
    import psycopg2
    import os

    # Database connection settings matching the local docker configuration
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = "5432"
    DB_NAME = "gift_recommender"
    DB_USER = "gift_admin"
    DB_PASS = "secure_password_123"

    print("Connecting to live PostgreSQL Database...")
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS
    )

    # Fetch a subset of active items from DB avoiding locking all memory
    with conn.cursor() as cur:
        # Example: Fetching items that are somewhat popular or highly rated
        cur.execute("""
            SELECT p.id, p.name, p.price_sale, c.name, b.name, p.rating, p.review_count
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN brands b ON p.brand_id = b.id
            WHERE p.is_active = TRUE
            LIMIT 500;
        """)
        db_rows = cur.fetchall()

    conn.close()

    unique_products = []
    seen = set()

    for row in db_rows:
        pid, name, price, category, brand, rating, reviews = row
        key = (name, price)
        if key not in seen:
            seen.add(key)
            product = {
                "product_id": str(pid),
                "title": str(name),
                "price": float(price) if price else 0.0,
                "category": str(category or ""),
                "tags": [str(category or ""), str(brand or "")],
                "attributes": {},
                "average_rating": float(rating) if rating else 0.0,
                "rating_count": int(reviews) if reviews else 0,
                "popularity_score": float(rating) if rating else 0.0,
                "relationship": [],
                "occasion": []
            }
            unique_products.append(product)

    print(f"Loaded {len(unique_products)} live products from the database.")
    print("Processing Hybrid AI Score against rule bounds...")

    recommendations = recommend_products_hybrid(user_profile, unique_products)

    print("\n--- FINAL HYBRID GIFTS (SQL + RULES + AI) ---")
    for r in recommendations:
        print(f"Product: {r['title']} | Score: {r['final_score']} | Reason: {', '.join(r['reasons'])}")