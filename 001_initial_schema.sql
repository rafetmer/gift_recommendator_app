-- =============================================================================
-- TRENDYOL GIFT RECOMMENDATION SYSTEM
-- Migration 001: Initial Schema
-- Database: PostgreSQL 16 + pgvector
-- Author: Senior Data Engineer
-- Strategy: Hybrid OLTP/OLAP with AI-readiness from day one
-- =============================================================================

-- ---------------------------------------------------------------------------
-- EXTENSIONS
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";        -- Hashing & encryption
CREATE EXTENSION IF NOT EXISTS "vector";          -- pgvector for embeddings
CREATE EXTENSION IF NOT EXISTS "pg_trgm";         -- Trigram fuzzy search
CREATE EXTENSION IF NOT EXISTS "btree_gin";       -- GIN on btree-able types
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements"; -- Query performance monitoring

-- ---------------------------------------------------------------------------
-- SCHEMAS  (separation of concerns)
-- ---------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS catalog;      -- Core product catalog (OLTP)
CREATE SCHEMA IF NOT EXISTS analytics;   -- Materialized views, aggregates (OLAP)
CREATE SCHEMA IF NOT EXISTS ai;          -- Embeddings, features, ML artifacts
CREATE SCHEMA IF NOT EXISTS events;      -- User interaction event store
CREATE SCHEMA IF NOT EXISTS audit;       -- Audit trails & change history

-- ---------------------------------------------------------------------------
-- SHARED ENUMS
-- ---------------------------------------------------------------------------
CREATE TYPE catalog.product_status AS ENUM (
    'active', 'inactive', 'out_of_stock', 'discontinued', 'draft'
);

CREATE TYPE catalog.currency_code AS ENUM ('TRY', 'USD', 'EUR');

CREATE TYPE events.interaction_type AS ENUM (
    'view', 'click', 'add_to_cart', 'purchase', 'wishlist',
    'share', 'review', 'return', 'search_impression'
);

CREATE TYPE ai.embedding_model AS ENUM (
    'text-embedding-3-small',
    'text-embedding-3-large',
    'paraphrase-multilingual-mpnet-base-v2',
    'clip-vit-base-patch32',
    'custom-v1'
);

CREATE TYPE ai.embedding_source AS ENUM (
    'title', 'description', 'title_description',
    'attributes', 'full_text', 'image', 'multimodal'
);

-- ---------------------------------------------------------------------------
-- CATALOG SCHEMA — CORE TABLES
-- ---------------------------------------------------------------------------

