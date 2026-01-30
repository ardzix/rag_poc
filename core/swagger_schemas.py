"""
Custom Swagger/OpenAPI schema definitions dan decorators
"""
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


# Common responses
unauthorized_response = openapi.Response(
    description="Unauthorized - Token tidak valid atau tidak ada",
    examples={
        "application/json": {
            "detail": "Token tidak valid atau expired"
        }
    }
)

bad_request_response = openapi.Response(
    description="Bad Request - Validasi gagal",
    examples={
        "application/json": {
            "error": "Validasi gagal",
            "details": {
                "field_name": ["Error message"]
            }
        }
    }
)


# Document schemas
document_upload_schema = swagger_auto_schema(
    operation_description="""
    Upload dokumen baru untuk digunakan sebagai konteks chat.
    
    **Format yang didukung:**
    - PDF (dengan text layer, bukan hasil scan)
    - DOCX (Microsoft Word)
    - TXT (Plain text)
    
    **Batasan:**
    - Ukuran maksimal: 10 MB
    - File hasil scan (image-only PDF) tidak didukung
    
    **Response:**
    - 201: Dokumen berhasil diupload
    - 400: Validasi gagal (dokumen kosong, dll)
    - 401: Token tidak valid
    - 413: File terlalu besar (>10MB)
    - 415: Format file tidak didukung
    - 422: Gagal ekstraksi dokumen
    """,
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['file'],
        properties={
            'file': openapi.Schema(
                type=openapi.TYPE_FILE,
                description='File dokumen (PDF/DOCX/TXT)'
            ),
            'title': openapi.Schema(
                type=openapi.TYPE_STRING,
                description='Judul dokumen (opsional, default: nama file)',
                max_length=500
            ),
        },
    ),
    responses={
        201: openapi.Response(
            description="Dokumen berhasil diupload",
            examples={
                "application/json": {
                    "message": "Dokumen berhasil diupload",
                    "document": {
                        "id": 1,
                        "title": "Laporan Q3 2025",
                        "source_filename": "report.pdf",
                        "mime_type": "application/pdf",
                        "content_length": 15420,
                        "content_preview": "LAPORAN KINERJA...",
                        "created_at": "2026-01-30T10:15:30.123456Z",
                        "updated_at": "2026-01-30T10:15:30.123456Z"
                    }
                }
            }
        ),
        400: bad_request_response,
        401: unauthorized_response,
        413: openapi.Response(
            description="File terlalu besar",
            examples={
                "application/json": {
                    "error": "Validasi gagal",
                    "details": {
                        "file": ["Ukuran file melebihi batas maksimal 10 MB"]
                    }
                }
            }
        ),
        415: openapi.Response(
            description="Format tidak didukung",
            examples={
                "application/json": {
                    "error": "Format file tidak didukung",
                    "mime_type": "image/jpeg",
                    "supported_formats": "PDF, DOCX, TXT"
                }
            }
        ),
        422: openapi.Response(
            description="Gagal ekstraksi",
            examples={
                "application/json": {
                    "error": "Gagal mengekstrak dokumen",
                    "details": "PDF tidak mengandung teks yang bisa diekstrak"
                }
            }
        ),
    },
    security=[{'Bearer': []}],
    tags=['Documents']
)


document_list_schema = swagger_auto_schema(
    operation_description="""
    List semua dokumen milik user yang sedang login.
    
    Dokumen diurutkan berdasarkan waktu upload (terbaru di atas).
    """,
    responses={
        200: openapi.Response(
            description="List dokumen berhasil diambil",
            examples={
                "application/json": {
                    "count": 3,
                    "documents": [
                        {
                            "id": 1,
                            "title": "Laporan Q3 2025",
                            "source_filename": "report.pdf",
                            "mime_type": "application/pdf",
                            "content_length": 15420,
                            "content_preview": "Preview...",
                            "created_at": "2026-01-30T10:15:30Z",
                            "updated_at": "2026-01-30T10:15:30Z"
                        }
                    ]
                }
            }
        ),
        401: unauthorized_response,
    },
    security=[{'Bearer': []}],
    tags=['Documents']
)


document_detail_schema = swagger_auto_schema(
    operation_description="""
    Detail dokumen dengan full content.
    
    Berbeda dengan list endpoint yang hanya menampilkan preview,
    endpoint ini mengembalikan seluruh isi dokumen yang sudah diekstrak.
    """,
    responses={
        200: openapi.Response(
            description="Detail dokumen",
            examples={
                "application/json": {
                    "id": 1,
                    "owner_user_id": "user-123",
                    "title": "Laporan Q3 2025",
                    "content": "Full content here...",
                    "source_filename": "report.pdf",
                    "mime_type": "application/pdf",
                    "content_length": 15420,
                    "created_at": "2026-01-30T10:15:30Z",
                    "updated_at": "2026-01-30T10:15:30Z"
                }
            }
        ),
        401: unauthorized_response,
        404: openapi.Response(description="Dokumen tidak ditemukan"),
    },
    security=[{'Bearer': []}],
    tags=['Documents']
)


