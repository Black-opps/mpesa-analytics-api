"""
JWT Authentication for Analytics Service
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.core.database import get_db

# ====================== CONFIG ======================
# Use JWT_SECRET_KEY first, fallback to SECRET_KEY
SECRET_KEY = os.getenv("JWT_SECRET_KEY", os.getenv("SECRET_KEY", "your-super-secret-jwt-key-change-this-in-production-12345"))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Validate token coming from Gateway"""
   
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Development fallback - if no token, return admin user
    if not token:
        from src.models.user import User
        user = db.query(User).filter(User.email == "admin@example.com").first()
        if user:
            print("WARNING: Using development fallback user (admin@example.com)")
            return user
        raise credentials_exception
    
    try:
        # Decode token with the same logic as debug endpoint
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        email = payload.get("email")
       
        if user_id is None:
            print("❌ No user_id in token payload")
            raise credentials_exception
            
        print(f"✅ Token decoded successfully: user_id={user_id}, email={email}")
        
    except JWTError as e:
        print(f"[ERROR] JWT Error: {e}")
        raise credentials_exception
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        raise credentials_exception
    
    # Import User model inside the function to avoid circular imports
    from src.models.user import User
    
    # Find user by ID (as string, since it's UUID)
    user = db.query(User).filter(User.id == user_id).first()
   
    if user is None:
        # Try by email as fallback
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            print(f"❌ User not found: id={user_id}, email={email}")
            raise credentials_exception
    
    print(f"✅ User authenticated: {user.email} (id: {user.id})")
    return user