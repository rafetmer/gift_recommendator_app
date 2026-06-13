import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Enhanced embedding model (Turkish support)
from sentence_transformers import SentenceTransformer
try:
    embedding_model = SentenceTransformer("distiluse-base-multilingual-v2")  # Turkish-optimized
    print("✓ Using Turkish-optimized embedding model: distiluse-base-multilingual-v2")
except Exception as e:
    print(f"⚠ Falling back to all-MiniLM-L6-v2: {e}")
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

########################## ENHANCED CONFIGURATION ##########################

# 1. Relationship-based weight multipliers (different rules for wife vs colleague vs boss)
RELATIONSHIP_WEIGHTS = {
    "sevgili": {
        "personal": 3.5,
        "luxury": 2.5,
        "trendy": 2.5,
        "romantic": 3.0,
        "practical": 0.5,
        "professional": 0.0,
        "price_flex": 1.2,  # Can go above budget
    },
    "anne": {
        "practical": 3.5,
        "home": 3.0,
        "comfort": 3.0,
        "luxury": 1.5,
        "personal": 1.5,
        "trendy": 0.8,
        "price_flex": 0.9,
    },
    "baba": {
        "tech": 3.0,
        "practical": 2.5,
        "quality": 2.5,
        "professional": 1.5,
        "luxury": 1.5,
        "trendy": 0.5,
        "price_flex": 1.1,
    },
    "sevgili_erkek": {
        "tech": 2.5,
        "practical": 2.5,
        "quality": 2.5,
        "sports": 2.0,
        "luxury": 2.0,
        "personal": 1.5,
        "price_flex": 1.2,
    },
    "arkadaş": {
        "trendy": 3.0,
        "fun": 3.0,
        "personal": 2.5,
        "luxury": 1.5,
        "practical": 1.0,
        "price_flex": 1.0,
    },
    "patron": {
        "professional": 3.5,
        "quality": 3.0,
        "luxury": 2.0,
        "practical": 1.5,
        "personal": 0.0,
        "trendy": 0.0,
        "price_flex": 0.8,  # Don't overspend on boss
    },
    "öğretmen": {
        "educational": 3.0,
        "practical": 2.5,
        "quality": 2.0,
        "personal": 1.0,
        "luxury": 1.0,
        "trendy": 0.5,
        "price_flex": 0.9,
    },
    "kendime": {
        "personal": 3.5,
        "quality": 3.0,
        "trendy": 2.5,
        "luxury": 2.5,
        "practical": 2.0,
        "price_flex": 1.3,  # Treat yourself!
    },
    "default": {
        "quality": 2.0,
        "practical": 1.5,
        "trendy": 1.5,
        "luxury": 1.0,
        "personal": 1.0,
        "price_flex": 1.0,
    }
}

# 2. Occasion-based boosts
OCCASION_BOOSTS = {
    "doğum günü": 1.5,
    "yıl dönümü": 1.6,
    "sevgililer günü": 2.0,
    "anneler günü": 1.4,
    "babalar günü": 1.4,
    "yılbaşı": 1.3,
    "mezuniyet": 1.5,
    "yeni ev": 1.4,
    "geçmiş olsun": 1.8,
    "özür dileme": 1.9,
    "içimden geldi": 1.0,
}

# 3. Personality/Lifestyle mapping (from Question 8)
LIFESTYLE_MAPPING = {
    "evden hiç çıkmadan": {
        "categories": ["battaniye", "kupa", "dizi", "film", "ev dekoru", "konfor"],
        "tags": ["comfort", "indoor", "cozy"],
        "boost": 0.8,
    },
    "doğada keşfe çıkmak": {
        "categories": ["outdoor", "kamp", "sırt çantası", "termos", "dağcılık"],
        "tags": ["adventure", "outdoor", "travel"],
        "boost": 0.8,
    },
    "uzun brunch": {
        "categories": ["moda", "aksesuar", "kozmetik", "çanta"],
        "tags": ["trendy", "social", "fashion"],
        "boost": 0.8,
    },
    "kitap okumak": {
        "categories": ["kitap", "kırtasiye", "ajanda", "sanat", "puzzle"],
        "tags": ["creative", "thoughtful", "hobby"],
        "boost": 0.8,
    },
}

