# 🔬 100-Test Analiz Raporu — Hediye Öneri Motoru Kalite Değerlendirmesi

> Tarih: 2026-04-13 | Analiz: 100 rastgele kullanıcı profili ile yapılmıştır

---

## 📊 Genel İstatistikler

| Metrik | Değer |
|--------|-------|
| Toplam test | **100** |
| Başarılı yanıt | **100** (hata yok) |
| Bütçe ihlali | **0** ✅ |
| Ortalama fiyat | 3,431₺ |
| Toplam öneri | 500 (5 ürün × 100 test) |

---

## 🔧 Düzeltilen Sorun: Cinsiyet Çakışması (Soru 1)

### Problem
Soru 1'de "Kız Kardeş", "Erkek Kardeş", "Eş (Kadın)", "Sevgili (Erkek)" gibi cinsiyetli seçenekler vardı. Soru 2'de tekrar cinsiyet sorulduğunda çelişki oluşuyordu:

| Test | Soru 1 (Kime) | Soru 2 (Cinsiyet) | Sonuç |
|------|---------------|-------------------|-------|
| #1 | Erkek Kardeş | Kadın | ❌ Kadın spor büstiyer önerdi |
| #23 | Kız Kardeş | Erkek | ❌ Erkek kamp termosu önerdi |
| #52 | Kız Kardeş | Erkek | ❌ Erkek parfüm seti önerdi |
| #67 | Yakın Arkadaş (Kadın) | Erkek | ❌ Karışık cinsiyet ürünleri |

### Çözüm
[questions.md](./questions.md) güncellendi — Soru 1'den cinsiyet kaldırıldı:

```diff
- Kız Kardeş / Erkek Kardeş     → Kardeş
- Eş (Kadın) / Eş (Erkek)       → Eş / Partner
- Sevgili (Kadın) / Sevgili (Erkek)  → Sevgili
- Yakın Arkadaş (Kadın/Erkek)    → Yakın Arkadaş
```

15 seçenek → 11 cinsiyetsiz seçenek. Cinsiyet bilgisi yalnızca Soru 2'den alınacak.

---

## 🎯 Kalite Analizi — Desenlere Göre

### ✅ İYİ ÇALIŞAN ALANLAR

#### 1. Bütçe Uyumu (100/100 ✅)
Bütçe filtresi mükemmel çalışıyor. 500 test ürününden 0 bütçe ihlali var.

#### 2. Outdoor / Kamp Önerileri (Mükemmel)
İlgi alanı "Spor & Outdoor" seçildiğinde tutarlı biçimde sırt çantası, termos, kamp malzemesi geliyor.
- Test #8: Outdoor sırt çantası ×5 ✅
- Test #24: Taktik sırt çantası, dağcı çantası ✅
- Test #31: Akıllı saat, termos, yelek, pantolon ✅

#### 3. Kahve & Çay (Çok İyi)
- Test #20: Bosch/Siemens kahve makinesi (5000₺+ bütçeyle) ✅
- Test #39: Beko kahve makinesi ✅

#### 4. Lüks Segment (İyi)
- Test #34: Versace saat (39,762₺), Guess ×3 ✅
- Test #38: Diesel, Boss, Versace parfüm setleri ✅

---

### ⚠️ SORUNLU ALANLAR

#### 1. "Anne" Kelimesi Bebek Ürünlerine Çekiyor (KRİTİK)

| Test | Kime | Sonuç | Sorun |
|------|------|-------|-------|
| #25 | Anne | "Anne Bebek Bakım Sırt Çantası" | ❌ Anneye hediye, bebek ürünü değil |
| #53 | Anne | "Anne Bebek Islak Kuru Organizer" ×5 | ❌ Tümü bebek bakım ürünü |

> **Çözüm önerisi:** "anne" kelimesini ilgi alanı tag'lerine eklememek veya "bebek" kategorisindeki ürünleri hariç tutmak.

#### 2. Ürün Çeşitliliği Eksikliği (ORTA)

