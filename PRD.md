# PRD — POC Chat RAG-like (Django + DRF + DeepSeek)

## 1. Latar Belakang
Kebutuhan produk sebenarnya adalah RAG. Namun untuk POC, infrastruktur RAG terlalu mahal. Solusi POC: gunakan API DeepSeek saja dengan memasukkan konten dokumen sebagai konteks ke LLM, sehingga user merasakan pengalaman “seolah‑olah RAG”.

## 2. Tujuan
- Mendemokan kemampuan query berbasis dokumen melalui chat.
- Mendukung response terstruktur untuk chart (Chart.js) via payload API.
- Memvalidasi alur upload dokumen → jadi konteks → jawaban chat.

## 3. Non‑Tujuan
- Tidak membangun pipeline RAG full (vector DB, embedding, retrieval).
- Tidak membangun autentikasi/role yang kompleks (hanya integrasi SSO + Bearer token).
- Tidak membangun STT/TTS (disiapkan sebagai future features).

## 4. Ruang Lingkup Fitur
### 4.1 Upload Dokumen (Admin/POC User)
- User mengupload dokumen melalui endpoint API.
- Dokumen disimpan ke DB sebagai teks hasil ekstraksi agar bisa digunakan sebagai konteks.
- Format dokumen untuk POC: PDF, DOCX, TXT.
- Batasan POC (disarankan):
  - Max size upload: 10 MB per file (lebih dari itu → 413).
  - Jika ekstraksi gagal → 422 dengan pesan error yang jelas.
  - Normalisasi teks: hilangkan karakter non-printable, rapikan whitespace.
  - PDF hasil scan (image-only) tidak didukung tanpa OCR (out of scope POC).

### 4.2 Dokumen Menjadi Konteks LLM
- Saat user chat, sistem akan mengambil dokumen terkait dari DB.
- Konten dokumen dimasukkan ke prompt sebagai konteks.
- Tidak ada retrieval cerdas; kontekstualisasi dilakukan dengan “attach full doc” atau “summary” sederhana.
- Batasan konteks (disarankan):
  - Jika total konteks melebihi limit token/model, lakukan trimming deterministik:
    1) Ringkas per dokumen (mis. 10-20 kalimat), lalu gabungkan; atau
    2) Ambil potongan teks paling relevan secara heuristik sederhana (keyword match dari `message`).
  - Catat di `text` bila jawaban berpotensi tidak lengkap karena konteks terpotong.

### 4.3 Interface Chat (Seolah‑olah RAG)
- Endpoint chat menerima input user dan mengembalikan jawaban dari LLM.
- Response bersih tanpa chain‑of‑thought.
- Mengembalikan struktur response yang siap dipakai FE.

### 4.4 Chart di Payload
- Response API dapat berisi `text` dan `chart`.
- `chart` mengikuti format standar Chart.js terbaru (type, data, options).
- FE akan merender chart berdasarkan payload.

### 4.5 Future Features (Tidak Dikerjakan Sekarang)
#### 4.5.1 Speech-to-Text (STT) — Input Suara
- User mengirim voice note/audio.
- Backend melakukan transkripsi via STT engine (sudah ada, tinggal deploy).
- Hasil transkripsi diperlakukan sama seperti `message` pada endpoint chat.

#### 4.5.2 Text-to-Speech (TTS) — Output Suara
- Setelah `text` dihasilkan dari LLM, backend dapat menghasilkan audio via TTS engine (sudah ada, tinggal deploy).
- API mengembalikan URL audio (atau base64) untuk diputar di FE.

## 5. User Flow
1) User login via SSO → FE menyimpan `access` token (dan `refresh` bila ada).  
2) User upload dokumen (teks) → tersimpan di DB.  
3) User chat → sistem memanggil LLM dengan konteks dokumen.  
4) API mengembalikan `text` + opsional `chart`.  
5) FE menampilkan jawaban; jika ada `chart`, FE render via Chart.js.  
6) (Future) User bisa bertanya via suara (STT) dan/atau meminta jawaban dibacakan (TTS).

