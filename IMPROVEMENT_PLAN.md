# 🎯 Recommender Engine Geliştirme Planı

## Mevcut Durum Analizi

### Sorunlar
1. **Embedding Model**: `all-MiniLM-L6-v2` genel amaçlı → hediye tavsiye için optimize değil
2. **Weight Kalibrasyonu**: Statik ağırlıklar → ilişki türüne göre dinamik değil
3. **User Profile Extraction**: Eksik → zodiac, renk, personality traits'i kullanmıyor
4. **Relationship Context**: Yok → patrona verilen hediye ≠ sevgili için hediye
5. **Budget Flexibility**: Sert kurallar → lower bound kontrol yok
6. **Category Matching**: Çok basit string matching → semantic matching yok
7. **Personality Traits**: Questions 8-9'dan gelen bilgi kullanılmıyor (hobi, davranış)
8. **Diversity Logic**: Sadece brand+category kontrol → pattern diversity yok

---

## 🚀 İyileştirme Stratejisi

### KATMAN 1: Embedding Model Geliştirme
**Hedef**: Turkish-specific semantic matching

**Eylemler**:
- [ ] `distiluse-base-multilingual-v2` modeline geç (Turkish support)
- [ ] Turkish hediye terminolojisi için mini vocabulary cache kur
- [ ] Product title + category + brand'in semantic consistency'sini artır
- [ ] Embedding cache'ini optimize et (faster lookups)

**Beklenen Artış**: +25-30% relevance

---

### KATMAN 2: Dinamik Scoring Rules
**Hedef**: Relationship-aware, occasion-aware, personality-aware scoring

**Eylemler**:

#### 2A: Relationship-Based Weight Multipliers
```python
RELATIONSHIP_WEIGHTS = {
    "sevgili": {"personal": 3, "luxury": 2, "practical": 0.5},
    "anne": {"practical": 3, "home": 2.5, "luxury": 1},
    "baba": {"tech": 2.5, "practical": 2, "personal": 0.5},
    "arkadaş": {"trendy": 2.5, "fun": 2, "luxury": 1.5},
    "patron": {"professional": 3, "luxury": 1.5, "personal": 0},
    "öğretmen": {"educational": 2.5, "practical": 2, "personal": 0.5}
}
```

#### 2B: Occasion Boosts
```python
OCCASION_BOOSTS = {
    "doğum günü": 1.5,           # Tüm kategorilerde boost
    "sevgililer günü": 2.0,      # Özellikle personal
    "yılbaşı": 1.3,             
    "geçmiş olsun": 1.2,         # Konfor ürünleri
    "özür dileme": 1.8           # Lüks/özel
}
```

#### 2C: Personality-Trait Matching
- Question 8 (Sunday habit) → kategorileri match et
- Question 9 (toxic trait) → spesifik ürünler match et
- Question 10 (zodiac) → algoritma tags'ini boost et

#### 2D: Color Affinity Scoring
- Renk tercihinin product'a eşleşme derecesi
- Title, tags, attributes'te renk arama

---

### KATMAN 3: User Profile Enrichment
**Hedef**: Questions'dan %100 signal extraction

**Eylemler**:
- [ ] Question 7 → Personality color profile (cool/warm/vibrant/soft)
- [ ] Question 8 → Lifestyle tag (homebody/adventurer/social/creative)
- [ ] Question 9 → Specific product needs (thermal/coffee/organization/music/tech)
- [ ] Question 10 → Zodiac archetype boosts
- [ ] Age range → Product appropriateness filtering

**Çıktı**:
```python
enriched_user_profile = {
    "relationship": "sevgili",
    "age_range": "25-34",
    "gender": "kadın",
    "occasion": "doğum günü",
    "budget": 2500,
    "budget_min": 2000,
    
    # Core interests
    "interests": ["kozmetik", "moda", "café"],
    
    # Enriched signals
    "personality_colors": ["pastel", "pembe", "lila"],
    "color_temp": "warm",
    "personality_type": "soft_romantic",
    "lifestyle": "social_trendy",
    "specific_needs": ["café_culture", "selfcare", "fashion_conscious"],
    "zodiac": "terazi",
    "zodiac_traits": ["artistic", "aesthetic", "balanced"],
}
```

---

### KATMAN 4: Product Attribute Extraction
**Hedef**: Product tarafında richer data

**Eylemler**:
- [ ] PostgreSQL queries'ini optimize et (attribute extraction)
- [ ] Color, material, size, target_age, gender, occasion_fit taşı
- [ ] Brand personality classify et (luxury/casual/premium/budget)
- [ ] Product occasion fitness score'u hesapla

---

### KATMAN 5: Semantic Matching Enhancements
**Hedef**: TF-IDF yerine semantic similarity

**Eylemler**:
- [ ] Embedding similarity score'unu 2x weight ver (0.4 → 0.6)
- [ ] Rule score normalization'ı geliştir
- [ ] Cross-product diversity boost (farklı categories/brands tercih et)

**Yeni Formula**:
```
final_score = 0.3 * rule_score + 0.5 * embedding_score + 0.2 * contextual_boost
```

---

### KATMAN 6: Confidence & Explainability
**Hedef**: Daha iyi user trust

**Eylemler**:
- [ ] Confidence score (0-1) hesapla her tavsiye için
- [ ] Rich, personalized reasoning generate et Turkish'de
- [ ] Why score factors daha detaylı açıkla

---

## 📊 Beklenen İyileştirmeler

| Metrik | Mevcut | Hedef | Artış |
|--------|--------|-------|-------|
| Relevance Score (avg) | 0.62 | 0.82 | +32% |
| Relationship Fit | 0.55 | 0.85 | +55% |
| Occasion Fit | 0.50 | 0.80 | +60% |
| Personality Fit | 0.00 | 0.75 | +∞ |
| Budget Accuracy | 0.90 | 0.97 | +8% |

---

## 🔧 Implementation Order

1. **Embedding Model Switch** (5 min)
2. **User Profile Enrichment** (15 min)
3. **Dynamic Weight Multipliers** (20 min)
4. **Personality-Based Scoring** (20 min)
5. **Product Attributes & Optimization** (25 min)
6. **Testing & Validation** (15 min)

**Total: ~100 minutes of focused development**

---

## 📝 Files to Modify

- `scripts/recommender_engine.py` - Core logic
- `api/main.py` - API improvements
- `scripts/requirements.txt` - Add new models

---

## ✅ Success Criteria

- [ ] API returns structured recommendations with confidence
- [ ] Relationship-specific results demonstrable (wife vs. boss)
- [ ] Personality traits influence recommendations
- [ ] Occasion-specific boosts working
- [ ] Budget filtering more accurate
- [ ] Response time < 2s
