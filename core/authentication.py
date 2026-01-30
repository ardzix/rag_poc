"""
Authentication middleware dan utilities untuk integrasi dengan SSO
"""
import requests
import jwt
from django.conf import settings
from rest_framework import authentication, exceptions
from django.core.cache import cache


class SSOAuthentication(authentication.BaseAuthentication):
    """
    Custom authentication class untuk memverifikasi Bearer token via SSO
    """
    
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header:
            return None
        
        # Parse Bearer token
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            raise exceptions.AuthenticationFailed('Format Authorization header tidak valid. Gunakan: Bearer <token>')
        
        token = parts[1]
        
        # Cek cache untuk menghindari pemanggilan SSO berulang
        cache_key = f'sso_token_{token[:20]}'  # Gunakan prefix token sebagai cache key
        cached_user_id = cache.get(cache_key)
        
        if cached_user_id:
            # Token valid dari cache
            return (MockUser(cached_user_id), token)
        
        # Verifikasi token ke SSO
        user_id = self.verify_token_with_sso(token)
        
        if not user_id:
            raise exceptions.AuthenticationFailed('Token tidak valid atau expired')
        
        # Cache hasil verifikasi untuk 60 detik
        cache.set(cache_key, user_id, 60)
        
        return (MockUser(user_id), token)
    
    def verify_token_with_sso(self, token):
        """
        Verifikasi token ke SSO service dan ekstrak user_id
        
        Returns:
            user_id (str) jika valid, None jika tidak valid
        """
        try:
            # Coba decode JWT untuk mendapatkan user_id tanpa verifikasi signature
            # (karena kita akan verifikasi via SSO endpoint)
            decoded = jwt.decode(token, options={"verify_signature": False})
            
            # Verifikasi ke SSO
            sso_url = f"{settings.SSO_BASE_URL}{settings.SSO_VERIFY_TOKEN_ENDPOINT}"
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(sso_url, headers=headers, json={'token': token}, timeout=5)
            
            if response.status_code == 200:
                # Token valid, ekstrak user_id dari JWT payload
                # Coba beberapa claim standar
                user_id = decoded.get('user_id') or decoded.get('sub') or decoded.get('id')
                
                if user_id:
                    return str(user_id)
            
            return None
            
        except jwt.DecodeError:
            return None
        except requests.RequestException:
            # Jika SSO tidak bisa dihubungi, sebaiknya reject untuk keamanan
            return None
        except Exception:
            return None


class MockUser:
    """
    Mock user object untuk menyimpan user_id dari SSO
    Django REST framework memerlukan user object
    """
    
    def __init__(self, user_id):
        self.id = user_id
        self.user_id = user_id
        self.is_authenticated = True
        self.is_active = True
    
    def __str__(self):
        return f"SSO User {self.user_id}"