# 4. Toxic trait mapping (from Question 9) - specific product needs
TOXIC_TRAIT_MAPPING = {
    "üşümesi": {
        "keywords": ["battaniye", "peluş", "kışlık", "ısıtıcı", "termal"],
        "boost": 1.5,
    },
    "telefon şarjı": {
        "keywords": ["powerbank", "şarj aleti", "kablo", "adapter", "teknoloji"],
        "boost": 1.5,
    },
    "organize": {
        "keywords": ["organizer", "ajanda", "planner", "düzenleyici", "kutular"],
        "boost": 1.5,
    },
    "kahve": {
        "keywords": ["kahve", "kupa", "french press", "espresso", "filtre", "kahveci"],
        "boost": 1.5,
    },
    "eşyalarını unutması": {
        "keywords": ["airtag", "tracker", "cüzdan", "çanta", "akıllı takip"],
        "boost": 1.5,
    },
    "nostalji": {
        "keywords": ["analog", "retro", "polaroid", "albüm", "çerçeve", "vintage"],
        "boost": 1.5,
    },
    "kulaklık": {
        "keywords": ["kulaklık", "ses sistemi", "müzik", "airpods", "headphones"],
        "boost": 1.5,
    },
    "gardırobu": {
        "keywords": ["moda", "çanta", "takı", "giyim", "elbise", "ayakkabı"],
        "boost": 1.5,
    },
}

# 5. Zodiac archetype boosts (from Question 10)
ZODIAC_MAPPING = {
    "koç": ["spor", "outdoor", "kırmızı", "enerji", "hareketli", "adventure"],
    "boğa": ["ev dekoru", "gurme", "mutfak", "parfüm", "lüks", "rahat", "quality"],
    "ikizler": ["kitap", "teknoloji", "seyahat", "oyun", "eğlence", "iletişim"],
    "yengeç": ["ev", "mutfak", "dekorasyon", "çerçeve", "nostalji", "duygusal"],
    "aslan": ["lüks", "altın", "takı", "moda", "kişisel bakım", "gösteriş"],
    "başak": ["ajanda", "kırtasiye", "düzen", "temizlik", "sağlık", "pratik"],
    "terazi": ["sanat", "moda", "kozmetik", "estetik", "parfüm", "zarif", "takı"],
    "akrep": ["siyah", "gizem", "mum", "psikoloji", "deri", "tutku", "enerjik"],
    "yay": ["seyahat", "kamp", "outdoor", "sırt çantası", "macera", "keşif"],
    "oğlak": ["saat", "iş", "klasik", "giyim", "bilgisayar", "aksesuar", "kaliteli"],
    "kova": ["teknoloji", "bilim kurgu", "akıllı cihazlar", "elektronik", "inovasyon"],
    "balık": ["sanat", "yaratıcılık", "müzik", "estetik", "ruh", "duygusal"],
}

# 6. Color personality profiles (from Question 7)
COLOR_PERSONALITY = {
    "cool": {  # Siyah / Gri / Antrasit
        "colors": ["siyah", "gri", "antrasit", "koyu mavi", "koyu yeşil"],
        "traits": ["minimalist", "teknolojik", "modern", "profesyonel"],
        "boost": 0.8,
    },
    "warm": {  # Toprak / Ahşap
        "colors": ["kahverengi", "ahşap", "doğal", "terrakotta", "krem"],
        "traits": ["doğal", "rustik", "sakin", "eklektik"],
        "boost": 0.8,
    },
    "vibrant": {  # Canlı Sarı / Neon / Kırmızı
        "colors": ["sarı", "neon", "kırmızı", "turuncu", "lime"],
        "traits": ["enerjik", "eğlenceli", "pop-art", "canlı", "iddialı"],
        "boost": 0.8,
    },
    "soft": {  # Pastel / Lila / Pembe
        "colors": ["pembe", "lila", "pastel", "lemon", "mint", "lavender"],
        "traits": ["soft", "romantik", "zarif", "estetik", "yumuşak"],
        "boost": 0.8,
    },
}

# 7. Core scoring weights
BASE_WEIGHTS = {
    "budget_match": 4,
    "interest_match": 3,
    "color_match": 2,
    "popular_product": 1,
    "category_hierarchy": 3,
    "title_keyword": 2,
    "discount_bonus": 1,
    "embedding_similarity": 5,  # Increased from 3
    "relationship_fit": 2,
    "occasion_fit": 2,
    "personality_fit": 2,
    "age_appropriateness": 1,
    "lifestyle_fit": 2,
}

