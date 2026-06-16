# Sprint 6 - Edge Case & Stability Test Report

Generated: 2026-06-17 00:29:04

## Summary

- PASS: 6
- FAIL: 0

## Test #1: S6-E1 | Empty answers should not crash

**Status:** PASS

HTTP status: 200  
API status: success  
Result count: 5  
Expected minimum results: 1

### Selected Answers
- Empty or unmatched answers

### Recommendations
| # | Product | Price | Brand | Category | Score | Confidence |
|---|---------|-------|-------|----------|-------|------------|
| 1 | KOBINA I Erkek Beyaz Tişört | 399.9 | Slazenger | erkek > spor & outdoor > T-shirt | 0.133 | 0.1 |
| 2 | Team Icon 23 Forma | 1049.0 | adidas | erkek > spor & outdoor > T-shirt | 0.132 | 0.1 |
| 3 | Oversize Mor Hoodie - Unisex | 639.2 | MBEY1989 | erkek > giyim > Sweatshirt | 0.13 | 0.1 |
| 4 | Z.n.e. Full-zip Kapüşonlu Üst | 4449.04 | adidas | spor & outdoor > spor üst giyim > Sweatshirt | 0.13 | 0.1 |
| 5 | Su Sporu Ayakkabısı | 850.0 | MY SUPPORT | ayakkabı & çanta > erkek ayakkabı > Deniz Ayakkabısı | 0.124 | 0.1 |

---

## Test #2: S6-E2 | Only gender selected

**Status:** PASS

HTTP status: 200  
API status: success  
Result count: 5  
Expected minimum results: 1

### Selected Answers
- **cinsiyeti_nedir:** Kadın

### Recommendations
| # | Product | Price | Brand | Category | Score | Confidence |
|---|---------|-------|-------|----------|-------|------------|
| 1 | Laila Kadın Kürk | 13094.03 | Guess | kadın > giyim > Palto | 0.368 | 0.1 |
| 2 | Vanna Kadın Kürk | 11760.0 | Guess | kadın > giyim > Palto | 0.367 | 0.1 |
| 3 | Kadın Gri Kemer | 149.95 | Colin’s | kadın > aksesuar & çanta > Kemer | 0.361 | 0.1 |
| 4 | Kadın Atkı C6866AX24WN | 274.99 | Defacto | kadın > aksesuar & çanta > Atkı | 0.358 | 0.1 |
| 5 | Kadın ceket | 1000.0 | KEJAN TEKSTİL | kadın > giyim > Kot Ceket | 0.356 | 0.1 |

---

## Test #3: S6-E3 | Only budget selected

**Status:** PASS

HTTP status: 200  
API status: success  
Result count: 5  
Expected minimum results: 1

### Selected Answers
- **bütçe_aralığın_nedir:** 500 - 1.000 TL

### Recommendations
| # | Product | Price | Brand | Category | Score | Confidence |
|---|---------|-------|-------|----------|-------|------------|
| 1 | 500 gr 0.01 Tam Hassas Kuyumcu Eczane Terazisi | 695.0 | Brader | kitap & kırtasiye & hobi > ofis > Yazarkasa ve Terazi | 0.474 | 0.73 |
| 2 | 1000 TL+200 TL Hediye Puan | 1000.0 | TikTak | erkek > elektronik > Hediye Kartları | 0.465 | 0.65 |
| 3 | 500gr 0.01 Tam Hassas Terazi Eczane Kuyumcu Modeli | 645.0 | Brader | kitap & kırtasiye & hobi > ofis > Yazarkasa ve Terazi | 0.453 | 0.73 |
| 4 | 500 Versatil Kalem 0.5 mm Siyah 1904725 | 564.9 | Genel Markalar | kitap & kırtasiye & hobi > kalem > Kurşun Kalem | 0.452 | 0.73 |
| 5 | 250 Zımba Teli 1000 Li 23/6 (10 Paket) | 510.21 | Delta | kitap & kırtasiye & hobi > ofis > Zımba & Delgeç | 0.444 | 0.73 |

