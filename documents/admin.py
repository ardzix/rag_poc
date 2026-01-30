from django.contrib import admin
from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'owner_user_id', 'source_filename', 'mime_type', 'content_length', 'created_at']
    list_filter = ['mime_type', 'created_at']
    search_fields = ['title', 'source_filename', 'owner_user_id', 'content']
    readonly_fields = ['created_at', 'updated_at', 'content_length']
    
    fieldsets = (
        ('Informasi Dasar', {
            'fields': ('owner_user_id', 'title', 'source_filename', 'mime_type')
        }),
        ('Konten', {
            'fields': ('content', 'content_length')
        }),
        ('Timestamp', {
            'fields': ('created_at', 'updated_at')
        }),
    )
