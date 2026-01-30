"""
Serializers untuk Document API
"""
from rest_framework import serializers
from .models import Document


class DocumentUploadSerializer(serializers.Serializer):
    """Serializer untuk upload dokumen"""
    
    file = serializers.FileField(required=True)
    title = serializers.CharField(
        required=False,
        max_length=500,
        allow_blank=True
    )
    tags = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Tags dipisah koma (opsional untuk POC)"
    )
    
    def validate_file(self, value):
        """Validasi file upload"""
        from django.conf import settings
        
        # Cek ukuran file
        max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024  # Convert to bytes
        if value.size > max_size:
            raise serializers.ValidationError(
                f"Ukuran file melebihi batas maksimal {settings.MAX_UPLOAD_SIZE_MB} MB"
            )
        
        return value


class DocumentSerializer(serializers.ModelSerializer):
    """Serializer untuk list dan detail dokumen"""
    
    # Jangan expose content_length yang terlalu besar
    content_preview = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = [
            'id',
            'title',
            'source_filename',
            'mime_type',
            'content_length',
            'content_preview',
            'created_at',
            'updated_at'
        ]
        read_only_fields = fields
    
    def get_content_preview(self, obj):
        """Return preview konten (200 karakter pertama)"""
        if obj.content:
            preview = obj.content[:200]
            if len(obj.content) > 200:
                preview += "..."
            return preview
        return ""


class DocumentDetailSerializer(serializers.ModelSerializer):
    """Serializer untuk detail dokumen dengan full content"""
    
    class Meta:
        model = Document
        fields = [
            'id',
            'owner_user_id',
            'title',
            'content',
            'source_filename',
            'mime_type',
            'content_length',
            'created_at',
            'updated_at'
        ]
        read_only_fields = fields
