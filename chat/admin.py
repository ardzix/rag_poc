from django.contrib import admin
from .models import ChatLog


@admin.register(ChatLog)
class ChatLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'owner_user_id', 'user_message_preview', 'conversation_id', 'created_at']
    list_filter = ['created_at']
    search_fields = ['owner_user_id', 'user_message', 'response_text', 'conversation_id']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Informasi Chat', {
            'fields': ('owner_user_id', 'conversation_id')
        }),
        ('Pesan', {
            'fields': ('user_message', 'response_text')
        }),
        ('Chart Data', {
            'fields': ('response_chart_json', 'document_ids')
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )
    
    def user_message_preview(self, obj):
        """Preview pesan user (50 karakter pertama)"""
        return obj.user_message[:50] + '...' if len(obj.user_message) > 50 else obj.user_message
    
    user_message_preview.short_description = 'Pesan User'