## 6. API Requirements (DRF)
### 6.0 Authentication (SSO)
Semua endpoint aplikasi (dokumen, chat, future STT/TTS) menggunakan Bearer token dari SSO.

#### 6.0.1 Format Header
- Header wajib: `Authorization: Bearer <access_token>`

#### 6.0.2 SSO Service (Referensi dari `sso.json`)
- Base: `https://sso.arnatech.id/api`
- Security scheme: Bearer token di header `Authorization`.

Endpoint yang relevan untuk FE (login/refresh) dan backend (verify):
- **POST** `/auth/login/` — login email+password (MFA-aware)
  - Jika MFA diperlukan: response `mfa_required: true`, lalu lanjut ke `/auth/mfa/verify/`.
- **POST** `/auth/mfa/verify/` — verifikasi token MFA, mengembalikan `access` + `refresh`.
- **POST** `/auth/token/refresh/` — refresh `access` memakai `refresh`.
- **POST** `/auth/token/verify/` — verifikasi validitas token (backend dapat memakai ini untuk cek akses token).

#### 6.0.3 Perilaku Aplikasi Terkait Auth
- Jika header `Authorization` tidak ada / format salah → 401.
- Jika token tidak valid (SSO verify gagal) → 401.
- Jika token expired:
  - FE melakukan refresh via SSO `/auth/token/refresh/`, lalu retry request aplikasi.
  - Backend tidak melakukan refresh; backend hanya menolak (401) agar FE yang handle.
- Strategi verifikasi token (POC):
  - Default: backend memanggil SSO `POST /auth/token/verify/` untuk setiap request yang butuh auth.
  - Optimisasi (opsional): cache hasil verify per token untuk TTL pendek (mis. 60 detik) untuk mengurangi latency.
- Identitas user untuk audit/ownership (POC):
  - Setelah token valid, backend perlu mendapatkan `owner_user_id` dari token (decode JWT payload) atau dari endpoint SSO yang menyediakan identitas user.
  - Karena `token/verify` hanya memvalidasi token (tanpa mengembalikan user id), claim yang dipakai (mis. `user_id` / `sub`) perlu dipastikan.

### 6.1 Upload Dokumen
- **POST** `/api/documents`
- Request: multipart/form-data
  - `file`: file (PDF/DOCX/TXT)
  - `title`: string (opsional; default: nama file)
  - `tags`: array/string (opsional; POC boleh skip)
- Response: id dokumen, ringkasan metadata
Catatan: butuh `Authorization: Bearer ...`.

### 6.2 List Dokumen
- **GET** `/api/documents`
- Response: daftar dokumen untuk dipilih sebagai konteks
Catatan: butuh `Authorization: Bearer ...`.

### 6.2.1 (Opsional) Detail & Hapus Dokumen
Jika diperlukan untuk demo/operasional POC:
- **GET** `/api/documents/{id}` — detail dokumen (tanpa mengembalikan `content` penuh jika terlalu panjang).
- **DELETE** `/api/documents/{id}` — hapus dokumen.

### 6.3 Chat
- **POST** `/api/chat`
- Payload:
  - `message`: string
  - `document_ids`: array id (boleh kosong untuk default)
  - `include_chart`: boolean (opsional; FE set `true` hanya saat user memang meminta chart)
  - `conversation_id`: string/uuid (opsional; jika ingin mempertahankan konteks percakapan)
- Response:
  - `text`: string
  - `chart`: object (opsional)
Catatan: butuh `Authorization: Bearer ...`.

#### Format `chart` (Chart.js)
```
{
  "type": "bar",
  "data": {
    "labels": ["Jan", "Feb"],
    "datasets": [
      {"label": "Target", "data": [80, 90]},
      {"label": "Actual", "data": [75, 95]}
    ]
  },
  "options": {
    "responsive": true
  }
}
```

### 6.4 Future API (Opsional)
Catatan: skema ini hanya untuk perencanaan; tidak dikerjakan pada POC awal.