---

## Test #4: S6-E4 | Conflicting signals: erkek + kozmetik

**Status:** PASS

HTTP status: 200  
API status: success  
Result count: 5  
Expected minimum results: 1

### Selected Answers
- **cinsiyeti_nedir:** Erkek
- **hangi_yaş_aralığında:** 25 - 34
- **bu_hediyeyi_hangi_özel_durum_için_alıyorsun:** Doğum Günü
- **bütçe_aralığın_nedir:** 1.000 - 2.500 TL
- **temel_ilgi_alanları_neler:** Kozmetik & Kişisel Bakım (Algoritma: parfüm, kozmetik, cilt bakım, makyaj, kişisel bakım, ruj, fondöten, göz kalemi, maskara, allık, makyaj seti, saç bakım)

### Recommendations
| # | Product | Price | Brand | Category | Score | Confidence |
|---|---------|-------|-------|----------|-------|------------|
| 1 | Ares EDP Meyveli Erkek Parfüm 100 ml çarkıfelek şeftali ahududu notalı | 1592.0 | Frederic Patric | erkek > kişisel bakım > Parfüm | 1.052 | 1.0 |
| 2 | Narkotik Edp 100 ml Erkek Parfüm | 1179.4 | Soel Parfüm | erkek > kişisel bakım > Parfüm | 1.038 | 1.0 |
| 3 | Sumptuous Extreme Maskara Işıltılı Bakışlar Seti - Maskara + Göz Kalemi + Göz Kremi 5ml | 1980.0 | Estee Lauder | kozmetik > makyaj > Makyaj Seti | 0.989 | 1.0 |
| 4 | 12 Parça Premium Makyaj Seti 5’li Nude Ruj BB Fondöten Maskara Fırça Törpü Hediye Çantalı | 1200.0 | KYLA | kozmetik > makyaj > Makyaj Seti | 0.987 | 1.0 |
| 5 | EDT 125 ml + Deospray 200 ml Erkek Parfüm Seti | 1395.0 | Pino Silvestre | kozmetik > parfüm & deodorant > Parfüm Setleri | 0.966 | 1.0 |

---

## Test #5: S6-E5 | Very strict low slider budget

**Status:** PASS

HTTP status: 200  
API status: success  
Result count: 5  
Expected minimum results: 0

### Selected Answers
- **kime_hediye_alıyorsun:** Yakın Arkadaş
- **cinsiyeti_nedir:** Belirtmek İstemiyorum / Unisex
- **hangi_yaş_aralığında:** 18 - 24
- **bu_hediyeyi_hangi_özel_durum_için_alıyorsun:** Doğum Günü
- **temel_ilgi_alanları_neler:** Teknoloji & Elektronik (Algoritma: elektronik, teknoloji, bilgisayar, telefon, kulaklık, tablet, akıllı saat)

### Recommendations
| # | Product | Price | Brand | Category | Score | Confidence |
|---|---------|-------|-------|----------|-------|------------|
| 1 | Masaüstü Telefon ve Tablet Tutacağı Katlanabilir Yükseklik Ayarlı Holder | 249.9 | ProNorth | elektronik > telefon > Araç İçi Telefon Tutucu | 1.039 | 1.0 |
| 2 | Koltuk Arkası Ayarlanabilir Tablet Telefon Tutucu | Araç Arka Koltuk Telefon Tablet Tutucu | 299.0 | PFU Pratik Faydalı Ürünler | elektronik > telefon > Araç İçi Telefon Tutucu | 1.037 | 1.0 |
| 3 | Tüm Dokunmatik Cihazlarla Uyumlu Akıllı Tahta - Tablet - Telefon Dokunmatik Kalemi Siyah | 59.9 | ARABULALACA | elektronik > elektronik aksesuarlar > Bilgisayar Aksesuar | 1.037 | 1.0 |
| 4 | Tüm Dokunmatik Cihazlarla Uyumlu Akıllı Tahta - Tablet - Telefon Dokunmatik Kalemi Siyah | 39.99 | Fibaks | elektronik > elektronik aksesuarlar > Bilgisayar Aksesuar | 1.032 | 1.0 |
| 5 | Kulak Üstü Mikrofonlu Extra Bass Kulaklık Telefon, Tv. Tablet Ve Gaming Uyumlu, Mdr-xb450 Beyaz | 290.0 | İlkDağ | elektronik > oyunculara özel > Oyuncu Kulaklığı | 0.942 | 1.0 |