########################## ENRICHED PROFILE BUILDER ##########################

def build_enriched_user_profile(raw_answers):
    """
    Transform raw questionnaire answers into a rich user profile
    with extracted personality, lifestyle, and specific product needs.
    """
    profile = {
        "relationship": "",
        "gender": "",
        "age_range": "",
        "occasion": "",
        "budget": 0,
        "budget_min": 0,
        
        # Core interests from Q6
        "interests": [],
        
        # Enriched signals
        "personality_colors": [],
        "color_personality": None,  # "cool", "warm", "vibrant", "soft"
        "lifestyle": None,  # from Q8
        "specific_needs": [],  # from Q9 toxic traits
        "zodiac": "",
        "zodiac_traits": [],
    }
    
    import re
    
    # Parse each answer
    for key, val in raw_answers.items():
        if isinstance(val, list):
            vals = val
        else:
            vals = [val]
        
        for v in vals:
            v_lower = str(v).lower()
            
            # Q1: Relationship
            if any(r in v_lower for r in ["anne", "baba", "kardeş", "eş", "partner", "sevgili", "arkadaş", "patron", "yönetici", "öğretmen"]):
                profile["relationship"] = v
            
            # Q2: Gender
            if "kadın" in v_lower:
                profile["gender"] = "kadın"
            elif "erkek" in v_lower:
                profile["gender"] = "erkek"
            elif "unisex" in v_lower or "belirtmek" in v_lower:
                profile["gender"] = "unisex"
            
            # Q3: Age range
            if any(age in v_lower for age in ["18 altı", "18-24", "25-34", "35-44", "45-54", "55-64", "65"]):
                profile["age_range"] = v
            
            # Q4: Occasion
            if any(occ in v_lower for occ in ["doğum günü", "yıl dönümü", "sevgililer", "anneler", "babalar", "yılbaşı", "mezuniyet", "yeni ev", "geçmiş olsun", "özür", "içimden"]):
                profile["occasion"] = v
                for key_occ, boost in OCCASION_BOOSTS.items():
                    if key_occ in v_lower:
                        profile["occasion_boost"] = boost
                        break
            
            # Q5: Budget
            budget_match = re.search(r'(\d+)\s*-\s*(\d+)\s*TL', v_lower)
            if budget_match:
                profile["budget_min"] = float(budget_match.group(1).replace(".", ""))
                profile["budget"] = float(budget_match.group(2).replace(".", ""))
            elif "üzeri" in v_lower:
                budget_match2 = re.search(r'(\d+)', v_lower)
                if budget_match2:
                    profile["budget_min"] = float(budget_match2.group(1).replace(".", ""))
                    profile["budget"] = 50000.0
            
            # Q6: Interests - extract algorithm tags
            algo_match = re.search(r'\(Algoritma:\s*(.*?)\)', v)
            if algo_match:
                tags = [t.strip().lower() for t in algo_match.group(1).split(',')]
                profile["interests"].extend(tags)
            elif not any(keyword in v_lower for keyword in ["hızlı", "doğa", "brunch", "kitap"]):
                clean_v = re.sub(r'\(.*?\)', '', v).strip().lower()
                if len(clean_v) > 2 and clean_v not in profile["interests"]:
                    profile["interests"].append(clean_v)
            
            # Q7: Color personality
            if "siyah" in v_lower or "gri" in v_lower or "antrasit" in v_lower:
                profile["color_personality"] = "cool"
                profile["personality_colors"] = ["siyah", "gri", "antrasit", "koyu mavi"]
            elif "toprak" in v_lower or "ahşap" in v_lower:
                profile["color_personality"] = "warm"
                profile["personality_colors"] = ["kahverengi", "ahşap", "terrakotta", "krem"]
            elif "sarı" in v_lower or "neon" in v_lower or "kırmızı" in v_lower:
                profile["color_personality"] = "vibrant"
                profile["personality_colors"] = ["sarı", "neon", "kırmızı", "turuncu"]
            elif "pastel" in v_lower or "lila" in v_lower or "pembe" in v_lower:
                profile["color_personality"] = "soft"
                profile["personality_colors"] = ["pembe", "lila", "pastel", "lavender"]
            
            # Q8: Lifestyle mapping
            for lifestyle_key, lifestyle_data in LIFESTYLE_MAPPING.items():
                if lifestyle_key in v_lower:
                    profile["lifestyle"] = lifestyle_key
                    profile["interests"].extend(lifestyle_data["categories"])
                    break
            
            # Q9: Toxic traits - extract specific needs
            for trait_key, trait_data in TOXIC_TRAIT_MAPPING.items():
                if trait_key in v_lower:
                    profile["specific_needs"].extend(trait_data["keywords"])
            
            # Q10: Zodiac
            for zodiac_key, zodiac_tags in ZODIAC_MAPPING.items():
                if zodiac_key in v_lower:
                    profile["zodiac"] = zodiac_key
                    profile["zodiac_traits"].extend(zodiac_tags)
                    profile["interests"].extend(zodiac_tags[:3])  # Add top 3 tags
                    break
    
    # Remove duplicates
    profile["interests"] = list(set(profile["interests"]))
    profile["specific_needs"] = list(set(profile["specific_needs"]))
    profile["zodiac_traits"] = list(set(profile["zodiac_traits"]))
    profile["personality_colors"] = list(set(profile["personality_colors"]))
    
    return profile

