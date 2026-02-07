"""
Views untuk Chat API
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import ChatLog
from .serializers import ChatRequestSerializer, ChatResponseSerializer, ChatLogSerializer
from core.authentication import SSOAuthentication
from core.deepseek_service import DeepSeekService
from core.chat_helper import detect_chart_needed
from documents.models import Document
from core.swagger_schemas import chat_create_schema, chat_history_schema


class ChatViewSet(viewsets.ViewSet):
    """
    ViewSet untuk chat dengan LLM
    
    Endpoints:
    - POST /api/chat - Kirim pesan dan terima response
    """
    
    authentication_classes = [SSOAuthentication]
    permission_classes = [IsAuthenticated]
    
    @chat_create_schema
    def create(self, request):
        """
        Chat dengan LLM menggunakan dokumen sebagai konteks
        
        POST /api/chat
        
        Sistem akan otomatis:
        - Mengambil semua dokumen dari database (global RAG POC)
        - Mendeteksi apakah perlu chart berdasarkan kata kunci di message
        """
        serializer = ChatRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {"error": "Validasi gagal", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        message = serializer.validated_data['message']
        conversation_id = serializer.validated_data.get('conversation_id')
        
        # Auto-detect apakah perlu chart dari message
        include_chart = detect_chart_needed(message)

        # Ambil history percakapan jika conversation_id ada (multi-turn context)
        # Ambil beberapa turn terakhir agar follow-up seperti "tampilkan dalam bentuk chart"
        # tetap memiliki konteks dari pertanyaan sebelumnya.
        conversation_messages = []
        if conversation_id:
            try:
                # Ambil 10 chat terakhir dalam room ini (ascending agar urut)
                recent_logs = list(
                    ChatLog.objects.filter(
                        owner_user_id=request.user.user_id,
                        conversation_id=conversation_id
                    ).order_by('-created_at')[:10]
                )
                recent_logs.reverse()

                for log in recent_logs:
                    if log.user_message:
                        conversation_messages.append(
                            {"role": "user", "content": log.user_message}
                        )
                    if log.response_text:
                        # Simpan jawaban AI sebagai assistant message (tanpa chart config)
                        conversation_messages.append(
                            {"role": "assistant", "content": log.response_text}
                        )
            except Exception:
                # Jika gagal ambil history, lanjut tanpa history
                conversation_messages = []
        
        # Ambil SEMUA dokumen dari database (POC: dokumen global, bukan per-user)
        documents = Document.objects.all().order_by('-created_at')
        
        # Konversi ke format yang dibutuhkan DeepSeek service
        documents_data = [
            {
                'id': doc.id,
                'title': doc.title,
                'content': doc.content,
                'structured_data': doc.structured_data
            }
            for doc in documents
        ]
        
        # Extract document IDs untuk logging
        document_ids = [doc.id for doc in documents]
        
        # Panggil DeepSeek
        response_data, error_msg = DeepSeekService.call_deepseek(
            message=message,
            documents=documents_data,
            include_chart=include_chart,
            document_ids=document_ids,
            conversation_messages=conversation_messages,
        )
        
        if error_msg:
            return Response(
                {
                    "error": "Gagal mendapatkan response dari LLM",
                    "details": error_msg
                },
                status=status.HTTP_502_BAD_GATEWAY
            )
        
        # Simpan ke chat log (opsional)
        try:
            ChatLog.objects.create(
                owner_user_id=request.user.user_id,
                user_message=message,
                response_text=response_data.get('text', ''),
                response_chart_json=response_data.get('chart'),
                document_ids=document_ids,
                conversation_id=conversation_id
            )
        except Exception:
            # Jika gagal save log, tidak perlu error ke user
            pass
        
        # Return response
        return Response(response_data, status=status.HTTP_200_OK)


class ChatHistoryViewSet(viewsets.ViewSet):
    """
    ViewSet untuk melihat history chat (opsional)
    
    Endpoints:
    - GET /api/chat/history - List chat history
    """
    
    authentication_classes = [SSOAuthentication]
    permission_classes = [IsAuthenticated]
    
    @chat_history_schema
    def list(self, request):
        """
        List chat history untuk user
        
        GET /api/chat/history
        """
        # Filter berdasarkan owner_user_id
        chat_logs = ChatLog.objects.filter(
            owner_user_id=request.user.user_id
        ).order_by('-created_at')[:50]  # Ambil 50 terakhir
        
        serializer = ChatLogSerializer(chat_logs, many=True)
        
        return Response({
            "count": chat_logs.count(),
            "history": serializer.data
        })
