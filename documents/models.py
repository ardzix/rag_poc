from django.db import models
from django.utils import timezone


class Document(models.Model):
    """Model untuk menyimpan dokumen yang di-upload"""
    
    owner_user_id = models.CharField(
        max_length=255,
        help_text="User ID dari SSO token (untuk audit/ownership)"
    )
    title = models.CharField(max_length=500)
    content = models.TextField(help_text="Teks hasil ekstraksi dokumen")
    source_filename = models.CharField(max_length=500)
    mime_type = models.CharField(max_length=100, blank=True, null=True)
    content_length = models.IntegerField(
        blank=True, 
        null=True,
        help_text="Panjang konten dalam bytes"
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'documents'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner_user_id', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.source_filename})"
