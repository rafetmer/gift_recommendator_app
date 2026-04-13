-- =============================================================================
-- EXAMPLE QUERIES — Gift Recommendation System
-- Covers: semantic search, content-based filtering, hybrid recommendations,
--         category browsing, price filtering, analytics
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. SEMANTIC SIMILARITY SEARCH (Content-Based Recommendation)
-- "Find products similar to product X" using vector cosine similarity
-- Use case: "More like this" on product detail page
-- ---------------------------------------------------------------------------
-- SET ivfflat.probes = 20;  -- Increase for better accuracy (slower)

SELECT
    p.product_id,
    p.name,
    p.effective_price,
    p.rating_avg,
    b.name                                                    AS brand,
    c.name                                                    AS category,
    1 - (e2.embedding_384 <=> e1.embedding_384)              AS cosine_similarity
FROM ai.product_embeddings e1
JOIN ai.product_embeddings e2
    ON e1.model = e2.model
    AND e1.product_id != e2.product_id
JOIN catalog.products p
    ON p.product_id = e2.product_id
LEFT JOIN catalog.brands b ON p.brand_id = b.brand_id
LEFT JOIN catalog.categories c ON p.category_id = c.category_id
WHERE e1.product_id = :target_product_id
  AND p.status = 'active'
ORDER BY e2.embedding_384 <=> e1.embedding_384   -- ASC = most similar first
LIMIT 20;

-- ---------------------------------------------------------------------------
-- 2. GIFT RECOMMENDATION — Budget + Occasion filtered
-- "Find birthday gifts for ₺100–₺500"
-- Hybrid: vector similarity + filters + popularity score
-- ---------------------------------------------------------------------------
WITH occasion_products AS (
    SELECT po.product_id, po.relevance_score
    FROM catalog.product_occasions po
    JOIN catalog.gift_occasions go ON go.occasion_id = po.occasion_id
    WHERE go.name = :occasion_name                            -- e.g. 'birthday'
)
SELECT
    p.product_id,
    p.name,
    p.effective_price,
    p.discount_pct,
    p.rating_avg,
    p.rating_count,
    b.name                                                    AS brand,
    c.name                                                    AS category,
    pf.popularity_score,
    op.relevance_score,
    -- Composite recommendation score
    (0.4 * pf.popularity_score
     + 0.3 * op.relevance_score
     + 0.2 * (p.rating_avg / 5.0)
     + 0.1 * CASE WHEN p.discount_pct > 0 THEN 1.0 ELSE 0.5 END
    )                                                         AS rec_score
FROM catalog.products p
JOIN occasion_products op ON p.product_id = op.product_id
JOIN ai.product_features pf ON p.product_id = pf.product_id
LEFT JOIN catalog.brands b ON p.brand_id = b.brand_id
LEFT JOIN catalog.categories c ON p.category_id = c.category_id
WHERE p.status = 'active'
  AND p.effective_price BETWEEN :budget_min AND :budget_max
  AND p.rating_avg >= 3.5
ORDER BY rec_score DESC
LIMIT 20;

-- ---------------------------------------------------------------------------
-- 3. FULL-TEXT SEARCH (Turkish)
-- "Search for 'deri cüzdan erkek' (leather wallet men)"
-- ---------------------------------------------------------------------------
SELECT
    p.product_id,
    p.name,
    p.effective_price,
    p.rating_avg,
    b.name                                                    AS brand,
    ts_rank_cd(
        to_tsvector('turkish', p.name || ' ' || COALESCE(p.description, '')),
        plainto_tsquery('turkish', :search_query)
    )                                                         AS text_rank
FROM catalog.products p
LEFT JOIN catalog.brands b ON p.brand_id = b.brand_id
WHERE p.status = 'active'
  AND to_tsvector('turkish', p.name || ' ' || COALESCE(p.description, ''))
      @@ plainto_tsquery('turkish', :search_query)
ORDER BY text_rank DESC, p.rating_avg DESC NULLS LAST
LIMIT 50;

-- ---------------------------------------------------------------------------
-- 4. CATEGORY BROWSING with full hierarchy
-- "Get all products in 'Elektronik' including all subcategories"
-- Uses closure table for O(1) hierarchy traversal
-- ---------------------------------------------------------------------------
SELECT
    p.product_id,
    p.name,
    p.effective_price,
    p.rating_avg,
    c.name                                                    AS category,
    c.level
FROM catalog.products p
JOIN catalog.category_closure cc
    ON cc.descendant_id = p.category_id
JOIN catalog.categories root_cat
    ON root_cat.category_id = cc.ancestor_id
JOIN catalog.categories c
    ON c.category_id = p.category_id
WHERE root_cat.slug = :category_slug                         -- e.g. 'elektronik-l0'
  AND p.status = 'active'
ORDER BY p.rating_avg DESC NULLS LAST
LIMIT 100;

-- ---------------------------------------------------------------------------
-- 5. PRE-COMPUTED SIMILARITY LOOKUP (Fast, cached)
-- Used in real-time recommendation API for low-latency response
-- ---------------------------------------------------------------------------
SELECT
    p.product_id,
    p.name,
    p.effective_price,
    p.rating_avg,
    ps.similarity_score,
    b.name AS brand
FROM ai.product_similarity ps
JOIN catalog.products p ON p.product_id = ps.similar_product_id
LEFT JOIN catalog.brands b ON p.brand_id = b.brand_id
WHERE ps.product_id = :target_product_id
  AND ps.model = 'paraphrase-multilingual-mpnet-base-v2'
  AND p.status = 'active'
ORDER BY ps.similarity_score DESC
LIMIT 10;