########################## ENHANCED SCORING ##########################

def get_relationship_weights(relationship_name):
    """Get dynamic weights based on relationship type."""
    rel_lower = str(relationship_name).lower()
    
    for key, weights in RELATIONSHIP_WEIGHTS.items():
        if key in rel_lower:
            return weights
    
    return RELATIONSHIP_WEIGHTS["default"]

def score_product_enhanced(user_profile, product, embedding_score):
    """
    Enhanced scoring with relationship context, personality, and confidence.
    
    Returns: (score, reasons, confidence)
    """
    score = 0
    reasons = []
    confidence = 0.5  # Start at 50% confidence
    
    # Get relationship-specific weights
    rel_weights = get_relationship_weights(user_profile.get("relationship", ""))
    
    # 1. BUDGET CHECK (most important)
    budget = user_profile.get("budget", 50000)
    budget_min = user_profile.get("budget_min", 0)
    product_price = product.get("price", 0)
    
    price_flex = rel_weights.get("price_flex", 1.0)
    
    if budget_min <= product_price <= (budget * price_flex):
        score += BASE_WEIGHTS["budget_match"]
        reasons.append("✓ Bütçede")
        confidence += 0.15
    else:
        return 0, ["✗ Bütçe dışı"], 0.1
    
    # 2. INTEREST MATCH (category + tags)
    user_interests = set(user_profile.get("interests", []))
    product_tags = set(product.get("tags", []))
    
    interest_matches = user_interests & product_tags
    if interest_matches:
        match_count = min(len(interest_matches), 3)  # Cap at 3 for scoring
        score += match_count * BASE_WEIGHTS["interest_match"]
        reasons.append(f"🎯 İlgi: {', '.join(list(interest_matches)[:2])}")
        confidence += 0.15
    
    # 3. CATEGORY HIERARCHY DEPTH
    category_path = product.get("category", "").lower()
    for interest in user_interests:
        if interest in category_path:
            path_segments = [s.strip() for s in category_path.split(">")]
            if len(path_segments) >= 3 and interest in path_segments[-1].lower():
                score += BASE_WEIGHTS["category_hierarchy"]
                reasons.append(f"📂 Kategori eşleşme")
                confidence += 0.10
                break
    
    # 4. SPECIFIC NEEDS (from toxic traits)
    specific_needs = set(user_profile.get("specific_needs", []))
    product_text = (product.get("title", "") + " " + category_path).lower()
    
    needs_found = 0
    for need in specific_needs:
        if need.lower() in product_text:
            needs_found += 1
    
    if needs_found > 0:
        score += needs_found * 1.5
        reasons.append(f"⚡ Spesifik ihtiyaç")
        confidence += 0.15
    
    # 5. PERSONALITY TRAITS (Zodiac)
    zodiac_traits = set(user_profile.get("zodiac_traits", []))
    if zodiac_traits & product_tags:
        score += 2
        reasons.append(f"♈ Burç uyumu")
        confidence += 0.08
    
    # 6. COLOR MATCH
    preferred_colors = set(user_profile.get("personality_colors", []))
    product_title_lower = product.get("title", "").lower()
    
    for color in preferred_colors:
        if color in product_title_lower or color in category_path:
            score += BASE_WEIGHTS["color_match"]
            reasons.append(f"🎨 Renk: {color}")
            confidence += 0.10
            break
    
    # 7. RELATIONSHIP CONTEXT BOOST
    rel = str(user_profile.get("relationship", "")).lower()
    for rel_key in RELATIONSHIP_WEIGHTS.keys():
        if rel_key in rel and rel_key != "default":
            # Check if product is appropriate for this relationship
            rel_weight_obj = RELATIONSHIP_WEIGHTS[rel_key]
            
            # Boost luxury products for romantic relationships
            if rel_key == "sevgili" and product.get("discount_pct", 0) < 20:
                score += 1
                confidence += 0.05
            
            # Boost practical for parents
            if rel_key in ["anne", "baba"] and "pratik" in product.get("tags", []):
                score += 1.5
                confidence += 0.07
            
            # Avoid personal for professional
            if rel_key == "patron" and "personal" in product.get("tags", []):
                return 0, ["✗ Patron için uygun değil"], 0.2
            
            break
    
    # 8. OCCASION BOOST
    occasion = str(user_profile.get("occasion", "")).lower()
    occasion_boost = user_profile.get("occasion_boost", 1.0)
    
    if occasion_boost > 1.0:
        score *= occasion_boost
        reasons.append(f"🎉 {occasion_boost:.1f}x " + occasion)
        confidence += 0.10
    
    # 9. POPULARITY
    if product.get("average_rating", 0) > 4.0:
        score += BASE_WEIGHTS["popular_product"]
        reasons.append("⭐ Popüler & yüksek puanlı")
        confidence += 0.08
    
    # 10. DISCOUNT
    discount = product.get("discount_pct", 0)
    if discount and discount > 20:
        score += BASE_WEIGHTS["discount_bonus"]
        reasons.append(f"💰 %{int(discount)} indirim")
    
    # 11. EMBEDDING SIMILARITY (semantic matching)
    embedding_weight = BASE_WEIGHTS["embedding_similarity"]
    score += embedding_score * embedding_weight
    if embedding_score > 0.7:
        confidence += 0.15
    elif embedding_score > 0.5:
        confidence += 0.08
    
    # Normalize confidence to 0-1
    confidence = min(confidence, 1.0)
    
    return score, reasons, confidence