-- 1. CATEGORIES (Closure Table pattern for unlimited hierarchy depth)
-- Why closure table over adjacency list: supports arbitrary-depth queries
-- in O(1) reads. Trendyol has 4-5 levels: e.g. Giyim→Kadın→Elbise→Midi
CREATE TABLE catalog.categories (
    category_id     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id     TEXT UNIQUE,                          -- Trendyol's own ID
    slug            TEXT NOT NULL UNIQUE,                 -- URL-friendly key
    name            TEXT NOT NULL,
    name_en         TEXT,                                 -- Translated name for ML
    description     TEXT,
    level           SMALLINT NOT NULL DEFAULT 0,          -- 0=root, 1=top, etc.
    is_leaf         BOOLEAN NOT NULL DEFAULT false,       -- True = accepts products
    is_active       BOOLEAN NOT NULL DEFAULT true,
    display_order   INTEGER DEFAULT 0,
    icon_url        TEXT,
    meta_keywords   TEXT[],                               -- SEO & search signals
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Closure table: every ancestor-descendant pair including self
CREATE TABLE catalog.category_closure (
    ancestor_id     UUID NOT NULL REFERENCES catalog.categories(category_id) ON DELETE CASCADE,
    descendant_id   UUID NOT NULL REFERENCES catalog.categories(category_id) ON DELETE CASCADE,
    depth           SMALLINT NOT NULL DEFAULT 0,
    PRIMARY KEY (ancestor_id, descendant_id)
);

-- 2. BRANDS
CREATE TABLE catalog.brands (
    brand_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id     TEXT UNIQUE,
    name            TEXT NOT NULL,
    name_normalized TEXT NOT NULL,                        -- lowercase, trimmed
    slug            TEXT NOT NULL UNIQUE,
    country_of_origin TEXT,
    logo_url        TEXT,
    website_url     TEXT,
    is_verified     BOOLEAN NOT NULL DEFAULT false,
    tier            SMALLINT DEFAULT 2,                   -- 1=luxury, 2=mid, 3=budget
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3. ATTRIBUTE DEFINITIONS (schema-on-read for flexibility)
-- Why not hardcode columns: Trendyol products have 200+ attribute types.
-- This allows adding new attribute types without migrations.
CREATE TABLE catalog.attribute_definitions (
    attr_def_id     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT NOT NULL UNIQUE,                 -- e.g. 'renk', 'beden'
    name_en         TEXT,                                 -- 'color', 'size'
    data_type       TEXT NOT NULL DEFAULT 'text',         -- text|number|boolean|list
    unit            TEXT,                                 -- e.g. 'cm', 'kg'
    is_filterable   BOOLEAN NOT NULL DEFAULT true,
    is_searchable   BOOLEAN NOT NULL DEFAULT true,
    display_order   INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4. PRODUCTS — The central OLTP table
-- Normalization decision: price kept here (single source of truth for OLTP)
-- Denormalized copies go into analytics.product_features for ML
CREATE TABLE catalog.products (
    product_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id         TEXT UNIQUE NOT NULL,             -- Trendyol product ID
    sku                 TEXT UNIQUE,                      -- Stock keeping unit
    name                TEXT NOT NULL,
    name_normalized     TEXT NOT NULL,                    -- for dedup & search
    slug                TEXT NOT NULL UNIQUE,
    description         TEXT,
    category_id         UUID NOT NULL REFERENCES catalog.categories(category_id),
    brand_id            UUID REFERENCES catalog.brands(brand_id),

    -- Pricing (multi-currency ready)
    base_price          NUMERIC(12,2) NOT NULL,
    discounted_price    NUMERIC(12,2),
    currency            catalog.currency_code NOT NULL DEFAULT 'TRY',
    discount_pct        NUMERIC(5,2) GENERATED ALWAYS AS (
                            CASE WHEN base_price > 0 AND discounted_price IS NOT NULL
                            THEN ROUND((1 - discounted_price / base_price) * 100, 2)
                            ELSE 0 END
                        ) STORED,
    effective_price     NUMERIC(12,2) GENERATED ALWAYS AS (
                            COALESCE(discounted_price, base_price)
                        ) STORED,

    -- Quality signals
    rating_avg          NUMERIC(3,2),
    rating_count        INTEGER DEFAULT 0,
    review_count        INTEGER DEFAULT 0,
    sales_count         INTEGER DEFAULT 0,                -- For popularity scoring
    favorite_count      INTEGER DEFAULT 0,

    -- Logistics
    is_free_shipping    BOOLEAN DEFAULT false,
    delivery_days       SMALLINT,

    -- Content
    primary_image_url   TEXT,
    images              JSONB DEFAULT '[]',               -- [{url, alt, order}]
    video_url           TEXT,

    -- Raw scraped data preserved for reprocessing
    raw_attributes      JSONB DEFAULT '{}',               -- key:value from scrape
    raw_tags            TEXT[],

    -- Lifecycle
    status              catalog.product_status NOT NULL DEFAULT 'active',
    scraped_at          TIMESTAMPTZ,                      -- When we got this
    first_seen_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_verified_at    TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Constraints
    CONSTRAINT chk_price_positive CHECK (base_price >= 0),
    CONSTRAINT chk_discount_price CHECK (
        discounted_price IS NULL OR discounted_price <= base_price
    ),
    CONSTRAINT chk_rating CHECK (rating_avg IS NULL OR rating_avg BETWEEN 0 AND 5)
);

-- 5. PRODUCT ATTRIBUTES (EAV — Entity-Attribute-Value)
-- Why EAV here: Trendyol products have sparse, heterogeneous attributes.
-- We store typed values + raw text for backward compatibility.
CREATE TABLE catalog.product_attributes (
    product_attr_id  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id       UUID NOT NULL REFERENCES catalog.products(product_id) ON DELETE CASCADE,
    attr_def_id      UUID NOT NULL REFERENCES catalog.attribute_definitions(attr_def_id),
    value_text       TEXT,                                -- Always populated
    value_numeric    NUMERIC,                             -- For numeric attrs
    value_list       TEXT[],                              -- For multi-value attrs
    display_value    TEXT,                                -- Human-readable
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (product_id, attr_def_id)
);

-- 6. PRODUCT TAGS (many-to-many, denormalized for speed)
CREATE TABLE catalog.tags (
    tag_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        TEXT NOT NULL UNIQUE,
    tag_type    TEXT DEFAULT 'general',                   -- gift|occasion|age|style
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE catalog.product_tags (
    product_id  UUID NOT NULL REFERENCES catalog.products(product_id) ON DELETE CASCADE,
    tag_id      UUID NOT NULL REFERENCES catalog.tags(tag_id) ON DELETE CASCADE,
    source      TEXT DEFAULT 'manual',                    -- manual|ml|scrape
    confidence  NUMERIC(4,3),                             -- ML confidence score
    PRIMARY KEY (product_id, tag_id)
);

-- 7. GIFT OCCASIONS (domain-specific for gift recommendation)
CREATE TABLE catalog.gift_occasions (
    occasion_id     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT NOT NULL UNIQUE,                 -- 'birthday','wedding'
    name_tr         TEXT,                                 -- Turkish name
    description     TEXT,
    season          TEXT,                                 -- 'all','winter','summer'
    is_active       BOOLEAN DEFAULT true
);

CREATE TABLE catalog.product_occasions (
    product_id      UUID NOT NULL REFERENCES catalog.products(product_id) ON DELETE CASCADE,
    occasion_id     UUID NOT NULL REFERENCES catalog.gift_occasions(occasion_id),
    relevance_score NUMERIC(4,3) DEFAULT 1.0,
    source          TEXT DEFAULT 'manual',
    PRIMARY KEY (product_id, occasion_id)
);

-- ---------------------------------------------------------------------------
-- AI SCHEMA — EMBEDDINGS & FEATURE STORE
-- ---------------------------------------------------------------------------

-- 8. PRODUCT EMBEDDINGS (pgvector core table)
-- Each product can have multiple embeddings from different models/sources.
-- Why separate table: embeddings are large (1536 dims = 6KB per row).
-- Keeping them separate avoids bloating the products table.
CREATE TABLE ai.product_embeddings (
    embedding_id    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id      UUID NOT NULL REFERENCES catalog.products(product_id) ON DELETE CASCADE,
    model           ai.embedding_model NOT NULL,
    source          ai.embedding_source NOT NULL,
    embedding       vector(1536),                         -- Adjustable per model
    embedding_384   vector(384),                          -- Lighter multilingual models
    embedding_768   vector(768),                          -- BERT-family models
    text_hash       TEXT,                                 -- SHA256 of source text
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (product_id, model, source)
);

-- 9. FEATURE STORE — Denormalized ML-ready feature table
-- Why this exists: ML pipelines need flat, numeric, pre-computed features.
-- This is the "wide table" pattern common in production feature stores.
CREATE TABLE ai.product_features (
    product_id          UUID PRIMARY KEY REFERENCES catalog.products(product_id) ON DELETE CASCADE,
    -- Price features
    price_log           FLOAT,                            -- log(effective_price)
    price_bucket        SMALLINT,                         -- 1-10 decile
    discount_pct        FLOAT,
    -- Quality features
    rating_avg          FLOAT,
    rating_count_log    FLOAT,
    review_count_log    FLOAT,
    popularity_score    FLOAT,                            -- Composite signal
    -- Category features (encoded)
    category_l1_enc     SMALLINT,                         -- Level 1 category ID
    category_l2_enc     SMALLINT,
    category_l3_enc     SMALLINT,
    brand_enc           INTEGER,
    -- Content features
    title_length        SMALLINT,
    has_description     BOOLEAN,
    image_count         SMALLINT,
    -- Gift-specific features
    is_giftable         BOOLEAN DEFAULT false,
    gift_occasions_enc  INTEGER[],                        -- Encoded occasion IDs
    -- Temporal features
    days_since_scraped  INTEGER,
    -- Raw JSON for new features without migration
    extra_features      JSONB DEFAULT '{}',
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 10. SIMILARITY INDEX (pre-computed for fast lookups)
-- Cache top-K similar products to avoid real-time vector search at scale
CREATE TABLE ai.product_similarity (
    product_id          UUID NOT NULL REFERENCES catalog.products(product_id) ON DELETE CASCADE,
    similar_product_id  UUID NOT NULL REFERENCES catalog.products(product_id) ON DELETE CASCADE,
    similarity_score    FLOAT NOT NULL,
    similarity_type     TEXT NOT NULL DEFAULT 'cosine',   -- cosine|dot|euclidean
    model               ai.embedding_model NOT NULL,
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (product_id, similar_product_id, model)
);

-- ---------------------------------------------------------------------------
-- EVENTS SCHEMA — USER INTERACTIONS (future-ready)
-- ---------------------------------------------------------------------------

-- 11. USERS (skeleton — fills in as app grows)
CREATE TABLE events.users (
    user_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id     TEXT UNIQUE,                          -- App user ID
    session_id      TEXT,                                 -- Anonymous sessions
    country_code    TEXT DEFAULT 'TR',
    age_group       TEXT,                                 -- '18-24','25-34' etc
    gender          TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 12. INTERACTIONS — Partitioned by month for scalability
-- Why partitioning: at 10M users × 50 events/day = 500M rows/day.
-- Monthly partitions allow fast archival and partition-pruning in queries.
CREATE TABLE events.interactions (
    interaction_id  UUID NOT NULL DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES events.users(user_id),
    session_id      TEXT NOT NULL,
    product_id      UUID NOT NULL REFERENCES catalog.products(product_id),
    interaction     events.interaction_type NOT NULL,
    -- Context
    source_page     TEXT,                                 -- 'home','search','reco'
    search_query    TEXT,
    position        SMALLINT,                             -- Position in list
    -- Gift context
    occasion_id     UUID REFERENCES catalog.gift_occasions(occasion_id),
    recipient_profile JSONB DEFAULT '{}',                 -- age_group, gender, etc
    -- Metrics
    dwell_time_ms   INTEGER,
    scroll_depth    NUMERIC(4,3),
    -- Technical
    device_type     TEXT,
    ip_hash         TEXT,                                 -- Privacy-safe
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
) PARTITION BY RANGE (created_at);

-- Create initial monthly partitions
CREATE TABLE events.interactions_2024_01
    PARTITION OF events.interactions
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE events.interactions_2024_q2
    PARTITION OF events.interactions
    FOR VALUES FROM ('2024-04-01') TO ('2024-07-01');

CREATE TABLE events.interactions_2025_q1
    PARTITION OF events.interactions
    FOR VALUES FROM ('2025-01-01') TO ('2025-04-01');

CREATE TABLE events.interactions_2025_q2
    PARTITION OF events.interactions
    FOR VALUES FROM ('2025-04-01') TO ('2025-07-01');

CREATE TABLE events.interactions_2025_q3
    PARTITION OF events.interactions
    FOR VALUES FROM ('2025-07-01') TO ('2025-10-01');

CREATE TABLE events.interactions_2025_q4
    PARTITION OF events.interactions
    FOR VALUES FROM ('2025-10-01') TO ('2026-01-01');

CREATE TABLE events.interactions_2026_q1
    PARTITION OF events.interactions
    FOR VALUES FROM ('2026-01-01') TO ('2026-04-01');

CREATE TABLE events.interactions_2026_q2
    PARTITION OF events.interactions
    FOR VALUES FROM ('2026-04-01') TO ('2026-07-01');

-- Default partition catches out-of-range
CREATE TABLE events.interactions_default
    PARTITION OF events.interactions DEFAULT;

-- 13. RECOMMENDATION REQUESTS — Log what was recommended & why
CREATE TABLE events.recommendation_requests (
    request_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES events.users(user_id),
    session_id      TEXT NOT NULL,
    occasion_id     UUID REFERENCES catalog.gift_occasions(occasion_id),
    recipient_profile JSONB DEFAULT '{}',
    budget_min      NUMERIC(12,2),
    budget_max      NUMERIC(12,2),
    algorithm       TEXT NOT NULL,                        -- 'content','collab','hybrid'
    model_version   TEXT,
    recommended_ids UUID[],                               -- Ordered product IDs
    clicked_ids     UUID[],
    purchased_ids   UUID[],
    latency_ms      INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- ANALYTICS SCHEMA — MATERIALIZED VIEWS FOR OLAP
-- ---------------------------------------------------------------------------

-- 14. PRICE HISTORY (time-series for trend analysis)
CREATE TABLE analytics.product_price_history (
    price_hist_id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id      UUID NOT NULL REFERENCES catalog.products(product_id),
    base_price      NUMERIC(12,2) NOT NULL,
    discounted_price NUMERIC(12,2),
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 15. MATERIALIZED VIEW: Category stats (refreshed by cron)
CREATE MATERIALIZED VIEW analytics.category_stats AS
SELECT
    c.category_id,
    c.name,
    c.level,
    COUNT(p.product_id)                 AS product_count,
    AVG(p.effective_price)              AS avg_price,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY p.effective_price) AS median_price,
    MIN(p.effective_price)              AS min_price,
    MAX(p.effective_price)              AS max_price,
    AVG(p.rating_avg)                   AS avg_rating,
    SUM(p.sales_count)                  AS total_sales,
    now()                               AS refreshed_at
FROM catalog.categories c
JOIN catalog.products p ON p.category_id = c.category_id
WHERE p.status = 'active'
GROUP BY c.category_id, c.name, c.level
WITH DATA;

-- 16. MATERIALIZED VIEW: Brand stats
CREATE MATERIALIZED VIEW analytics.brand_stats AS
SELECT
    b.brand_id,
    b.name,
    b.tier,
    COUNT(p.product_id)     AS product_count,
    AVG(p.effective_price)  AS avg_price,
    AVG(p.rating_avg)       AS avg_rating,
    SUM(p.sales_count)      AS total_sales,
    now()                   AS refreshed_at
FROM catalog.brands b
JOIN catalog.products p ON p.brand_id = b.brand_id
WHERE p.status = 'active'
GROUP BY b.brand_id, b.name, b.tier
WITH DATA;

-- ---------------------------------------------------------------------------
-- AUDIT SCHEMA
-- ---------------------------------------------------------------------------

CREATE TABLE audit.product_changes (
    change_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id      UUID NOT NULL,
    changed_by      TEXT DEFAULT 'system',
    change_type     TEXT NOT NULL,                        -- INSERT|UPDATE|DELETE
    old_values      JSONB,
    new_values      JSONB,
    changed_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- INDEXES — The performance backbone
-- ---------------------------------------------------------------------------

-- Categories
CREATE INDEX idx_categories_slug ON catalog.categories(slug);
CREATE INDEX idx_categories_level ON catalog.categories(level) WHERE is_active = true;
CREATE INDEX idx_category_closure_descendant ON catalog.category_closure(descendant_id);

-- Brands
CREATE INDEX idx_brands_name ON catalog.brands USING gin(name_normalized gin_trgm_ops);
CREATE INDEX idx_brands_slug ON catalog.brands(slug);

-- Products — Core lookups
CREATE INDEX idx_products_category ON catalog.products(category_id) WHERE status = 'active';
CREATE INDEX idx_products_brand ON catalog.products(brand_id) WHERE status = 'active';
CREATE INDEX idx_products_status ON catalog.products(status);
CREATE INDEX idx_products_external_id ON catalog.products(external_id);

-- Products — Price range filtering (common in gift apps: "budget: 100-500 TRY")
CREATE INDEX idx_products_price_range ON catalog.products(effective_price, currency)
    WHERE status = 'active';

-- Products — Rating-based sorting
CREATE INDEX idx_products_rating ON catalog.products(rating_avg DESC NULLS LAST, rating_count DESC)
    WHERE status = 'active';

-- Products — Full-text search (Turkish + English)
CREATE INDEX idx_products_fts ON catalog.products
    USING gin(to_tsvector('turkish', COALESCE(name, '') || ' ' || COALESCE(description, '')));

-- Products — Trigram search for fuzzy matching
CREATE INDEX idx_products_name_trgm ON catalog.products USING gin(name_normalized gin_trgm_ops);

-- Products — JSONB attributes index
CREATE INDEX idx_products_raw_attrs ON catalog.products USING gin(raw_attributes);

-- Product attributes
CREATE INDEX idx_product_attrs_product ON catalog.product_attributes(product_id);
CREATE INDEX idx_product_attrs_def ON catalog.product_attributes(attr_def_id);
CREATE INDEX idx_product_attrs_value ON catalog.product_attributes(value_text)
    WHERE value_text IS NOT NULL;

-- Product tags
CREATE INDEX idx_product_tags_tag ON catalog.product_tags(tag_id);

-- Embeddings — IVFFlat for approximate nearest neighbor
-- lists = sqrt(row_count). Start with 100, tune after data load.
-- Why IVFFlat over HNSW: lower memory, faster inserts, good for batch
-- HNSW is better for real-time; switch when query latency matters more.
CREATE INDEX idx_embeddings_ivfflat_1536 ON ai.product_embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX idx_embeddings_ivfflat_384 ON ai.product_embeddings
    USING ivfflat (embedding_384 vector_cosine_ops) WITH (lists = 100);

CREATE INDEX idx_embeddings_product ON ai.product_embeddings(product_id);

-- Feature store
CREATE INDEX idx_features_price_bucket ON ai.product_features(price_bucket);
CREATE INDEX idx_features_giftable ON ai.product_features(is_giftable) WHERE is_giftable = true;

-- Similarity
CREATE INDEX idx_similarity_product ON ai.product_similarity(product_id, similarity_score DESC);

-- Events — Already partitioned, but add local indexes per partition
CREATE INDEX idx_interactions_session ON events.interactions(session_id, created_at DESC);
CREATE INDEX idx_interactions_product ON events.interactions(product_id, created_at DESC);
CREATE INDEX idx_interactions_user ON events.interactions(user_id, created_at DESC)
    WHERE user_id IS NOT NULL;
CREATE INDEX idx_interactions_type ON events.interactions(interaction, created_at DESC);

-- Price history
CREATE INDEX idx_price_history_product ON analytics.product_price_history(product_id, recorded_at DESC);

-- Unique index on materialized views
CREATE UNIQUE INDEX idx_cat_stats_category ON analytics.category_stats(category_id);
CREATE UNIQUE INDEX idx_brand_stats_brand ON analytics.brand_stats(brand_id);

-- ---------------------------------------------------------------------------
-- TRIGGERS — Automation & data integrity
-- ---------------------------------------------------------------------------

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_products_updated_at
    BEFORE UPDATE ON catalog.products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_brands_updated_at
    BEFORE UPDATE ON catalog.brands
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_categories_updated_at
    BEFORE UPDATE ON catalog.categories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Audit log trigger for products
CREATE OR REPLACE FUNCTION audit.log_product_change()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO audit.product_changes(product_id, change_type, old_values, new_values)
    VALUES (
        COALESCE(NEW.product_id, OLD.product_id),
        TG_OP,
        CASE WHEN TG_OP != 'INSERT' THEN row_to_json(OLD)::jsonb ELSE NULL END,
        CASE WHEN TG_OP != 'DELETE' THEN row_to_json(NEW)::jsonb ELSE NULL END
    );
    RETURN COALESCE(NEW, OLD);
END;
$$;

CREATE TRIGGER trg_products_audit
    AFTER INSERT OR UPDATE OR DELETE ON catalog.products
    FOR EACH ROW EXECUTE FUNCTION audit.log_product_change();

-- Auto-populate name_normalized
CREATE OR REPLACE FUNCTION catalog.normalize_text(t TEXT)
RETURNS TEXT LANGUAGE sql IMMUTABLE AS $$
    SELECT lower(trim(regexp_replace(t, '\s+', ' ', 'g')));
$$;

CREATE OR REPLACE FUNCTION catalog.set_product_normalized()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.name_normalized = catalog.normalize_text(NEW.name);
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_products_normalize
    BEFORE INSERT OR UPDATE OF name ON catalog.products
    FOR EACH ROW EXECUTE FUNCTION catalog.set_product_normalized();

-- ---------------------------------------------------------------------------
-- ROW LEVEL SECURITY (baseline — extend per app requirements)
-- ---------------------------------------------------------------------------
ALTER TABLE events.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE events.interactions ENABLE ROW LEVEL SECURITY;

-- Service role bypasses RLS
CREATE POLICY service_bypass ON events.users
    USING (current_role = 'gift_app_service');
CREATE POLICY service_bypass ON events.interactions
    USING (current_role = 'gift_app_service');

-- ---------------------------------------------------------------------------
-- COMMENTS (documentation in the DB itself)
-- ---------------------------------------------------------------------------
COMMENT ON TABLE catalog.products IS 'Core product catalog. Single source of truth for product data.';
COMMENT ON TABLE catalog.category_closure IS 'Closure table for O(1) ancestor/descendant lookups at any hierarchy depth.';
COMMENT ON TABLE ai.product_embeddings IS 'Vector embeddings per product, per model, per source text. Used for semantic search and content-based recommendations.';
COMMENT ON TABLE ai.product_features IS 'Flat feature table for ML pipelines. Refresh on product update or nightly batch.';
COMMENT ON TABLE ai.product_similarity IS 'Pre-computed top-K similarity cache. Refresh weekly or on embedding update.';
COMMENT ON TABLE events.interactions IS 'User interaction event store. Partitioned by month. Feed for collaborative filtering.';
COMMENT ON COLUMN catalog.products.raw_attributes IS 'Original scraped attributes preserved as-is. Source of truth for re-ETL.';
COMMENT ON COLUMN ai.product_embeddings.embedding IS '1536-dim vector (OpenAI text-embedding-3-small/large). For semantic similarity.';