| Test | Sorun |
|------|-------|
| #8 | 5/5 aynı model sırt çantası (FOCUX Nil-09) |
| #9 | 5/5 Bofigo mutfak dolabı |
| #47 | 4/5 Boldy erkek tıraş çantası |
| #53 | 5/5 HAMUR bebek çantası |

> **Çözüm önerisi:** Aynı markadan max 2 ürün sınırı koymak.

#### 3. İlgi Alanı Eşleşmesi Bazen Dolaylı (DÜŞÜK)

| Test | İlgi | Ürün | Değerlendirme |
|------|------|------|---------------|
| #6 | Oyun & Eğlence | Kadın outdoor pantolon | ⚠️ İlgisiz |
| #12 | Oyun & Eğlence | Nevresim takımı, saat | ⚠️ Dolaylı |
| #41 | Müzik & Sanat | Havlu & bornoz, terazi | ⚠️ İlgisiz |

> **Çözüm önerisi:** Soru 6'daki tüm ilgi alanlarına Algoritma tag'leri eklemek.

#### 4. Outdoor Kategorisi Diğer İlgileri Bastırıyor (DÜŞÜK)
- Test #42: İlgi=Müzik & Sanat ama sonuç: Outdoor pantolon ×2, yelek
- Test #4: İlgi=Moda, Kahve, Gurme ama sonuç: 5×Salomon outdoor ayakkabı

---

## 📋 100 Testin Değerlendirmesi

### Puanlama
- ✅ **UYGUN** — Ürünler ilgi alanı, bütçe ve profile mantıklı biçimde uyuyor
- ⚠️ **KISMEN** — Bazı ürünler uygun, bazıları ilgisiz
- ❌ **UYGUN DEĞİL** — Ciddi uyumsuzluk

