# Gift Recommender Kurulum Rehberi

Bu rehberin amacı: **kullanıcının localinde hazır DB olmadan**, tek komutla dolu PostgreSQL’i ayağa kaldırmak ve ardından çalışan API’ye sahip olmak.

## Gereksinimler

- Docker
- Docker Compose
- (Opsiyonel) Python 3.10+ (API’yi local çalıştırmak için)

## 1) Dolu veritabanını ayağa kaldırma (tek komut)

Repo kökünde çalıştır:

```bash
docker compose up -d
```

Bu komut:
- `init.sql` dosyasını ilk kurulumda otomatik çalıştırır
- veritabanını tüm kayıtlarıyla yükler
- PostgreSQL’i `localhost:5432` üzerinde açar

> İlk açılışta `init.sql` büyük olduğu için biraz zaman alabilir.

Sağlık kontrolü:

```bash
docker compose ps
docker compose logs -f postgres
```

`database system is ready to accept connections` gördüğünde DB hazırdır.

## 2) API’yi çalıştırma

### Seçenek A (Önerilen): API’yi Docker ile çalıştır

```bash
docker build -t gift-recommender-api:local -f Dockerfile .
docker run -d --name gift_recsys_api -p 8000:8000 -e DB_HOST=host.docker.internal gift-recommender-api:local
```

API endpoint:
- `http://localhost:8000`

### Seçenek B: API’yi local Python ile çalıştır

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
DB_HOST=localhost uvicorn api.main:app --host 0.0.0.0 --port 8000
```

## 3) Hızlı doğrulama

DB bağlantı bilgileri:
- Host: `localhost`
- Port: `5432`
- Database: `gift_recommender`
- User: `gift_admin`
- Password: `secure_password_123`

API health kontrol:

```bash
curl http://localhost:8000/api/questions
```

## 4) Durdurma / Temizleme

Sadece servisleri durdur:

```bash
docker compose down
docker rm -f gift_recsys_api 2>/dev/null || true
```

DB verisini de sil (tam reset):

```bash
docker compose down -v
docker rm -f gift_recsys_api 2>/dev/null || true
```
