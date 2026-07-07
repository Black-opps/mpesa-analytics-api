"""
JWKS Token Validator for Analytics Service
Validates tokens using Auth Service's public keys
"""

import jwt
import requests
from jose import jwt as jose_jwt
from jose.exceptions import JWTError
from fastapi import HTTPException, status
import os
import time
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class JWKSValidator:
    """Validates JWT tokens using JWKS from Auth Service"""
    
    def __init__(self, jwks_url: str = "http://localhost:8001/.well-known/jwks.json"):
        self.jwks_url = jwks_url
        self.jwks_cache = None
        self.cache_time = 0
        self.cache_ttl = 300  # 5 minutes
        
    def _fetch_jwks(self):
        """Fetch JWKS from Auth Service"""
        try:
            response = requests.get(self.jwks_url, timeout=5)
            response.raise_for_status()
            self.jwks_cache = response.json()
            self.cache_time = time.time()
            logger.info("JWKS fetched successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            return False
    
    def _get_jwks(self):
        """Get JWKS from cache or fetch if expired"""
        if not self.jwks_cache or (time.time() - self.cache_time) > self.cache_ttl:
            self._fetch_jwks()
        return self.jwks_cache
    
    def _get_public_key(self, kid: str) -> Optional[str]:
        """Get public key for given kid from JWKS"""
        jwks = self._get_jwks()
        if not jwks:
            return None
            
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                # Construct public key from JWK
                from jwt.algorithms import RSAAlgorithm
                return RSAAlgorithm.from_jwk(key)
        return None
    
    def validate_token(self, token: str) -> Dict:
        """Validate JWT token using JWKS"""
        try:
            # Get unverified header to extract kid
            headers = jwt.get_unverified_header(token)
            kid = headers.get("kid")
            
            if not kid:
                raise HTTPException(status_code=401, detail="Missing key ID")
            
            # Get public key
            public_key = self._get_public_key(kid)
            if not public_key:
                # Try to refresh JWKS once
                self._fetch_jwks()
                public_key = self._get_public_key(kid)
                if not public_key:
                    raise HTTPException(status_code=401, detail="Unknown signing key")
            
            # Verify token
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                options={"verify_aud": False}
            )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {e}")
            raise HTTPException(status_code=401, detail="Invalid token")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Validation error: {e}")
            raise HTTPException(status_code=401, detail="Authentication failed")

# Singleton instance
validator = JWKSValidator()

def get_current_user(token: str = None):
    """Dependency for protected endpoints"""
    from fastapi import Request
    
    def dependency(request: Request):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        token = auth_header.replace("Bearer ", "")
        return validator.validate_token(token)
    
    return dependency