-- ---------------------------------------------------------------------------
-- 6. COLLABORATIVE FILTERING BASE QUERY
-- "Users who interacted with product X also interacted with..."
-- (Run once users exist; skeleton shows the pattern)
-- ---------------------------------------------------------------------------
WITH product_interactors AS (
    SELECT DISTINCT user_id
    FROM events.interactions
    WHERE product_id = :target_product_id
      AND interaction IN ('purchase', 'add_to_cart', 'wishlist')
      AND created_at > now() - INTERVAL '90 days'
),
co_interacted AS (
    SELECT
        i.product_id,
        COUNT(DISTINCT i.user_id)                            AS co_interaction_count,
        COUNT(*) FILTER (WHERE i.interaction = 'purchase')   AS purchase_count
    FROM events.interactions i
    JOIN product_interactors pi ON i.user_id = pi.user_id
    WHERE i.product_id != :target_product_id
      AND i.interaction IN ('purchase', 'add_to_cart', 'wishlist')
    GROUP BY i.product_id
    HAVING COUNT(DISTINCT i.user_id) >= 3                    -- Min support threshold
)
SELECT
    p.product_id,
    p.name,
    p.effective_price,
    p.rating_avg,
    c.co_interaction_count,
    c.purchase_count,
    -- Item-item collaborative filtering score
    c.purchase_count * 2.0 + c.co_interaction_count          AS cf_score
FROM co_interacted c
JOIN catalog.products p ON p.product_id = c.product_id
WHERE p.status = 'active'
ORDER BY cf_score DESC
LIMIT 20;

-- ---------------------------------------------------------------------------
-- 7. HYBRID RECOMMENDATION (Content-Based + Collaborative)
-- Combines vector similarity with CF signals
-- ---------------------------------------------------------------------------
WITH content_scores AS (
    SELECT
        ps.similar_product_id                                AS product_id,
        ps.similarity_score                                  AS content_score
    FROM ai.product_similarity ps
    WHERE ps.product_id = :target_product_id
),
cf_scores AS (
    SELECT
        i.product_id,
        COUNT(DISTINCT i.user_id)::float /
            (SELECT COUNT(DISTINCT user_id) FROM events.interactions
             WHERE product_id = :target_product_id)          AS cf_score
    FROM events.interactions i
    WHERE i.user_id IN (
        SELECT DISTINCT user_id FROM events.interactions
        WHERE product_id = :target_product_id
    )
    AND i.product_id != :target_product_id
    GROUP BY i.product_id
)
SELECT
    p.product_id,
    p.name,
    p.effective_price,
    p.rating_avg,
    b.name                                                   AS brand,
    COALESCE(cs.content_score, 0)                           AS content_score,
    COALESCE(cfs.cf_score, 0)                               AS cf_score,
    -- Weighted hybrid: 60% content + 40% collaborative
    -- Tune weights based on A/B test results
    (0.6 * COALESCE(cs.content_score, 0)
     + 0.4 * COALESCE(cfs.cf_score, 0))                    AS hybrid_score
FROM catalog.products p
LEFT JOIN content_scores cs ON cs.product_id = p.product_id
LEFT JOIN cf_scores cfs ON cfs.product_id = p.product_id
LEFT JOIN catalog.brands b ON p.brand_id = b.brand_id
WHERE p.status = 'active'
  AND (cs.product_id IS NOT NULL OR cfs.product_id IS NOT NULL)
ORDER BY hybrid_score DESC
LIMIT 20;

-- ---------------------------------------------------------------------------
-- 8. ANALYTICS — Category performance dashboard
-- ---------------------------------------------------------------------------
SELECT
    cs.name,
    cs.level,
    cs.product_count,
    ROUND(cs.avg_price::numeric, 2)                         AS avg_price,
    ROUND(cs.median_price::numeric, 2)                      AS median_price,
    ROUND(cs.avg_rating::numeric, 2)                        AS avg_rating,
    cs.total_sales,
    cs.refreshed_at
FROM analytics.category_stats cs
ORDER BY cs.total_sales DESC NULLS LAST
LIMIT 20;

-- ---------------------------------------------------------------------------
-- 9. PRICE TREND ANALYSIS
-- "How has the price of product X changed over time?"
-- ---------------------------------------------------------------------------
SELECT
    product_id,
    base_price,
    discounted_price,
    recorded_at,
    base_price - LAG(base_price) OVER (
        PARTITION BY product_id ORDER BY recorded_at
    )                                                        AS price_delta
FROM analytics.product_price_history
WHERE product_id = :target_product_id
ORDER BY recorded_at DESC;

-- ---------------------------------------------------------------------------
-- 10. PRODUCT ATTRIBUTE FACETS (for filter sidebar)
-- "What are all color options in category X, with counts?"
-- ---------------------------------------------------------------------------
SELECT
    ad.name                                                  AS attribute_name,
    ad.name_en,
    pa.value_text,
    pa.display_value,
    COUNT(*)                                                 AS product_count
FROM catalog.product_attributes pa
JOIN catalog.attribute_definitions ad ON ad.attr_def_id = pa.attr_def_id
JOIN catalog.products p ON p.product_id = pa.product_id
WHERE p.category_id IN (
    SELECT descendant_id FROM catalog.category_closure
    WHERE ancestor_id = (SELECT category_id FROM catalog.categories WHERE slug = :category_slug)
)
  AND p.status = 'active'
  AND ad.is_filterable = true
GROUP BY ad.name, ad.name_en, pa.value_text, pa.display_value
HAVING COUNT(*) >= 3                                        -- Min support
ORDER BY ad.display_order, product_count DESC;
