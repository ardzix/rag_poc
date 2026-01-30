# NOC RAG (POC) - Document Chat (Django + DRF + DeepSeek)

POC sistem chat berbasis dokumen. Dokumen yang di-upload user disuntikkan sebagai konteks ke LLM (tanpa vector DB) untuk memberikan pengalaman "RAG-like". API mengembalikan jawaban teks dan (opsional) konfigurasi chart untuk dirender oleh frontend via Chart.js.

Catatan: README ini mengkonsolidasikan informasi yang sebelumnya tersebar di beberapa file Markdown agar repo lebih rapi. Dokumentasi lain yang redundant sudah dihapus.

## Table of Contents

- [Fitur](#fitur)
- [Tech Stack](#tech-stack)
- [Quick Start (5 menit)](#quick-start-5-menit)
- [Konfigurasi](#konfigurasi)
- [Authentication (SSO)](#authentication-sso)
- [API](#api)
- [Swagger UI / ReDoc](#swagger-ui--redoc)
- [Seeding Sample Documents](#seeding-sample-documents)
- [Sample Queries](#sample-queries)
- [Testing Guide](#testing-guide)
- [Deployment (Production)](#deployment-production)
- [Arsitektur dan Struktur Project](#arsitektur-dan-struktur-project)
- [Changelog](#changelog)
- [Future Features](#future-features)

## Legacy Docs (Removed)

Dokumentasi terpisah (quickstart, swagger guide, seeding/testing guide, deployment, dll) sudah dihapus untuk menghindari inkonsistensi. Jika perlu, ambil dari riwayat git.

## Fitur

- Upload dokumen (PDF, DOCX, TXT) + ekstraksi teks otomatis
- Chat berbasis konteks dokumen user
- Output chart (Chart.js config) di payload response
- Integrasi autentikasi SSO (Bearer token)
- Chat history (opsional) untuk audit/demo

## Tech Stack

- Backend: Django 5 + Django REST Framework
- LLM: DeepSeek API
- Database: SQLite (dev) / PostgreSQL (prod)
- Auth: Bearer token dari SSO Arnatech
- Document extraction: PyPDF2, python-docx

## Quick Start (5 menit)

1) Install dependencies

```bash
pip install -r requirements.txt
```

2) Siapkan `.env`

Gunakan `env.template` sebagai referensi. Minimalnya:

```env
DEBUG=True
SECRET_KEY=django-insecure-dev-key-change-me
ALLOWED_HOSTS=localhost,127.0.0.1

DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

SSO_BASE_URL=https://sso.arnatech.id/api
SSO_VERIFY_TOKEN_ENDPOINT=/auth/token/verify/
```

3) Migrasi DB

```bash
python3 manage.py makemigrations
python3 manage.py migrate
```

4) (Opsional) Seed sample documents untuk testing cepat

```bash
python3 manage.py seed_documents --user-id=test-user-001 --clear
```

5) Run server

```bash
python3 manage.py runserver
```

Helper scripts (opsional):

- `setup.sh` menjalankan setup dasar (venv, install, migrate) sesuai kebutuhan lokal.
- `test_api.sh` contoh script untuk testing endpoint via curl.

URL penting saat dev:

- Swagger UI: `http://127.0.0.1:8000/swagger/`
- ReDoc: `http://127.0.0.1:8000/redoc/`
- Schema JSON: `http://127.0.0.1:8000/swagger.json`
- Root: `http://127.0.0.1:8000/` (redirect ke Swagger UI)

## Konfigurasi

Referensi lengkap ada di `env.template`. Variable yang penting:

```text
DEBUG, SECRET_KEY, ALLOWED_HOSTS

DB_ENGINE, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT

SSO_BASE_URL, SSO_VERIFY_TOKEN_ENDPOINT

DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL, DEEPSEEK_TIMEOUT

MAX_UPLOAD_SIZE_MB, DOCUMENT_CONTEXT_MAX_LENGTH

CORS_ALLOWED_ORIGINS
```

Catatan:

- PDF hasil scan (image-only) tidak akan bisa diekstrak tanpa OCR (out of scope POC).
- `DOCUMENT_CONTEXT_MAX_LENGTH` membatasi konteks yang disuntikkan ke LLM.

## Authentication (SSO)

Semua endpoint aplikasi memerlukan header:

```text
Authorization: Bearer <access_token>
```

SSO base: `https://sso.arnatech.id/api` (lihat `sso.json`).

Endpoint SSO yang relevan:

- `POST /auth/login/` (frontend login)
- `POST /auth/mfa/verify/` (jika MFA required)
- `POST /auth/token/refresh/` (frontend refresh access token)
- `POST /auth/token/verify/` (backend validate access token)

Contoh login SSO (email+password):

```bash
curl -X POST https://sso.arnatech.id/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"user@arnatech.id","password":"your-password"}'
```

Jika `mfa_required: true`, lanjut dengan endpoint MFA verify sesuai response SSO.

Catatan implementasi backend:

- Backend memvalidasi token via SSO `POST /auth/token/verify/`.
- Token result di-cache singkat (default: 60 detik) untuk mengurangi latency.
- `owner_user_id` diambil dari JWT payload (claim perlu disepakati: `user_id` / `sub`).

## API

Base URL (dev): `http://127.0.0.1:8000/api`

### Documents

- `POST /documents/` upload dokumen (multipart/form-data)
- `GET /documents/` list dokumen user
- `GET /documents/{id}/` detail dokumen (termasuk `content`)
- `DELETE /documents/{id}/` hapus dokumen

Upload dokumen:

```bash
curl -X POST http://127.0.0.1:8000/api/documents/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@sample_documents/laporan_q3_2025.txt" \
  -F "title=Laporan Kinerja Q3 2025"
```

### Chat

- `POST /chat/` kirim message dan dapat response
- `GET /chat/history` list chat history (tanpa trailing slash)

Chat request (payload disederhanakan):

```json
{
  "message": "Berapa target NPS Q3 2025 untuk Jawa Barat?",
  "conversation_id": "conv-123"
}
```

Catatan:

- Client hanya wajib mengirim `message`.
- Dokumen konteks diambil otomatis: semua dokumen milik user (`owner_user_id`) dari DB.
- Chart ditentukan otomatis dari keyword di message (lihat bagian Chart).

Response chat:

```json
{
  "text": "Berdasarkan dokumen ...",
  "chart": null
}
```

### Chart (Chart.js)

Jika chart terdeteksi dan data cukup, response akan menyertakan `chart` berupa konfigurasi Chart.js (frontend tinggal `new Chart(ctx, chart)`).

Contoh:

```json
{
  "text": "Berikut perbandingan target vs capaian NPS Q3 2025:",
  "chart": {
    "type": "bar",
    "data": {
      "labels": ["Juli", "Agustus", "September"],
      "datasets": [
        {"label": "Target", "data": [80, 82, 83]},
        {"label": "Capaian", "data": [78, 81, 84]}
      ]
    },
    "options": {"responsive": true}
  }
}
```

Chart auto-detect (heuristik keyword) umumnya mencakup: `chart`, `grafik`, `visualisasi`, `diagram`, `perbandingan`, `tren`, `line chart`, `pie chart`, `doughnut`.

### Error Codes

| Code | Meaning |
|------|---------|
| 200 | OK |
| 201 | Created |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (invalid/expired token) |
| 404 | Not Found |
| 413 | Payload Too Large (file > `MAX_UPLOAD_SIZE_MB`) |
| 415 | Unsupported Media Type (bukan PDF/DOCX/TXT) |
| 422 | Unprocessable Entity (gagal ekstraksi; mis. PDF scan) |
| 502 | Bad Gateway (error upstream DeepSeek) |

### Frontend Integration Example (JavaScript)

```javascript
// axios instance dengan Bearer token
const api = axios.create({
  baseURL: "http://127.0.0.1:8000/api",
  headers: { Authorization: `Bearer ${accessToken}` },
});

// Upload document
async function uploadDocument(file, title) {
  const formData = new FormData();
  formData.append("file", file);
  if (title) formData.append("title", title);
  const { data } = await api.post("/documents/", formData);
  return data;
}

// Send chat message (payload disederhanakan)
async function sendMessage(message, conversationId) {
  const payload = { message };
  if (conversationId) payload.conversation_id = conversationId;
  const { data } = await api.post("/chat/", payload);
  return data; // { text, chart }
}

// Render chart via Chart.js
function renderChart(chartConfig) {
  const ctx = document.getElementById("myChart").getContext("2d");
  return new Chart(ctx, chartConfig);
}
```

## Swagger UI / ReDoc

Swagger UI:

- `http://127.0.0.1:8000/swagger/`

Cara authorize Bearer token di Swagger:

1) Klik tombol "Authorize"
2) Masukkan: `Bearer <access_token>` (dengan prefix `Bearer `)
3) Jalankan endpoint dengan "Try it out"

ReDoc:

- `http://127.0.0.1:8000/redoc/`

## Seeding Sample Documents

Project menyediakan 3 sample documents di `sample_documents/`:

- `sample_documents/laporan_q3_2025.txt` (KPI report Q3 2025: NPS, CSI, revenue, churn, dll)
- `sample_documents/definisi_kpi.txt` (definisi dan formula KPI)
- `sample_documents/market_analysis_2025.txt` (market/kompetitor/market share/pricing)

Seed via management command:

```bash
python3 manage.py seed_documents --user-id=test-user-001 --clear
```

Catatan penting:

- Dokumen dan chat log di-filter berdasarkan `owner_user_id`.
- Jika hasil chat "tidak menemukan dokumen", kemungkinan `owner_user_id` dari token tidak match dengan `--user-id` yang dipakai saat seeding.

## Sample Queries

Gunakan ini untuk demo/testing. Semua query cukup dikirim ke `POST /api/chat/` dengan payload `{"message": "..."}`.

Tanpa chart:

1) "Apa itu NPS dan bagaimana cara menghitungnya?"
2) "Berapa target NPS Q3 2025 untuk Jawa Barat?"
3) "Apakah target NPS Q3 2025 tercapai?"
4) "Berapa total revenue Q3 2025?"
5) "Siapa kompetitor utama kami dan berapa market share mereka?"
6) "Berapa customer retention rate di Q3 2025?"
7) "Bagaimana employee satisfaction score Q3 2025?"
8) "Regional mana yang perform terbaik untuk NPS Q3?"
9) "Apa perbedaan antara NPS dan CSI?"
10) "Berapa churn rate per bulan di Q3 2025?"

