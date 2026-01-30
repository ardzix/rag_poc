from django.db import models
from django.utils import timezone


class ChatLog(models.Model):
    """Model opsional untuk menyimpan log percakapan chat"""
    
    owner_user_id = models.CharField(
        max_length=255,
        help_text="User ID dari SSO token"
    )
    user_message = models.TextField()
    response_text = models.TextField()
    response_chart_json = models.JSONField(blank=True, null=True)
    document_ids = models.JSONField(
        blank=True,
        null=True,
        help_text="Array of document IDs yang digunakan sebagai konteks"
    )
    conversation_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="ID untuk mengelompokkan percakapan"
    )
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'chat_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner_user_id', '-created_at']),
            models.Index(fields=['conversation_id', '-created_at']),
        ]
    
    def __str__(self):
        return f"Chat {self.id} - {self.user_message[:50]}"