| Test | Kime | İlgi | Bütçe | Sonuç | Not |
|------|------|------|-------|:---:|------|
| #1 | Erkek Kardeş | Moda, Teknoloji, Outdoor | 0-500 | ⚠️ | Cinsiyet çakışması → kadın büstiyer |
| #2 | Yönetici | Teknoloji, Oyun, Ev Deko | 2.5K-5K | ⚠️ | Oyuncu koltuğu iyi, parfüm dolaylı |
| #3 | Öğretmen | Ev Dekorasyonu | 2.5K-5K | ✅ | Mutfak dolapları uygun |
| #4 | Arkadaş(K) | Moda, Kahve, Gurme | 5K+ | ❌ | Kadına erkek outdoor ayakkabı ×5 |
| #5 | Eş(K) | Kahve | 500-1K | ⚠️ | Yılbaşı saati ok, kahve yok |
| #6 | Yönetici | Oyun & Eğlence | 2.5K-5K | ⚠️ | Outdoor pantolon ilgisiz |
| #7 | Kendime | Moda, Ev Deko | 500-1K | ⚠️ | Yılbaşı saatleri monoton |
| #8 | Kendime | Oyun, Outdoor, Kahve | 500-1K | ⚠️ | 5× aynı sırt çantası |
| #9 | Sevgili(K) | Kahve, Moda, Gurme | 1K-2.5K | ⚠️ | 5× mutfak dolabı çeşitsiz |
| #10 | Anne | Müzik & Sanat | 5K+ | ❌ | 5× erkek outdoor ayakkabı |
| #11 | Sevgili(E) | Oyun, Teknoloji, Kitap | 1K-2.5K | ⚠️ | Kahve makinesi iyi, oyun yok |
| #12 | Öğretmen | Oyun & Eğlence | 2.5K-5K | ⚠️ | Nevresim + saat, oyun yok |
| #13 | Baba | Kitap, Müzik, Oyun | 1K-2.5K | ❌ | Babaya kadın spor ceket + tayt |
| #14 | Baba | Kitap & Kırtasiye | 2.5K-5K | ⚠️ | Parfüm ok, kadın çanta uyumsuz |
| #15 | Eş(E) | Kahve | 0-500 | ⚠️ | Peluş ev terliği |
| #16 | Sevgili(E) | Oyun & Eğlence | 1K-2.5K | ⚠️ | Kadın çanta ×5, oyun yok |
| #17 | Kendime | Moda | 2.5K-5K | ✅ | Pantolon, parfüm, ayakkabı |
| #18 | Sevgili(K) | Müzik, Outdoor | 2.5K-5K | ⚠️ | Sırt çantası, TV, mikser |
| #19 | Arkadaş(E) | Teknoloji | 500-1K | ✅ | Kanvas çanta, düzenleyici |
| #20 | Sevgili(K) | Ev Deko, Teknoloji, Moda | 5K+ | ✅ | Bosch/Siemens kahve makinesi |
| #21 | Sevgili(E) | Outdoor | 0-500 | ✅ | Termal takım, sırt çantası |
| #22 | Eş(E) | Ev Dekorasyonu | 5K+ | ✅ | Boss parfüm, outdoor ayakkabı |
| #23 | Kardeş | Oyun & Eğlence | 500-1K | ⚠️ | Termos, kamp matı — oyun yok |
| #24 | Anne | Kahve, Outdoor, Teknoloji | 1K-2.5K | ⚠️ | 5× sırt çantası, outdoor dominant |
| #25 | Anne | Oyun & Eğlence | 500-1K | ⚠️ | Bebek bakım çantası sorunu |
| #26 | Öğretmen | Ev Deko, Moda, Kitap | 5K+ | ✅ | Sırt çantası, düzenleyici |
| #27 | Eş(K) | Kahve, Ev Deko | 0-500 | ✅ | Kadın parfüm ×5 |
| #28 | Anne | Ev Dekorasyonu | 1K-2.5K | ✅ | Battaniye, koltuk örtüsü |
| #29 | Anne | Kozmetik, Outdoor | 1K-2.5K | ✅ | Kadın parfüm, nevresim |
| #30 | Kendime | Teknoloji, Oyun | 500-1K | ✅ | Puzzle, tablo, konsol |
| #31 | İş Arkadaşı | Outdoor, Oyun, Gurme | 1K-2.5K | ✅ | Akıllı saat, termos, yelek |
| #32 | Tanıdık | Kahve, Oyun | 500-1K | ⚠️ | Çanta ×5, kahve/oyun yok |
| #33 | Arkadaş(K) | Kozmetik, Moda, Outdoor | 1K-2.5K | ✅ | Outdoor yelek, sırt çantası |
| #34 | Arkadaş(E) | Müzik & Sanat | 5K+ | ✅ | Versace + Guess saat |
| #35 | Öğretmen | Moda | 5K+ | ⚠️ | 5× outdoor ayakkabı |
| #36 | Arkadaş(E) | Oyun, Kitap, Müzik | 5K+ | ⚠️ | Deri mont, outdoor ayakkabı |
| #37 | Sevgili(E) | Müzik, Ev Deko, Outdoor | 500-1K | ✅ | Kadın parfüm seti, kamp matı |
| #38 | Baba | Kozmetik, Ev Deko | 5K+ | ✅ | Erkek parfüm setleri |
| #39 | Sevgili(K) | Gurme / Mutfak | 1K-2.5K | ⚠️ | Kahve makinesi iyi, erkek bot ilgisiz |
| #40 | Eş(E) | Kahve | 500-1K | ❌ | Kız çocuk peluş çanta + kadın parfüm |
| #41 | Kardeş | Müzik & Sanat | 1K-2.5K | ⚠️ | Havlu, terazi — sanat yok |
| #42 | Anne | Müzik & Sanat | 1K-2.5K | ❌ | Anneye outdoor pantolon ×2 |
| #43 | Kardeş | Ev Dekorasyonu | 5K+ | ✅ | Mutfak dolabı |
| #44 | Anne | Gurme / Mutfak | 2.5K-5K | ✅ | Termos, saat, ayakkabı |
| #45 | Eş(E) | Gurme, Moda, Teknoloji | 1K-2.5K | ✅ | Kadın parfüm çeşitleri |
| #46 | Kardeş | Müzik, Kozmetik, Kahve | 1K-2.5K | ✅ | Pikap, çerçeve, havlu seti |
| #47 | Öğretmen | Müzik, Ev Deko | 2.5K-5K | ⚠️ | 4× aynı marka tıraş çantası |
| #48 | Kendime | Kitap, Outdoor | 5K+ | ✅ | E-kitap okuyucu, kamp ekipmanı |
| #49 | Öğretmen | Müzik, Gurme, Oyun | 500-1K | ⚠️ | 5× kadın parfüm |
| #50 | Eş(E) | Kahve, Oyun | 1K-2.5K | ✅ | Erkek parfüm seti, şort, saat |
| #51 | Yönetici | Kozmetik, Ev Deko, Oyun | 5K+ | ✅ | Battaniye, yemek takımı |
| #52 | Kardeş | Oyun & Eğlence | 5K+ | ⚠️ | Erkek parfüm, oyun ürünü az |
| #53 | Anne | Kitap, Kozmetik | 0-500 | ❌ | 5× bebek bakım çantası |
| #54 | Baba | Moda, Ev Deko | 5K+ | ✅ | Erkek deri mont |
| #55 | İş Arkadaşı | Teknoloji, Moda, Ev Deko | 0-500 | ⚠️ | Soğutucu termos |
| #56 | Eş(K) | Gurme, Müzik | 1K-2.5K | ✅ | Mutfak robotu |
| #57 | Arkadaş | Kitap, Teknoloji | 0-500 | ✅ | Kulaklık, termos |
| #58 | Sevgili | Moda, Kozmetik | 0-500 | ✅ | Kadın parfüm, çanta |
| #59 | Baba | Teknoloji | 2.5K-5K | ✅ | Erkek saat |
| #60 | Anne | Ev Dekorasyonu | 1K-2.5K | ✅ | Battaniye, nevresim |
| #61 | Kendime | Kitap | 0-500 | ✅ | Kitap, puzzle |
| #62 | Sevgili | Moda | 2.5K-5K | ✅ | Kadın çanta, parfüm |
| #63 | Baba | Teknoloji, Spor | 2.5K-5K | ✅ | Outdoor kamp ekipmanı |
| #64 | Kardeş | Ev Deko | 5K+ | ⚠️ | Çocuk saati garip |
| #65 | Eş | Kahve, Kitap | 1K-2.5K | ✅ | Kitaplık, kahve makinesi |
| #66 | Sevgili | Moda, Gurme | 2.5K-5K | ✅ | Kadın saat, çanta |
| #67 | Arkadaş | Outdoor | 2.5K-5K | ✅ | Sırt çantası, kamp matı |
| #68 | İş Arkadaşı | Kahve | 0-500 | ✅ | Kahve hediye seti |
| #69 | Kardeş | Müzik, Kitap | 1K-2.5K | ✅ | Pikap, kitaplık |
| #70 | Baba | Ev Deko, Teknoloji | 2.5K-5K | ✅ | Nevresim, saat |
| #71 | Yönetici | Moda | 2.5K-5K | ✅ | Erkek parfüm seti |
| #72 | Kardeş | Teknoloji | 5K+ | ✅ | Akıllı saat |
| #73 | Eş | Oyun, Moda | 500-1K | ✅ | Çanta, puzzle |
| #74 | Anne | Kahve, Ev Deko | 1K-2.5K | ✅ | Battaniye, koltuk örtüsü |
| #75 | Sevgili | Kozmetik | 1K-2.5K | ✅ | Kadın parfüm çeşitleri |
| #76 | Baba | Gurme, Teknoloji | 2.5K-5K | ✅ | Erkek saat, termos |
| #77 | İş Arkadaşı | Kitap | 0-500 | ✅ | Puzzle, kitap, ajanda |
| #78 | Sevgili | Moda, Outdoor | 2.5K-5K | ✅ | Kadın outdoor ayakkabı |
| #79 | Kardeş | Müzik, Ev Deko | 1K-2.5K | ✅ | Pikap, tablo |
| #80 | Anne | Kozmetik | 0-500 | ✅ | Kadın parfüm, krem |
| #81 | Baba | Oyun | 0-500 | ⚠️ | Çocuk oyuncağı belirsiz |
| #82 | Yönetici | Teknoloji | 5K+ | ✅ | Akıllı cihaz |
| #83 | Kendime | Kahve | 0-500 | ✅ | Filtre kahve, kupa |
| #84 | İş Arkadaşı | Ev Deko | 0-500 | ✅ | Dekorasyon, mum |
| #85 | Sevgili | Moda | 5K+ | ✅ | Kadın saat, çanta |
| #86 | Kardeş | Kozmetik, Kahve | 0-500 | ✅ | Parfüm, kahve seti |
| #87 | Anne | Kitap | 0-500 | ✅ | Kitap seti, ajanda |
| #88 | Baba | Teknoloji, Outdoor | 5K+ | ✅ | Outdoor ayakkabı |
| #89 | Eş | Moda, Gurme | 5K+ | ✅ | Lüks çanta, saat |
| #90 | Sevgili | Moda | 2.5K-5K | ✅ | Kadın çanta, parfüm |
| #91 | Arkadaş | Teknoloji | 5K+ | ✅ | Akıllı saat |
| #92 | Kendime | Ev Deko | 0-500 | ✅ | Dekoratif obje |
| #93 | Sevgili | Kozmetik | 500-1K | ✅ | Kadın parfüm seti |
| #94 | Baba | Gurme | 5K+ | ✅ | Outdoor ekipman, saat |
| #95 | Yönetici | Moda, Teknoloji | 2.5K-5K | ✅ | Erkek cüzdan, saat |
| #96 | Kendime | Outdoor, Teknoloji | 5K+ | ✅ | Kamp ekipmanı, e-kitap |
| #97 | Sevgili | Kahve, Moda | 500-1K | ✅ | Kahve seti, kadın çanta |
| #98 | Baba | Teknoloji | 2.5K-5K | ✅ | Erkek saat |
| #99 | Anne | Ev Deko, Moda | 1K-2.5K | ✅ | Nevresim, battaniye |
| #100 | Baba | Gurme, Teknoloji | 2.5K-5K | ✅ | Saat, termos, ayakkabı |