########################## TEXT GENERATION ##########################

def create_product_text(product):
    """Create semantic text for embedding."""
    parts = []
    
    parts.append(product.get("title", ""))
    parts.append(product.get("category", ""))
    parts.extend(product.get("tags", []))
    parts.extend(product.get("relationship", []))
    parts.extend(product.get("occasion", []))
    
    for value in product.get("attributes", {}).values():
        parts.append(str(value))
    
    return " ".join(parts).lower()

def create_user_text(user_profile):
    """Create semantic text for user profile."""
    parts = []
    
    # Add all rich signals
    parts.extend(user_profile.get("interests", []))
    parts.extend(user_profile.get("personality_colors", []))
    parts.extend(user_profile.get("specific_needs", []))
    parts.extend(user_profile.get("zodiac_traits", []))
    
    parts.append(user_profile.get("relationship", ""))
    parts.append(user_profile.get("occasion", ""))
    parts.append(user_profile.get("lifestyle", ""))
    
    return " ".join(parts).lower()

########################## EMBEDDING SIMILARITY ##########################

def calculate_embedding_similarity(user_profile, products):
    """Calculate semantic similarity using embeddings."""
    user_text = create_user_text(user_profile)
    product_texts = [create_product_text(p) for p in products]
    
    try:
        user_embedding = embedding_model.encode([user_text])
        product_embeddings = embedding_model.encode(product_texts)
        
        similarities = cosine_similarity(user_embedding, product_embeddings)[0]
        return similarities
    except Exception as e:
        print(f"⚠ Embedding error: {e}, using TF-IDF fallback")
        return calculate_tfidf_similarity(user_profile, products)