Dengan chart:

11) "Buatkan grafik perbandingan target vs capaian NPS Jawa Barat Q3 2025" (bar)
12) "Tampilkan chart perbandingan target revenue vs actual revenue per bulan Q3" (bar)
13) "Buatkan grafik batang NPS September 2025 untuk semua regional" (bar)
14) "Visualisasikan jumlah customer baru per bulan Q3 dalam bentuk diagram" (bar)
15) "Buatkan line chart tren NPS Jawa Barat Q3 2025" (line)
16) "Tampilkan grafik garis perkembangan CSI selama Q3" (line)
17) "Visualkan tren churn rate Q3 2025 dengan line chart" (line)
18) "Buatkan grafik garis perbandingan tren NPS semua regional Q3" (multi-line)
19) "Show me the trend of employee satisfaction score Q3 as a line graph" (line)
20) "Buatkan pie chart untuk market share Q3 2025" (pie)
21) "Tampilkan diagram pie untuk distribusi customer kita berdasarkan segment" (pie)
22) "Visualisasikan distribusi jumlah client per regional dalam pie chart" (pie)
23) "Buatkan doughnut chart untuk kategori NPS (Promoters, Passives, Detractors)" (doughnut)
24) "Tampilkan doughnut chart untuk komponen revenue growth (new customers, upselling, retention)" (doughnut)

