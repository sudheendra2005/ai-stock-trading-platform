from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from schemas.auth import UserCreate, UserLogin, Token, UserResponse
from services.auth_service import (
    get_user_by_email,
    get_user_by_username,
    create_user,
    authenticate_user,
    create_access_token,
    generate_verification_token,
    generate_reset_token
)
from database import get_db
from jose import JWTError, jwt
from config import settings
from datetime import datetime, timedelta
from models import User, Wallet
from services.auth_service import pwd_context
from schemas.auth import VerifyEmail, PasswordResetRequest, PasswordReset

router = APIRouter()

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    db_user = get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if username already exists
    db_username = get_user_by_username(db, username=user.username)
    if db_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create new user and get verification token
    created_user, verification_token = create_user(db=db, user=user)
    
    # In a real application, you would send this token via email
    # For now, we return it in the response (in production, don't return it)
    return {
        "message": "User created successfully. Please check your email for verification.",
        "user_id": created_user.id,
        "email": created_user.email,
        "verification_token": verification_token  # Remove this in production!
    }

@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, user_credentials.email, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if email is verified
    # if not user.is_verified:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Email not verified. Please verify your email before logging in."
    #     )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/verify-email")
async def verify_email(data: VerifyEmail, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.verification_token == data.token).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token"
        )
    
    # Check if token has expired
    if user.verification_token_expires and user.verification_token_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired"
        )
    
    # Mark email as verified
    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires = None
    db.commit()
    
    return {"message": "Email verified successfully"}

@router.post("/request-password-reset")
async def request_password_reset(data: PasswordResetRequest, db: Session = Depends(get_db)):
    user = get_user_by_email(db, data.email)
    # Always return same message to prevent user enumeration
    if user:
        # Generate reset token
        reset_token = generate_reset_token()
        reset_token_expires = datetime.utcnow() + timedelta(hours=1)  # 1 hour to reset
        
        user.reset_token = reset_token
        user.reset_token_expires = reset_token_expires
        db.commit()
        
        # In a real application, you would send this token via email
        # For now, we return it in the response (in production, don't return it)
        return {
            "message": "If the email exists, a password reset link has been sent.",
            "reset_token": reset_token  # Remove this in production!
        }
    
    return {"message": "If the email exists, a password reset link has been sent."}

@router.post("/reset-password")
async def reset_password(data: PasswordReset, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.reset_token == data.token).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Check if token has expired
    if user.reset_token_expires and user.reset_token_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Validate password strength
    if len(data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    # Hash new password
    hashed_password = pwd_context.hash(data.password)
    user.password_hash = hashed_password
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    
    return {"message": "Password has been reset successfully"}

def _ensure_wallet(user_id: int, db: Session) -> Wallet:
    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
    if not wallet:
        wallet = Wallet(user_id=user_id, balance=100000.0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    return wallet


@router.get("/me", response_model=UserResponse)
async def get_current_user(token: str = Depends(HTTPBearer()), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    wallet = _ensure_wallet(user.id, db)
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_verified": user.is_verified,
        "balance": round(wallet.balance, 2),
    }


@router.post("/reset-balance")
async def reset_balance(token: str = Depends(HTTPBearer()), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception

    wallet = _ensure_wallet(user.id, db)
    wallet.balance = 100000.0
    db.commit()
    db.refresh(wallet)
    return {"message": "Balance reset successfully", "balance": round(wallet.balance, 2)}
