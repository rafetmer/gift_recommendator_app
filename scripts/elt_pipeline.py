import os
import glob
import uuid
import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from sentence_transformers import SentenceTransformer
from slugify import slugify

# Database connection settings
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = "5432"
DB_NAME = "gift_recommender"
DB_USER = "gift_admin"
DB_PASS = "secure_password_123"

# Model for embeddings (384 dimensions)
MODEL_NAME = 'all-MiniLM-L6-v2'
BATCH_SIZE = 100

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

def setup_database(conn):
    """Ensure our constraints are ready for upserts."""
    with conn.cursor() as cur:
        # We add a unique constraint on product_url to handle strict upserts safely
        cur.execute("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'unique_product_url'
                ) THEN
                    ALTER TABLE products ADD CONSTRAINT unique_product_url UNIQUE (product_url);
                END IF;
            END $$;
        """)
        conn.commit()

class ELTPipeline:
    def __init__(self):
        self.conn = get_db_connection()
        setup_database(self.conn)
        self.model = SentenceTransformer(MODEL_NAME)
        
        # In-memory caches to avoid hammering the DB for small lookup tables
        self.category_cache = {} # Map: slug -> id
        self.brand_cache = {}    # Map: slug -> id
        
        self.load_caches()

    def load_caches(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT slug, id FROM categories;")
            for slug, cat_id in cur.fetchall():
                self.category_cache[slug] = cat_id
                
            cur.execute("SELECT slug, id FROM brands;")
            for slug, brand_id in cur.fetchall():
                self.brand_cache[slug] = brand_id

    def get_or_create_category(self, name, parent_id=None, slug_prefix=""):
        if not name or pd.isna(name):
            return None, None
            
        base_slug = slugify(str(name))
        slug = f"{slug_prefix}-{base_slug}" if slug_prefix else base_slug
        
        if slug in self.category_cache:
            return self.category_cache[slug], slug
            
        # Create category
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO categories (parent_id, name, slug) VALUES (%s, %s, %s) ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name RETURNING id;",
                (parent_id, name, slug)
            )
            cat_id = cur.fetchone()[0]
            self.conn.commit()
            
        self.category_cache[slug] = cat_id
        return cat_id, slug

    def get_or_create_brand(self, name):
        if not name or pd.isna(name):
            return None
            
        slug = slugify(str(name))
        
        if slug in self.brand_cache:
            return self.brand_cache[slug]
            
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO brands (name, slug) VALUES (%s, %s) ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name RETURNING id;",
                (name, slug)
            )
            brand_id = cur.fetchone()[0]
            self.conn.commit()
            
        self.brand_cache[slug] = brand_id
        return brand_id

    def process_file(self, file_path):
        print(f"Processing: {file_path}")
        df = pd.read_csv(file_path)
        
        # Replace NaN with None for psycopg2 compatibility
        df = df.replace({np.nan: None})
        
        # Batch insertions
        records = []
        
        for _, row in df.iterrows():
            # 1. Resolve Category Hierarchy
            main_cat_id, main_slug = self.get_or_create_category(row.get('main_category'))
            sub_cat_id, sub_slug = self.get_or_create_category(row.get('sub_category'), parent_id=main_cat_id, slug_prefix=main_slug)
            leaf_cat_id, leaf_slug = self.get_or_create_category(row.get('leaf_category'), parent_id=sub_cat_id, slug_prefix=sub_slug)
            
            final_cat_id = leaf_cat_id or sub_cat_id or main_cat_id
            
            # 2. Resolve Brand
            brand_id = self.get_or_create_brand(row.get('brand'))
            
            # 3. Compile context string for AI Embeddings
            name = str(row.get('name', 'Unknown Product'))
            brand_name = str(row.get('brand', ''))
            cat_path = str(row.get('category_path', ''))
            
            # "Category Path: Elektronik -> Beyaz Eşya -> Derin Dondurucu, Brand: TechCorp, Product Name: Wireless Headphones Pro"
            context_str = f"Category Path: {cat_path}, Brand: {brand_name}, Product Name: {name}"
            
            records.append({
                "category_id": final_cat_id,
                "brand_id": brand_id,
                "name": name,
                "price_original": row.get('price_original') if not pd.isna(row.get('price_original')) else None,
                "price_sale": row.get('price_sale') if not pd.isna(row.get('price_sale')) else 0, # Fallback to 0 if none
                "discount_pct": row.get('discount_pct') if not pd.isna(row.get('discount_pct')) else None,
                "rating": row.get('rating') if not pd.isna(row.get('rating')) else None,
                "review_count": row.get('review_count') if not pd.isna(row.get('review_count')) else None,
                "product_url": row.get('product_url'),
                "photo_url": row.get('photo_url'),
                "scraped_at": row.get('scraped_at'),
                "context_str": context_str
            })
            
            if len(records) >= BATCH_SIZE:
                self.flush_batch(records)
                records = []
                
        if records:
            self.flush_batch(records)

    def flush_batch(self, records):
        if not records: return
        
        unique_records = {}
        for r in records:
            if not r.get('product_url') or pd.isna(r['product_url']):
                r['product_url'] = str(uuid.uuid4()) # fake unique
            unique_records[r['product_url']] = r
            
        records = list(unique_records.values())
        if not records: return
        
        print(f"Flushing batch of {len(records)} products + embeddings to DB...")
        
        # Generate all vectors at once for hardware speed
        contexts = [r['context_str'] for r in records]
        embeddings = self.model.encode(contexts)
        
        upsert_query = """
            INSERT INTO products (
                id, category_id, brand_id, name, price_original, price_sale, 
                discount_pct, rating, review_count, product_url, photo_url, scraped_at
            ) VALUES %s
            ON CONFLICT (product_url) DO UPDATE SET
                price_sale = EXCLUDED.price_sale,
                discount_pct = EXCLUDED.discount_pct,
                rating = EXCLUDED.rating,
                review_count = EXCLUDED.review_count,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id;
        """
        
        # Map values to generate IDs in Python to ensure embeddings tie cleanly
        # Actually `RETURNING id` is powerful, but execute_values with RETURNING isn't always easy to pair back 1:1 if there are conflicts without data sorting.
        # Alternatively we pass a generated UUID.
        
        product_values = []
        for r in records:
            r['uuid'] = str(uuid.uuid4())
            product_values.append((
                r['uuid'],
                r['category_id'],
                r['brand_id'],
                r['name'],
                r['price_original'],
                r['price_sale'],
                r['discount_pct'],
                r['rating'],
                r['review_count'],
                r['product_url'],
                r['photo_url'],
                r['scraped_at']
            ))

        # Because we define ON CONFLICT DO UPDATE, the id of conflicts won't match the new UUID.
        # It's better to fetch the true ID.
        fixed_upsert_query = """
            INSERT INTO products (
                category_id, brand_id, name, price_original, price_sale, 
                discount_pct, rating, review_count, product_url, photo_url, scraped_at
            ) VALUES %s
            ON CONFLICT (product_url) DO UPDATE SET
                price_sale = EXCLUDED.price_sale,
                discount_pct = EXCLUDED.discount_pct,
                rating = EXCLUDED.rating,
                review_count = EXCLUDED.review_count,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id;
        """
        
        no_uuid_values = [v[1:] for v in product_values]

        with self.conn.cursor() as cur:
            # We can't use execute_values with RETURNING effectively across standard psycopg drivers without returning a list directly.
            # Instead we can do a loop, or `execute_values(..., fetch=True)`
            res = execute_values(cur, fixed_upsert_query, no_uuid_values, fetch=True)
            
            # Ensure mapped correctly: In modern postgres `execute_values` returns the IDs sequentially if we inserted sequentially.
            returned_ids = [row[0] for row in res]
            
            # Insert Embeddings
            emb_values = []
            for i, p_id in enumerate(returned_ids):
                vec_list = embeddings[i].tolist()
                emb_values.append((str(p_id), str(vec_list)))
                
            emb_upsert_query = """
                INSERT INTO product_embeddings (product_id, embedding)
                VALUES %s
                ON CONFLICT (product_id) DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    updated_at = CURRENT_TIMESTAMP;
            """
            execute_values(cur, emb_upsert_query, emb_values)
            self.conn.commit()

    def run(self, raw_data_dir="data/raw"):
        search_path = os.path.join(raw_data_dir, "**", "*.csv")
        csv_files = glob.glob(search_path, recursive=True)
        
        if not csv_files:
            print(f"No CSVs found in {search_path}")
            return
            
        print(f"Found {len(csv_files)} datasets. Beginning pipeline...")
        for file in csv_files:
            self.process_file(file)
            
        print("Pipeline Complete! All products are loaded and embedded.")
        self.conn.close()

if __name__ == "__main__":
    pipeline = ELTPipeline()
    pipeline.run()
