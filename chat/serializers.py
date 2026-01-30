"""
Serializers untuk Chat API
"""
from rest_framework import serializers
from .models import ChatLog


class ChatRequestSerializer(serializers.Serializer):
    """Serializer untuk request chat"""
    
    message = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=5000,
        help_text="Pesan dari user"
    )
    conversation_id = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=100,
        help_text="ID untuk mempertahankan konteks percakapan (opsional)"
    )


class ChatResponseSerializer(serializers.Serializer):
    """Serializer untuk response chat"""
    
    text = serializers.CharField(help_text="Jawaban dari LLM")
    chart = serializers.JSONField(
        required=False,
        allow_null=True,
        help_text="Konfigurasi Chart.js (null jika tidak ada chart)"
    )


class ChatLogSerializer(serializers.ModelSerializer):
    """Serializer untuk log chat history"""
    
    class Meta:
        model = ChatLog
        fields = [
            'id',
            'user_message',
            'response_text',
            'response_chart_json',
            'document_ids',
            'conversation_id',
            'created_at'
        ]
        read_only_fields = fields
