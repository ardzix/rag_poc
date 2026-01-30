"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Swagger/OpenAPI Schema
schema_view = get_schema_view(
    openapi.Info(
        title="NOC RAG API",
        default_version='v1',
        description="""
        # NOC RAG POC - Chat RAG-like API Documentation
        
        POC untuk sistem chat berbasis dokumen menggunakan DeepSeek LLM.
        
        ## Authentication
        
        Semua endpoint memerlukan Bearer token dari SSO Arnatech.
        
        **Header format:**
        ```
        Authorization: Bearer <access_token>
        ```
        
        **Cara mendapatkan token:**
        1. Login via SSO: `POST https://sso.arnatech.id/api/auth/login/`
        2. Gunakan access token yang diterima di header Authorization
        
        ## Features
        
        - 📄 **Document Management**: Upload dan kelola dokumen (PDF, DOCX, TXT)
        - 💬 **Chat**: Chat dengan konteks dokumen menggunakan LLM
        - 📊 **Chart Generation**: Generate chart dalam format Chart.js
        - 🔐 **SSO Authentication**: Integrasi dengan SSO Arnatech
        
        ## Supported Document Formats
        
        - PDF (dengan text layer)
        - DOCX (Microsoft Word)
        - TXT (Plain text)
        
        ## Response Format
        
        Chat response berisi:
        - `text`: Jawaban dari LLM dalam Bahasa Indonesia
        - `chart`: Object Chart.js (null jika tidak diminta atau data tidak cukup)
        
        ## Error Codes
        
        - `400`: Bad Request - Validasi gagal
        - `401`: Unauthorized - Token tidak valid
        - `413`: Payload Too Large - File > 10MB
        - `415`: Unsupported Media Type - Format tidak didukung
        - `422`: Unprocessable Entity - Gagal ekstraksi dokumen
        - `502`: Bad Gateway - Error dari LLM API
        """,
        terms_of_service="",
        contact=openapi.Contact(email="dev@arnatech.id"),
        license=openapi.License(name="Proprietary"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/documents/', include('documents.urls')),
    path('api/chat/', include('chat.urls')),
    
    # Swagger/OpenAPI Documentation
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('', schema_view.with_ui('swagger', cache_timeout=0), name='schema-root'),  # Root redirect to swagger
]
