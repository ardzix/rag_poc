"""
Django management command untuk seed sample documents
"""
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from documents.models import Document


class Command(BaseCommand):
    help = 'Seed sample documents untuk testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=str,
            default='test-user-001',
            help='User ID untuk ownership dokumen (default: test-user-001)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Hapus semua dokumen existing sebelum seed'
        )

    def handle(self, *args, **options):
        user_id = options['user_id']
        clear = options['clear']

        # Clear existing documents if requested
        if clear:
            count = Document.objects.filter(owner_user_id=user_id).count()
            Document.objects.filter(owner_user_id=user_id).delete()
            self.stdout.write(
                self.style.WARNING(f'Deleted {count} existing documents for user {user_id}')
            )

        # Path ke sample documents
        base_path = os.path.join(settings.BASE_DIR, 'sample_documents')
        
        # Sample documents yang akan di-seed
        documents = [
            {
                'filename': 'laporan_q3_2025.txt',
                'title': 'Laporan Kinerja Q3 2025',
            },
            {
                'filename': 'definisi_kpi.txt',
                'title': 'Definisi Key Performance Indicators (KPI)',
            },
            {
                'filename': 'market_analysis_2025.txt',
                'title': 'Analisis Pasar & Kompetitor 2025',
            },
        ]

        created_count = 0
        
        for doc_info in documents:
            file_path = os.path.join(base_path, doc_info['filename'])
            
            if not os.path.exists(file_path):
                self.stdout.write(
                    self.style.ERROR(f'File not found: {file_path}')
                )
                continue
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Create document
            document = Document.objects.create(
                owner_user_id=user_id,
                title=doc_info['title'],
                content=content,
                source_filename=doc_info['filename'],
                mime_type='text/plain',
                content_length=len(content)
            )
            
            created_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Created: {document.title} (ID: {document.id})'
                )
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Successfully seeded {created_count} documents for user {user_id}'
            )
        )
        
        # Display summary
        total_docs = Document.objects.filter(owner_user_id=user_id).count()
        self.stdout.write(
            self.style.SUCCESS(
                f'Total documents for {user_id}: {total_docs}'
            )
        )