---

## Test #6: S6-E6 | High limit request

**Status:** PASS

HTTP status: 200  
API status: success  
Result count: 20  
Expected minimum results: 1

### Selected Answers
- **kime_hediye_alıyorsun:** Yakın Arkadaş
- **cinsiyeti_nedir:** Belirtmek İstemiyorum / Unisex
- **hangi_yaş_aralığında:** 25 - 34
- **bu_hediyeyi_hangi_özel_durum_için_alıyorsun:** Doğum Günü
- **bütçe_aralığın_nedir:** 1.000 - 2.500 TL
- **temel_ilgi_alanları_neler:** Teknoloji & Elektronik (Algoritma: elektronik, teknoloji, bilgisayar, telefon, kulaklık, tablet, akıllı saat)

### Recommendations
| # | Product | Price | Brand | Category | Score | Confidence |
|---|---------|-------|-------|----------|-------|------------|
| 1 | Bluetooth Katlanabilir Klavye Telefon Tablet Pc Uyumlu Touch Pad | 1399.0 | TECHNOMEN | elektronik > elektronik aksesuarlar > Bilgisayar Aksesuar | 1.014 | 1.0 |
| 2 | Pn-3080 Telefon Tablet Apple Ipad Ve Ipad Pro Kalem | 2390.0 | Mcdodo | elektronik > bilgisayar & tablet > Grafik Tablet | 0.941 | 1.0 |
| 3 | Telefon Tablet Switch Dönüştürücü Bluetooth Oyun Kolu Gamepad D6 | 1120.88 | XİRA | elektronik > oyunculara özel > Konsol Aksesuarları | 0.926 | 1.0 |
| 4 | HNRLISHP Cep Boyutu Kablosuz Bluetooth Klye Telefon ve (163319) Tablet Uyumlu | 1001.0 | ZERO LAND | elektronik > bilgisayar & tablet > Klavye | 0.913 | 0.98 |
| 5 | HERŞEYTREND Dijital Yazı Tahtası LCD Tablet Çizim SK-011 | 1012.67 | HRŞYTREND | elektronik > bilgisayar & tablet > Grafik Tablet | 0.91 | 1.0 |
| 6 | Cep Boyutu Kablosuz Bluetooth Klavye Telefon ve Tablet Uyumlu | 1103.9 | EASERA TİCARET | elektronik > bilgisayar & tablet > Klavye | 0.907 | 0.98 |
| 7 | Iphone 11 Pro Max Uyumlu Dtno1 Watch 7 Pro Max Akıllı Saat + Tws Airpods 3.nesil Bluetooth Kulaklık | 1399.99 | BGGTech | erkek > elektronik > Akıllı Saat | 0.903 | 1.0 |
| 8 | Watch Hx Pro Kordon Hediyeli 46mm Akıllı Saat Iphone Ve Android Tüm Telefonlara Uyumlu | 1755.0 | SEYUWATCH | elektronik > giyilebilir teknoloji > Akıllı Saat | 0.902 | 1.0 |
| 9 | Esnek Boyun Telefonu Tutucu Masaüstü Telefon Tutacağı Vlog, Gezi, Canlı Yayın, Ürün Tanıtım Tutacağı | 1299.0 | Asfal | elektronik > telefon > Araç İçi Telefon Tutucu | 0.898 | 1.0 |
| 10 | Berry Beyaz 3x 120mm ARGB Fanlı mATX Akvaryum Gaming Bilgisayar Kasası Powersız | 1599.0 | Strong | elektronik > bilgisayar & tablet > Bilgisayar Bileşenleri | 0.895 | 1.0 |

---

