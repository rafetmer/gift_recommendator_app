import psycopg2
from sentence_transformers import SentenceTransformer

import os

# Database connection settings
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = "5432"
DB_NAME = "gift_recommender"
DB_USER = "gift_admin"
DB_PASS = "secure_password_123"

# Same embedding model used during the ELT pipeline
MODEL_NAME = 'all-MiniLM-L6-v2'

class GiftRecommenderApp:
    def __init__(self):
        self.model = SentenceTransformer(MODEL_NAME)
        self.conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS
        )
        
    def get_recommendations(self, user_prompt, max_price=None, limit=5):
        """
        Given a user prompt like "I want a practical kitchen gift for my mom",
        this method produces an embedding and runs a Cosine Similarity Search in pgvector.
        """
        print(f"User Prompt: '{user_prompt}'")
        
        # 1. Convert user's text into the exact same 384-dimensional vector space
        prompt_embedding = self.model.encode([user_prompt])[0].tolist()
        
        with self.conn.cursor() as cur:
            # 2. Execute Hybrid Search
            # We compare the user's vector strictly against our product embeddings.
            # We also return the full category logic.
            
            query = """
                SELECT 
                    p.name, 
                    p.price_sale,
                    b.name as brand,
                    c.name as leaf_category,
                    1 - (pe.embedding <=> %s::vector) AS similarity_score
                FROM products p
                JOIN product_embeddings pe ON p.id = pe.product_id
                LEFT JOIN brands b ON p.brand_id = b.id
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.is_active = TRUE
            """
            
            params = [str(prompt_embedding)]
            
            # Apply hard SQL filters alongside the Soft AI Vector filter (Hybrid Search)
            if max_price:
                query += " AND p.price_sale <= %s"
                params.append(max_price)
                
            query += """
                ORDER BY pe.embedding <=> %s::vector
                LIMIT %s;
            """
            params.extend([str(prompt_embedding), limit])
            
            cur.execute(query, tuple(params))
            results = cur.fetchall()
            
            print("\n--- TOP GIFT RECOMMENDATIONS ---")
            for idx, r in enumerate(results, 1):
                name, price, brand, category, score = r
                print(f"{idx}. {name} | Brand: {brand} | Category: {category} | Price: {price} TL | Similarity: {score:.3f}")
                
        return results

    def close(self):
        self.conn.close()


if __name__ == "__main__":
    app = GiftRecommenderApp()
    
    # Example 1: Suggesting electronics
    app.get_recommendations("I need a technological device to freeze food. Deep freezer.", max_price=30000.0)
    
    print("\n")
    
    # Example 2: Suggesting apparel
    app.get_recommendations("Warm comfortable winter clothing", limit=3)
    
    app.close()