Kompleks:

25) "Berikan ringkasan lengkap performa Q3 2025 dibandingkan target"
26) "Analisis lengkap performa per regional dan berikan rekomendasi"
27) "Bagaimana posisi kami dibanding kompetitor dalam hal NPS, pricing, dan market share?"
28) "Berapa pertumbuhan revenue Q3 dan proyeksi untuk Q4?"
29) "Buatkan stacked bar chart untuk revenue breakdown per bulan (target dan actual)"
30) "Visualisasikan NPS dan CSI dalam satu grafik untuk melihat korelasi"

## Testing Guide

Quick test via Swagger:

1) Run server
2) Buka `http://127.0.0.1:8000/swagger/`
3) Login SSO untuk dapat token
4) Authorize token di Swagger
5) Upload sample docs (opsional)
6) Test `POST /api/chat/` dengan beberapa query dari "Sample Queries"

Checklist validasi utama:

- Response berbahasa Indonesia (kecuali user minta lain)
- Tidak hallucinate (angka harus sesuai dokumen)
- Jika data tidak ada di dokumen, jawab "tidak ditemukan" + minta dokumen/clarification
- `chart` hanya muncul jika user meminta visualisasi dan datanya cukup
- Chart format valid untuk Chart.js (type/data/options)

Error handling yang perlu dites:

- 401: token invalid/expired
- 413: file > `MAX_UPLOAD_SIZE_MB`
- 415: upload non PDF/DOCX/TXT
- 422: gagal ekstraksi (mis. PDF scan)
- 502: error dari DeepSeek

## Deployment (Production)

Untuk production, referensi langkah umum:

- Gunakan PostgreSQL
- Jalankan via gunicorn + reverse proxy (Nginx)
- Set `DEBUG=False`, `SECRET_KEY` kuat, `ALLOWED_HOSTS` benar, dan `CORS_ALLOWED_ORIGINS` sesuai domain FE
- Set `client_max_body_size` Nginx minimal sesuai `MAX_UPLOAD_SIZE_MB`

Contoh gunicorn:

```bash
gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --timeout 120
```

Catatan:
- Jika butuh referensi detail (systemd, Nginx, SSL, backup), gunakan template internal tim atau ambil dari riwayat git.

## Arsitektur dan Struktur Project

Struktur high level:

```text
noc_rag/
  config/      Django settings + swagger endpoints
  core/        authentication (SSO), deepseek service, document extractor
  documents/   CRUD dokumen + management command seeding
  chat/        chat endpoint + chat history + ChatLog
```

File penting:

- `core/authentication.py` (SSO auth + caching)
- `core/document_extractor.py` (extract PDF/DOCX/TXT)
- `core/deepseek_service.py` (prompt + call DeepSeek + parse JSON)
- `core/swagger_schemas.py` (Swagger examples/schemas)

## DeepSeek Integration Notes

Kontrak output dari LLM (disarankan ketat):

- Model mengembalikan 1 JSON object valid, tanpa markdown/code fence.
- JSON hanya boleh memiliki 2 key: `text` dan `chart`.
- `chart` harus `null` jika user tidak meminta visualisasi atau data tidak cukup.

Konteks dokumen disuntikkan sebagai blok:

```text
<DOC id="1" title="Judul Dokumen">
... isi dokumen ...
</DOC>
```

Catatan operasional:

- Limit konteks diatur oleh `DOCUMENT_CONTEXT_MAX_LENGTH`.
- Jika konteks terlalu panjang, trimming harus deterministik (mis. potong proporsional atau summary sederhana) agar output stabil.

## Changelog

Highlights (2026-01-30):

- Swagger UI + ReDoc + schema export
- Chat API payload disederhanakan: hanya `message` (+ `conversation_id` opsional)
- Auto-detect chart dari keyword message
- Dokumen konteks diambil otomatis dari DB (semua dokumen user)

Detail historis bisa diambil dari riwayat git.

## Future Features

Direncanakan (tidak dikerjakan sekarang):

- Speech-to-Text (STT) untuk input suara
- Text-to-Speech (TTS) untuk output suara
- Tagging dokumen
- Multi-turn conversation context yang lebih kuat
- RAG penuh (embedding + vector database + retrieval)