########################## TFIDF FALLBACK ##########################

def calculate_tfidf_similarity(user_profile, products):
    """TF-IDF fallback for embedding failures."""
    user_text = create_user_text(user_profile)
    product_texts = [create_product_text(p) for p in products]
    
    all_texts = [user_text] + product_texts
    
    vectorizer = TfidfVectorizer(lowercase=True, stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(all_texts)
    
    user_vector = tfidf_matrix[0:1]
    product_vectors = tfidf_matrix[1:]
    
    similarities = cosine_similarity(user_vector, product_vectors)[0]
    
    return similarities

########################## HYBRID RECOMMENDER ##########################

def recommend_products_hybrid(user_profile, products, top_n=10):
    """
    Enhanced hybrid recommender with:
    - Relationship-aware weights
    - Personality/lifestyle matching
    - Confidence scores
    - Rich explanations
    """
    results = []
    
    # Calculate embedding similarities once
    similarities = calculate_embedding_similarity(user_profile, products)
    
    for product, embedding_sim in zip(products, similarities):
        # Get enhanced score with personality context
        rule_score, reasons, confidence = score_product_enhanced(
            user_profile, product, embedding_sim
        )
        
        if rule_score >= 0:
            # Normalize rule score for fair weighting
            normalized_rule = float(rule_score / 20)  # Adjusted normalization
            embedding_score = float(embedding_sim)
            
            # Better blending: more weight on semantic + confidence boost
            final_score = float(
                0.35 * normalized_rule +  # Rule-based (35%)
                0.45 * embedding_score +  # Semantic embedding (45%)
                0.20 * confidence         # Confidence boost (20%)
            )
            
            results.append({
                "product_id": product["product_id"],
                "title": product["title"],
                "price": product["price"],
                "_brand": product.get("_brand", ""),
                "_category_path": product.get("_category_path", ""),
                "rule_score": round(rule_score, 2),
                "embedding_score": round(embedding_score, 3),
                "confidence": round(confidence, 2),
                "final_score": round(final_score, 3),
                "reasons": reasons
            })
    
    results.sort(key=lambda x: x["final_score"], reverse=True)
    
    # ===== DIVERSITY FILTER =====
    diverse_results = []
    brand_counts = {}
    category_counts = {}
    
    for r in results:
        # Brand diversity (max 2 per brand)
        brand = r.get("_brand", "unknown") or "unknown"
        brand_key = str(brand).lower().strip()
        brand_counts[brand_key] = brand_counts.get(brand_key, 0) + 1
        if brand_counts[brand_key] > 2:
            continue
        
        # Category diversity (max 2 per leaf category)
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

########################## LEGACY SUPPORT ##########################

# Keep for backward compatibility
def recommend_products(user_profile, products, top_n=5):
    """Legacy function - redirects to hybrid."""
    return recommend_products_hybrid(user_profile, products, top_n)

if __name__ == "__main__":
    import psycopg2
    import os
    
    print("\n🚀 Enhanced Recommender Engine Started\n")
    
    # Test user profile
    raw_answers = {
        "relationship": ["Sevgili"],
        "gender": ["Kadın"],
        "age": ["25 - 34"],
        "occasion": ["Doğum Günü"],
        "budget": ["2.500 - 5.000 TL"],
        "interests": ["Moda & Giyim (Algoritma: giyim, çanta, ayakkabı, cüzdan, kemer, takı, aksesuar)"],
        "color": ["Pastel Tonlar / Lila / Pembe"],
        "sunday": ["Şık bir mekanda arkadaşlarıyla uzun brunchlar"],
        "toxic": ["Sürekli eşyalarını nereye koyduğunu unutması"],
        "zodiac": ["Terazi"],
    }
    
    enriched = build_enriched_user_profile(raw_answers)
    print("✓ Enriched User Profile:")
    for key, val in enriched.items():
        if val:
            print(f"  {key}: {val}")
    
    print("\n✓ Enhanced Recommender Engine Ready!")
    print(f"  - Embedding Model: {embedding_model.get_sentence_embedding_dimension()}-dim Turkish-optimized")
    print(f"  - Relationship Contexts: {len(RELATIONSHIP_WEIGHTS)}")
    print(f"  - Scoring Factors: {len(BASE_WEIGHTS)}")
