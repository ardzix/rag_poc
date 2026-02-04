"""
Service untuk integrasi dengan DeepSeek LLM API
"""
import json
import requests
from typing import Dict, List, Optional, Tuple
from django.conf import settings


class DeepSeekService:
    """
    Service untuk memanggil DeepSeek API dan menghasilkan response chat
    """
    
    SYSTEM_PROMPT = """Anda adalah asisten analisis dokumen untuk aplikasi chat POC (RAG-like).

Aturan penting:
1) Jawab dalam Bahasa Indonesia.
2) Jangan tampilkan proses berpikir, penalaran, atau langkah-langkah internal. Tulis jawaban final saja.
3) Untuk pertanyaan yang membutuhkan fakta/angka dari dokumen, gunakan hanya CONTEXT yang diberikan. Jika tidak ada, katakan tidak ditemukan di dokumen.
4) Output HARUS berupa 1 objek JSON valid, tanpa teks lain, tanpa markdown, tanpa code block.
5) JSON hanya boleh memiliki 2 key: "text" dan "chart".
6) "chart" harus null kecuali diminta dan datanya cukup.

Jika diminta chart:
- "chart" harus mengikuti format konfigurasi Chart.js (type, data, options).
- Pilih "type" yang sesuai: "line" untuk time-series, "bar" untuk perbandingan kategori, "pie/doughnut" untuk proporsi.
- Pastikan data numerik berupa number (bukan string)."""
    
    @staticmethod
    def create_user_prompt(
        message: str,
        documents_context: str,
        include_chart: bool,
        document_ids: List[int]
    ) -> str:
        """
        Membuat user prompt dengan format konsisten
        """
        prompt = f"""INCLUDE_CHART: {str(include_chart).lower()}
DOCUMENT_IDS: {document_ids}

CONTEXT (dokumen terlampir):
{documents_context}

USER_MESSAGE:
{message}"""
        
        return prompt
    
    @staticmethod
    def prepare_documents_context(documents: List[Dict]) -> str:
        """
        Menyiapkan konteks dokumen dengan format yang rapi
        
        Args:
            documents: List of dict dengan keys: id, title, content
        
        Returns:
            String konteks yang siap dimasukkan ke prompt
        """
        if not documents:
            return "(Tidak ada dokumen konteks)"
        
        context_parts = []
        max_length = settings.DOCUMENT_CONTEXT_MAX_LENGTH
        
        for doc in documents:
            doc_id = doc.get('id', '?')
            title = doc.get('title', 'Untitled')
            content = doc.get('content', '')
            
            # Trim content jika terlalu panjang per dokumen
            # Alokasi proporsional untuk setiap dokumen
            max_per_doc = max_length // len(documents)
            if len(content) > max_per_doc:
                # Ambil dari awal dan akhir dokumen untuk memastikan data penting tidak hilang
                half = max_per_doc // 2
                content = (
                    content[:half] + 
                    "\n\n...[Bagian tengah dokumen dipotong]...\n\n" + 
                    content[-half:]
                )
            
            doc_context = f'<DOC id="{doc_id}" title="{title}">\n{content}\n</DOC>'
            context_parts.append(doc_context)
        
        combined = "\n\n".join(context_parts)
        
        # Safety check: jika masih terlalu panjang, potong lagi
        if len(combined) > max_length:
            combined = combined[:max_length] + "...\n[Konteks total dipotong]"
        
        return combined
    
    @staticmethod
    def call_deepseek(
        message: str,
        documents: List[Dict],
        include_chart: bool = False,
        document_ids: Optional[List[int]] = None,
        conversation_messages: Optional[List[Dict[str, str]]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Memanggil DeepSeek API
        
        Args:
            message: Pesan user
            documents: List dokumen untuk konteks
            include_chart: Apakah user meminta chart
            document_ids: List ID dokumen (untuk logging di prompt)
            conversation_messages: List messages historis DeepSeek (role/content),
                contoh: [{"role":"user","content":"..."},{"role":"assistant","content":"..."}]
        
        Returns:
            Tuple (response_dict, error_message)
            Jika sukses: ({"text": "...", "chart": {...}}, None)
            Jika gagal: (None, error_message)
        """
        try:
            # Siapkan konteks dokumen
            documents_context = DeepSeekService.prepare_documents_context(documents)
            
            # Buat user prompt
            user_prompt = DeepSeekService.create_user_prompt(
                message=message,
                documents_context=documents_context,
                include_chart=include_chart,
                document_ids=document_ids or []
            )
            
            # Siapkan rangkaian messages (multi-turn) jika ada history
            messages: List[Dict[str, str]] = [
                {"role": "system", "content": DeepSeekService.SYSTEM_PROMPT},
            ]
            if conversation_messages:
                # Pastikan formatnya benar dan tidak terlalu besar
                for m in conversation_messages:
                    role = (m or {}).get("role")
                    content = (m or {}).get("content")
                    if role in ("user", "assistant") and isinstance(content, str) and content.strip():
                        messages.append({"role": role, "content": content})

            # Tambahkan prompt user terbaru (sudah termasuk konteks dokumen)
            messages.append({"role": "user", "content": user_prompt})

            # Siapkan payload untuk DeepSeek API
            payload = {
                "model": settings.DEEPSEEK_MODEL,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 8000,  # Maximum untuk response lebih detail (impress client)
            }
            
            # Jika API mendukung response_format (untuk JSON mode)
            # payload["response_format"] = {"type": "json_object"}
            
            headers = {
                "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            }
            
            # Panggil API
            response = requests.post(
                settings.DEEPSEEK_API_URL,
                json=payload,
                headers=headers,
                timeout=settings.DEEPSEEK_TIMEOUT
            )
            
            if response.status_code != 200:
                return (None, f"DeepSeek API error: {response.status_code} - {response.text}")
            
            # Parse response
            response_data = response.json()
            content = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            if not content:
                return (None, "DeepSeek tidak mengembalikan konten")
            
            # Parse JSON dari content
            parsed = DeepSeekService.parse_llm_response(content)
            
            if parsed is None:
                # Fallback: jika JSON invalid, kembalikan text saja
                return ({"text": content, "chart": None}, None)
            
            return (parsed, None)
            
        except requests.Timeout:
            return (None, "Timeout saat memanggil DeepSeek API")
        except requests.RequestException as e:
            return (None, f"Error koneksi ke DeepSeek: {str(e)}")
        except Exception as e:
            return (None, f"Error tidak terduga: {str(e)}")
    
    @staticmethod
    def parse_llm_response(content: str) -> Optional[Dict]:
        """
        Parse response dari LLM yang seharusnya berupa JSON
        
        Returns:
            Dict dengan keys "text" dan "chart", atau None jika gagal parse
        """
        try:
            # Clean content: hilangkan markdown code fence jika ada
            content = content.strip()
            
            # Hilangkan ```json dan ``` jika ada
            if content.startswith('```'):
                lines = content.split('\n')
                # Hilangkan baris pertama dan terakhir
                if len(lines) > 2:
                    if lines[-1].strip() == '```':
                        content = '\n'.join(lines[1:-1])
                    else:
                        content = '\n'.join(lines[1:])
            
            # Parse JSON
            parsed = json.loads(content)
            
            # Validasi struktur
            if not isinstance(parsed, dict):
                return None
            
            # Pastikan ada key text dan chart
            if 'text' not in parsed:
                return None
            
            # Normalisasi: pastikan chart ada (bisa null)
            if 'chart' not in parsed:
                parsed['chart'] = None
            
            return parsed
            
        except json.JSONDecodeError:
            return None
        except Exception:
            return None
