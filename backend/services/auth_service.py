from sqlalchemy.orm import Session
from models import User
from schemas.auth import UserCreate
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from config import settings
import secrets
import string

# Password hashing context
# New hashes use pbkdf2_sha256 to avoid bcrypt/passlib runtime failures in
# serverless environments. Bcrypt stays enabled so existing users can log in.
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, user: UserCreate):
    hashed_password = pwd_context.hash(user.password)
    # Generate email verification token
    verification_token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
    verification_token_expires = datetime.utcnow() + timedelta(hours=24)  # 24 hours to verify
    
    db_user = User(
        username=user.username,
        email=user.email,
        password_hash=hashed_password,
        verification_token=verification_token,
        verification_token_expires=verification_token_expires
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    # Create a wallet for the user with initial balance
    from models import Wallet
    wallet = Wallet(user_id=db_user.id, balance=100000.0)
    db.add(wallet)
    db.commit()
    return db_user, verification_token

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def authenticate_user(db: Session, email: str, password: str):
    # Get user with failed login tracking
    user = get_user_by_email(db, email)
    
    # If user doesn't exist, simulate same delay to prevent user enumeration
    if not user:
        pwd_context.verify("dummy", "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW")  # waste time
        return False
    
    # Check if account is locked due to too many failed attempts
    if user.failed_login_attempts >= 5:
        # Check if lockout period has passed (15 minutes)
        if user.last_failed_login and (datetime.utcnow() - user.last_failed_login).total_seconds() < 900:
            return False  # Still locked
        else:
            # Reset failed attempts after lockout period
            user.failed_login_attempts = 0
            db.add(user)
            db.commit()
    
    # Verify password
    if not verify_password(password, user.password_hash):
        # Increment failed login attempts
        user.failed_login_attempts += 1
        user.last_failed_login = datetime.utcnow()
        db.add(user)
        db.commit()
        return False
    
    # Reset failed attempts on successful login
    user.failed_login_attempts = 0
    user.last_failed_login = None
    db.add(user)
    db.commit()
    return user

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def generate_verification_token():
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))

def generate_reset_token():
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