#### 6.4.1 STT
- **POST** `/api/stt`
- Request: audio file
- Response:
  - `text`: string (hasil transkripsi)
Catatan: butuh `Authorization: Bearer ...`.

#### 6.4.2 TTS
- **POST** `/api/tts`
- Request:
  - `text`: string
- Response:
  - `audio_url`: string (atau `audio_base64`)
Catatan: butuh `Authorization: Bearer ...`.

## 7. DeepSeek LLM Integration
### 7.1 Prinsip Integrasi
- Gunakan standar Chat Completions (messages: system + user) dengan auth API key.
- Dokumen dari DB disuntikkan ke prompt sebagai konteks (tanpa vector search).
- Model wajib mengeluarkan output yang stabil untuk diparse (JSON saja, tidak pakai markdown).
- Parameter operasional (disarankan):
  - Timeout upstream ke LLM: 30-60 detik.
  - Batasi panjang konteks (lihat 4.2) agar tidak melebihi limit model.
  - Jika provider mendukung mode output JSON/structured output, aktifkan untuk mengurangi risiko JSON invalid.

### 7.2 Kontrak Output (Wajib)
Model harus mengembalikan SATU objek JSON valid, tanpa teks lain, dengan schema:
```
{
  "text": "string",
  "chart": { ... } | null
}
```
Aturan:
- Tidak boleh ada key lain selain `text` dan `chart`.
- Tidak boleh ada markdown/code fence.
- `chart` harus `null` jika `include_chart=false` atau user tidak meminta chart.
- Jika `include_chart=true` tetapi data tidak cukup untuk chart, kembalikan `chart: null` dan jelaskan kekurangannya di `text`.

### 7.3 Aturan Jawaban (Guardrails)
- Bahasa: jawab dalam Bahasa Indonesia (kecuali user minta bahasa lain).
- Tidak menampilkan chain-of-thought / langkah berpikir. Berikan jawaban final saja.
- Untuk pertanyaan yang membutuhkan data dari dokumen: gunakan HANYA informasi yang ada di konteks dokumen yang diberikan.
  - Jika tidak ditemukan di konteks, jawab jujur bahwa data tidak tersedia dan minta user upload/beri dokumen yang relevan atau klarifikasi.
- Untuk sapaan/percakapan ringan: boleh jawab singkat tanpa konteks dokumen.
- Jika pertanyaan ambigu (mis. periode/wilayah tidak jelas), ajukan pertanyaan klarifikasi di `text` dan set `chart: null`.

### 7.4 Template Prompt (Disarankan)
#### 7.4.1 System Prompt
Gunakan system prompt tetap seperti berikut (boleh disesuaikan sedikit, tapi aturan output jangan berubah):
```
Anda adalah asisten analisis dokumen untuk aplikasi chat POC (RAG-like).

Aturan penting:
1) Jawab dalam Bahasa Indonesia.
2) Jangan tampilkan proses berpikir, penalaran, atau langkah-langkah internal. Tulis jawaban final saja.
3) Untuk pertanyaan yang membutuhkan fakta/angka dari dokumen, gunakan hanya CONTEXT yang diberikan. Jika tidak ada, katakan tidak ditemukan di dokumen.
4) Output HARUS berupa 1 objek JSON valid, tanpa teks lain, tanpa markdown, tanpa code block.
5) JSON hanya boleh memiliki 2 key: "text" dan "chart".
6) "chart" harus null kecuali diminta dan datanya cukup.

Jika diminta chart:
- "chart" harus mengikuti format konfigurasi Chart.js (type, data, options).
- Pilih "type" yang sesuai: "line" untuk time-series, "bar" untuk perbandingan kategori, "pie/doughnut" untuk proporsi.
- Pastikan data numerik berupa number (bukan string).
```

