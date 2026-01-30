"""
Service untuk ekstraksi teks dari berbagai format dokumen
"""
import re
from typing import Tuple, Optional
import PyPDF2
import docx
import magic


class DocumentExtractor:
    """
    Service untuk mengekstrak teks dari dokumen PDF, DOCX, dan TXT
    """
    
    SUPPORTED_MIME_TYPES = {
        'application/pdf': 'pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
        'text/plain': 'txt',
    }
    
    @staticmethod
    def detect_mime_type(file_obj) -> str:
        """
        Deteksi MIME type dari file object
        """
        try:
            # Reset file pointer
            file_obj.seek(0)
            
            # Baca header untuk deteksi
            mime = magic.from_buffer(file_obj.read(2048), mime=True)
            
            # Reset lagi
            file_obj.seek(0)
            
            return mime
        except Exception:
            # Fallback ke content_type dari upload
            return file_obj.content_type if hasattr(file_obj, 'content_type') else 'application/octet-stream'
    
    @staticmethod
    def is_supported(mime_type: str) -> bool:
        """
        Cek apakah MIME type didukung
        """
        return mime_type in DocumentExtractor.SUPPORTED_MIME_TYPES
    
    @staticmethod
    def extract(file_obj, mime_type: str) -> Tuple[str, Optional[str]]:
        """
        Ekstrak teks dari file
        
        Args:
            file_obj: File object dari upload
            mime_type: MIME type yang sudah terdeteksi
        
        Returns:
            Tuple (extracted_text, error_message)
            Jika berhasil: (text, None)
            Jika gagal: ("", error_message)
        """
        try:
            file_obj.seek(0)
            
            if mime_type == 'application/pdf':
                return DocumentExtractor._extract_pdf(file_obj)
            elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                return DocumentExtractor._extract_docx(file_obj)
            elif mime_type == 'text/plain':
                return DocumentExtractor._extract_txt(file_obj)
            else:
                return ("", f"MIME type tidak didukung: {mime_type}")
                
        except Exception as e:
            return ("", f"Error saat ekstraksi: {str(e)}")
    
    @staticmethod
    def _extract_pdf(file_obj) -> Tuple[str, Optional[str]]:
        """Ekstrak teks dari PDF"""
        try:
            reader = PyPDF2.PdfReader(file_obj)
            text_parts = []
            
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            
            if not text_parts:
                return ("", "PDF tidak mengandung teks yang bisa diekstrak (mungkin hasil scan)")
            
            combined_text = "\n".join(text_parts)
            normalized_text = DocumentExtractor._normalize_text(combined_text)
            
            return (normalized_text, None)
            
        except Exception as e:
            return ("", f"Gagal membaca PDF: {str(e)}")
    
    @staticmethod
    def _extract_docx(file_obj) -> Tuple[str, Optional[str]]:
        """Ekstrak teks dari DOCX"""
        try:
            doc = docx.Document(file_obj)
            text_parts = []
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)
            
            # Ekstrak tabel juga
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(cell.text.strip() for cell in row.cells)
                    if row_text.strip():
                        text_parts.append(row_text)
            
            if not text_parts:
                return ("", "Dokumen DOCX kosong")
            
            combined_text = "\n".join(text_parts)
            normalized_text = DocumentExtractor._normalize_text(combined_text)
            
            return (normalized_text, None)
            
        except Exception as e:
            return ("", f"Gagal membaca DOCX: {str(e)}")
    
    @staticmethod
    def _extract_txt(file_obj) -> Tuple[str, Optional[str]]:
        """Ekstrak teks dari TXT"""
        try:
            # Coba decode dengan beberapa encoding
            encodings = ['utf-8', 'latin-1', 'cp1252']
            
            for encoding in encodings:
                try:
                    file_obj.seek(0)
                    text = file_obj.read().decode(encoding)
                    normalized_text = DocumentExtractor._normalize_text(text)
                    return (normalized_text, None)
                except UnicodeDecodeError:
                    continue
            
            return ("", "Tidak bisa decode file TXT dengan encoding yang didukung")
            
        except Exception as e:
            return ("", f"Gagal membaca TXT: {str(e)}")
    
    @staticmethod
    def _normalize_text(text: str) -> str:
        """
        Normalisasi teks:
        - Hilangkan karakter non-printable
        - Rapikan whitespace
        - Hilangkan baris kosong berlebihan
        """
        # Hilangkan karakter kontrol kecuali newline dan tab
        text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
        
        # Normalisasi whitespace: ganti multiple spaces dengan single space
        text = re.sub(r' +', ' ', text)
        
        # Normalisasi newline: maksimal 2 newline berturut-turut
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Trim setiap baris
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        return text.strip()