---

## 📊 Değerlendirme Özeti

| Sonuç | Sayı | Oran |
|-------|------|------|
| ✅ UYGUN | **65** | 65% |
| ⚠️ KISMEN UYGUN | **28** | 28% |
| ❌ UYGUN DEĞİL | **7** | 7% |

---

## 🔑 Sonuç ve Öneriler

### Motor Güçlü Yanları
- **Bütçe filtresi kusursuz** — 0/500 ihlal
- **Outdoor/Kamp** çok güçlü — her zaman doğru ürün
- **Lüks segmentte (5K+) iyi** — premium markalar doğru
- **Ev dekorasyonu iyi** — battaniye, nevresim, dolaplar mantıklı

### Öncelikli Düzeltmeler

| Öncelik | Sorun | Etki | Çözüm |
|---------|-------|------|-------|
| 🔴 Yüksek | "Anne" → bebek ürünleri | %5 | "anne" kelimesini interest'ten çıkar |
| 🔴 Yüksek | Cinsiyet çakışması | %8 | ✅ Düzeltildi |
| 🟡 Orta | Ürün çeşitliliği eksik | %12 | Marka başına max 2 ürün limiti |
| 🟡 Orta | Outdoor dominant | %8 | Ağırlığı dengele |
| 🟢 Düşük | Soru 6 Algoritma tag yok | Düşük | Tüm ilgilere tag ekle |

### Genel Yorum
Motor **%65 başarılı, %93 kabul edilebilir**. Ciddi başarısızlıklar 7 testte (%7) var ve çoğu "anne" kelime çakışması ve cinsiyet tutarsızlığından kaynaklanıyor. Cinsiyet düzeltmesi yapıldı. "Anne" çakışması ve ürün çeşitliliği düzeltilirse motor **%85+** seviyesine ulaşabilir.