document_delete_schema = swagger_auto_schema(
    operation_description="""
    Hapus dokumen.
    
    Dokumen yang sudah dihapus tidak bisa dikembalikan.
    """,
    responses={
        200: openapi.Response(
            description="Dokumen berhasil dihapus",
            examples={
                "application/json": {
                    "message": "Dokumen berhasil dihapus"
                }
            }
        ),
        401: unauthorized_response,
        404: openapi.Response(description="Dokumen tidak ditemukan"),
    },
    security=[{'Bearer': []}],
    tags=['Documents']
)


# Chat schemas
chat_create_schema = swagger_auto_schema(
    operation_description="""
    Kirim pesan chat dan terima response dari LLM dengan konteks dokumen.
    
    **Cara kerja (OTOMATIS):**
    1. Sistem mengambil SEMUA dokumen milik user dari database sebagai konteks
    2. Sistem AUTO-DETECT apakah perlu chart berdasarkan kata kunci di message:
       - Keywords: "chart", "grafik", "visualisasi", "diagram", "perbandingan", "tren", dll
       - AI akan generate chart jika data cukup dan relevan
    3. Konten dokumen dimasukkan sebagai konteks ke LLM
    4. LLM menjawab dalam Bahasa Indonesia berdasarkan konteks
    5. Jika terdeteksi perlu chart dan data cukup, LLM generate chart dalam format Chart.js
    
    **Payload Simplified:**
    - Hanya perlu kirim `message` saja!
    - Tidak perlu specify `document_ids` (auto dari DB)
    - Tidak perlu specify `include_chart` (auto-detect dari message)
    - `conversation_id` opsional untuk tracking percakapan
    
    **Tips:**
    - Untuk minta chart, gunakan kata "chart", "grafik", "visualisasi", "perbandingan" di message
    - Contoh: "Buatkan grafik perbandingan target vs capaian NPS"
    - Spesifik dalam pertanyaan untuk hasil lebih akurat
    """,
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['message'],
        properties={
            'message': openapi.Schema(
                type=openapi.TYPE_STRING,
                description='Pesan/pertanyaan dari user',
                max_length=5000,
                example='Berapa target NPS Q3 2025 untuk Jawa Barat?'
            ),
            'conversation_id': openapi.Schema(
                type=openapi.TYPE_STRING,
                description='ID untuk mempertahankan konteks percakapan (opsional)',
                max_length=100,
                example='conv-abc-123'
            ),
        },
    ),
    responses={
        200: openapi.Response(
            description="Response berhasil",
            examples={
                "application/json": {
                    "text": "Berdasarkan dokumen Laporan Q3 2025, target NPS untuk Jawa Barat pada Q3 2025 adalah:\n- Juli: 80\n- Agustus: 82\n- September: 83",
                    "chart": None
                },
                "application/json (with chart)": {
                    "text": "Berikut perbandingan target vs capaian NPS Q3 2025 untuk Jawa Barat:",
                    "chart": {
                        "type": "bar",
                        "data": {
                            "labels": ["Jul", "Agu", "Sep"],
                            "datasets": [
                                {"label": "Target", "data": [80, 82, 83]},
                                {"label": "Capaian", "data": [78, 81, 84]}
                            ]
                        },
                        "options": {"responsive": True}
                    }
                }
            }
        ),
        400: bad_request_response,
        401: unauthorized_response,
        502: openapi.Response(
            description="Error dari LLM API",
            examples={
                "application/json": {
                    "error": "Gagal mendapatkan response dari LLM",
                    "details": "Timeout saat memanggil DeepSeek API"
                }
            }
        ),
    },
    security=[{'Bearer': []}],
    tags=['Chat']
)


chat_history_schema = swagger_auto_schema(
    operation_description="""
    List history chat milik user (50 terakhir).
    
    History mencakup:
    - Pesan user
    - Response text dari LLM
    - Chart data (jika ada)
    - Document IDs yang digunakan
    - Conversation ID (jika ada)
    """,
    responses={
        200: openapi.Response(
            description="History berhasil diambil",
            examples={
                "application/json": {
                    "count": 15,
                    "history": [
                        {
                            "id": 1,
                            "user_message": "Berapa target NPS?",
                            "response_text": "Target NPS adalah...",
                            "response_chart_json": None,
                            "document_ids": [1, 2],
                            "conversation_id": "conv-123",
                            "created_at": "2026-01-30T12:00:00Z"
                        }
                    ]
                }
            }
        ),
        401: unauthorized_response,
    },
    security=[{'Bearer': []}],
    tags=['Chat']
)
