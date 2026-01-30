"""
Views untuk Document API
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import Document
from .serializers import (
    DocumentUploadSerializer,
    DocumentSerializer,
    DocumentDetailSerializer
)
from core.authentication import SSOAuthentication
from core.document_extractor import DocumentExtractor
from core.swagger_schemas import (
    document_upload_schema,
    document_list_schema,
    document_detail_schema,
    document_delete_schema
)


class DocumentViewSet(viewsets.ViewSet):
    """
    ViewSet untuk mengelola dokumen
    
    Endpoints:
    - POST /api/documents - Upload dokumen
    - GET /api/documents - List dokumen
    - GET /api/documents/{id} - Detail dokumen
    - DELETE /api/documents/{id} - Hapus dokumen
    """
    
    authentication_classes = [SSOAuthentication]
    permission_classes = [IsAuthenticated]
    
    @document_upload_schema
    def create(self, request):
        """
        Upload dokumen baru
        
        POST /api/documents
        """
        serializer = DocumentUploadSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {"error": "Validasi gagal", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        uploaded_file = serializer.validated_data['file']
        title = serializer.validated_data.get('title', '')
        
        # Jika title tidak diberikan, gunakan filename
        if not title:
            title = uploaded_file.name
        
        # Deteksi MIME type
        mime_type = DocumentExtractor.detect_mime_type(uploaded_file)
        
        # Cek apakah format didukung
        if not DocumentExtractor.is_supported(mime_type):
            return Response(
                {
                    "error": "Format file tidak didukung",
                    "mime_type": mime_type,
                    "supported_formats": "PDF, DOCX, TXT"
                },
                status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
            )
        
        # Ekstraksi teks
        extracted_text, error_msg = DocumentExtractor.extract(uploaded_file, mime_type)
        
        if error_msg:
            return Response(
                {
                    "error": "Gagal mengekstrak dokumen",
                    "details": error_msg
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        
        # Cek apakah dokumen kosong
        if not extracted_text or len(extracted_text.strip()) == 0:
            return Response(
                {"error": "Dokumen tidak mengandung teks yang bisa diekstrak"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Simpan ke database
        document = Document.objects.create(
            owner_user_id=request.user.user_id,
            title=title,
            content=extracted_text,
            source_filename=uploaded_file.name,
            mime_type=mime_type,
            content_length=len(extracted_text)
        )
        
        # Kembalikan response
        response_serializer = DocumentSerializer(document)
        return Response(
            {
                "message": "Dokumen berhasil diupload",
                "document": response_serializer.data
            },
            status=status.HTTP_201_CREATED
        )
    
    @document_list_schema
    def list(self, request):
        """
        List semua dokumen (global)
        
        GET /api/documents
        """
        # POC: dokumen bersifat global (RAG global), semua user bisa mengakses
        documents = Document.objects.all()
        
        serializer = DocumentSerializer(documents, many=True)
        
        return Response({
            "count": documents.count(),
            "documents": serializer.data
        })
    
    @document_detail_schema
    def retrieve(self, request, pk=None):
        """
        Detail dokumen dengan full content
        
        GET /api/documents/{id}
        """
        # POC: dokumen bersifat global, tidak dibatasi per user
        document = get_object_or_404(Document, pk=pk)
        
        serializer = DocumentDetailSerializer(document)
        return Response(serializer.data)
    
    @document_delete_schema
    def destroy(self, request, pk=None):
        """
        Hapus dokumen
        
        DELETE /api/documents/{id}
        """
        # POC: dokumen bersifat global, tidak dibatasi per user
        document = get_object_or_404(Document, pk=pk)
        
        document.delete()
        
        return Response(
            {"message": "Dokumen berhasil dihapus"},
            status=status.HTTP_200_OK
        )
