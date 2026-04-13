# Data Architecture & Technical Documentation
## Gift Recommendation System

This document outlines the architectural decisions, pipeline workflows, and scaling strategies for the AI-ready Gift Recommendation System based on Trendyol scraped data.

### 1. Database Design (Normalization)
**Core Strategy**: We utilize a **highly normalized schema** leaning on Third Normal Form (3NF) to align strictly with the predictable extraction properties.
- **Strict Typing for Products**: The core `products` table perfectly corresponds to absolute metadata variables scraped directly (e.g. `price_original`, `price_sale`, `discount_pct`, `rating`, `review_count`). By shedding generalized unstructured generic column approaches (JSONB), we guarantee explicit DB-level type safety and faster structured numerical operations without dynamic parsing.
- **Normalization (3NF)**: Core entities like `Categories`, `Brands`, and standard `Products` relationships are strictly linked.
- **AI Schema Design**: We map a strictly `1:1` table `product_embeddings` specifically for ML vectors. This prevents row bloating in the core OLTP `products` table, ensuring standard CRUD ops remain extremely fast while isolating analytical vector similarity searches.

### 2. Technology Selection
**Primary Database**: `PostgreSQL 16` equipped with the `pgvector` extension.
- **Justification**: Modern e-ecommerce engines require ACID transactions for real-time views/purchases. Adding `pgvector` introduces native Nearest-Neighbor vector search, turning Postgres into an AI database.
- **Trade-offs against MongoDB + Milvus/Pinecone**: Setting up an independent vector database creates dual-write orchestration complexity, synchronization latency, and operational overhead. Early-to-mid stage recommendation platforms perform optimally entirely inside Postgres. Only when encountering ultra-high volume global throughput (>50k ops/sec) would isolating vector searches to a specialized distributed store (like Milvus) be required.

### 3. Data Pipeline (ETL/ELT)
**Workflow**: Scrape → Clean → Transform → Load
1. **Clean**: Remove duplicates, handle missing prices, and uniformly format brands. (e.g., using Python Pandas/Polars). Data validation tests (via Pydantic or Great Expectations) ensure only valid products reach the DB.
2. **Transform (Feature Engineering)**: Run descriptions/attributes through an NLP embedding model (e.g. `all-MiniLM-L6-v2` yielding 384 dimensions) to output dense vector arrays.
3. **Load (Incremental)**: Upsert pipelines (`INSERT ON CONFLICT DO UPDATE`) to PostgreSQL ensuring price and attribute updates are mapped without crashing on duplicates.
4. **Schema Evolution**: Using a tool like `Alembic` or `Flyway` handles schema changes deterministically.

### 4. Performance & Scalability
- **Indexing Strategy**: 
  - `B-Tree` indexes on core Foreign Keys (category_id, brand_id).
  - `B-Tree` indexes on numericals heavily queried like `price_sale` and `rating` to instantly constrain hybrid metric queries.
  - `HNSW (Hierarchical Navigable Small World)` index on vector embeddings, guaranteeing low-latency Approximate Nearest Neighbor (ANN) matches over millions of arrays.
- **Partitioning Strategy**: 
  - The `user_interactions` table acts as a time-series event log, inherently growing immensely. It is **Partitioned by Time (Range)** natively in Postgres (e.g. breaking down globally into monthly or daily sub-tables), ensuring queries analyzing behavioral history remain bounded.
- **Bottlenecks/Mitigation**: As read-heavy vector searches grow, you can deploy Postgres read-replicas handling ML workloads purely, sparing the master node for transactional INSERTs.

### 5. AI & Recommendation Readiness
- **Content-based Filtering**: Built-in natively. Find a gift similar to Product A by comparing their vectors via Cosine distance (`<=>`).
- **Collaborative Filtering**: The `user_interactions` append-only partitioned table allows ML jobs (Matrix Factorization) to extract interaction graphs easily asynchronously.
- **Hybrid Recommendations**: Combine exact-match SQL rules with semantic AI search. E.g., "Find items semantically similar to 'Warm Winter Scarf' (pgvector cosine) but firmly constrain to `price < 150` and `brand = 'X'` (B-Tree)".

### 6. Best Practices
- **Naming Conventions**: Snake_case everywhere. Unambiguous PKs (`id`) and FKs (`table_id`).
- **Constraints**: Constraints stop garbage data (e.g., `CHECK (price > 0)`). 
- **Security**: The docker stack hides the database port internally unless actively bound. Standard App-tier roles (read/write limits) should be used rather than root DB credentials.