#### 7.4.2 User Prompt (Dengan Placeholder)
Backend membentuk user prompt dengan format konsisten:
```
INCLUDE_CHART: {{include_chart}}   # true/false
DOCUMENT_IDS: {{document_ids}}     # contoh: [1,2]

CONTEXT (dokumen terlampir):
{{documents_context}}

USER_MESSAGE:
{{message}}
```
Catatan `documents_context` (disarankan):
- Sertakan penanda per dokumen agar model bisa menyebut sumber secara natural di `text` bila perlu.
- Contoh:
```
<DOC id="1" title="OKR-KPI Q3 2025">
... isi dokumen ...
</DOC>
<DOC id="2" title="Definisi KPI">
... isi dokumen ...
</DOC>
```

### 7.5 Instruksi Chart (Chart.js v4+)
Jika chart diminta dan data cukup, `chart` harus berupa objek konfigurasi Chart.js yang minimal namun valid:
- `type`: string (mis. `bar`, `line`)
- `data.labels`: array string
- `data.datasets`: array object
  - minimal: `label` (string), `data` (array number)
- `options`: object (minimal `responsive: true`)

Pedoman:
- Jangan buat angka/label yang tidak ada di konteks dokumen.
- Jika user minta perbandingan target vs capaian, buat 2 datasets: `Target` dan `Actual` (atau istilah yang sesuai dokumen).
- Untuk time-series (bulan/minggu), pastikan urutan label benar.

### 7.6 Contoh Output
Contoh tanpa chart:
```
{"text":"Saya tidak menemukan angka NPS untuk Jawa Barat bulan September 2025 pada dokumen yang dilampirkan. Bisa upload laporan NPS periode tersebut atau sebutkan dokumen yang memuat angkanya?","chart":null}
```
Contoh dengan chart:
```
{
  "text": "Berikut perbandingan target vs capaian NPS Q3 2025 untuk Jawa Barat berdasarkan dokumen OKR-KPI Q3 2025.",
  "chart": {
    "type": "bar",
    "data": {
      "labels": ["Jul", "Agu", "Sep"],
      "datasets": [
        {"label": "Target", "data": [80, 82, 83]},
        {"label": "Actual", "data": [78, 81, 84]}
      ]
    },
    "options": {"responsive": true}
  }
}
```

## 8. Data Model (DB)
### 8.1 Document
- id
- owner_user_id (diambil dari token SSO; minimal untuk audit/ownership, **POC**: dokumen bersifat global, tidak dibatasi per user)
- title
- content (teks hasil ekstraksi)
- source_filename
- mime_type (opsional)
- content_length (opsional)
- created_at
- updated_at

### 8.2 Chat Log (opsional POC)
- id
- user_message
- response_text
- response_chart_json
- document_ids
- created_at

## 9. Validasi & Error Handling
- Dokumen kosong → error 400.
- Tidak ada dokumen untuk konteks → fallback ke message saja.
- DeepSeek API error → error 502 + message generik.
- Chart invalid JSON → hapus chart dan kembalikan text saja.
- Upload format tidak didukung → 415.
- Upload melebihi max size → 413.
- Ekstraksi dokumen gagal → 422.

## 10. UX/FE Expectations
- Chat UI sederhana.
- “Tidak menampilkan detail proses berpikir.”
- Chart hanya tampil jika `chart` ada.
- (Future) Tombol mic untuk input suara + tombol “play” untuk membacakan jawaban.

## 11. Kriteria Sukses POC
- Upload dokumen sukses dan tersimpan di DB.
- Chat bisa menjawab pertanyaan berbasis dokumen.
- Payload chart valid dan berhasil dirender di FE.
- Stabil untuk demo end‑to‑end.

## 12. Risiko & Mitigasi
- **Context terlalu panjang** → batasi panjang dokumen atau ringkas sederhana.
- **Jawaban halu** → tambahkan prompt guardrail (“hanya gunakan konteks”).
- **Chart format salah** → validasi JSON sebelum return.

## 13. Open Questions
- Dokumen per user atau global? (asumsi global POC)
- Apakah perlu tagging dokumen untuk memilih konteks lebih presisi?
- Format file yang pasti didukung di POC?
- Claim apa yang dipakai untuk identitas user di access token SSO (mis. `user_id` / `sub`)?
