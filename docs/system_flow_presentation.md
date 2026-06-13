# 🎁 Gift Recommender Engine: How it Works?

This system isn't just a simple search; it's a **Hybrid AI Recommendation Engine** that combines mathematical semantic understanding with curated business rules.

## 🎡 High-Level Architecture Flow

1. **Input:** User answers Questionnaire (6 questions).
2. **Pre-processing:** Filters out noise (e.g., separating kinship "Anne" from interest "Anne/Bebek").
3. **Stage 1 (Vector Search):** Uses `all-MiniLM-L6-v2` to find top 800 products by semantic similarity via `pgvector`.
4. **Stage 2 (Scoring):** Applies a weighted score (60% Logic / 40% AI) based on:
    - Algoritma keywords.
    - Category hierarchy matching.
    - Price-to-Budget alignment.
    - Rating & Popularity.
5. **Stage 3 (Diversity):** Enforces horizontal variety (Max 2 per brand, Max 2 per category).
6. **Output:** Top 5 highly relevant and diverse gift ideas.

## 🏆 Key Innovations
- **Hybrid Brain:** Combines LLM embeddings with strict Turkish retail category rules.
- **Instant Setup:** The entire 500k+ product DB is "pre-baked" into the Docker image, allowing immediate local development.
