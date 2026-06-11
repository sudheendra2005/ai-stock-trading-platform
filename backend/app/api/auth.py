import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import User
from app.schemas.schemas import UserCreate, UserOut, Token, UserLogin
from app.core.security import get_password_hash, verify_password, create_access_token, decode_access_token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")
    
    username: str = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

@router.post("/register", response_model=UserOut)
async def register(user_in: UserCreate, db: Session = Depends(get_db)):
    logger.info(f"Registration attempt for user: {user_in.username} ({user_in.email})")
    try:
        if db.query(User).filter(User.username == user_in.username).first():
            logger.warning(f"Username {user_in.username} already exists")
            raise HTTPException(status_code=400, detail="Username already registered")
        if db.query(User).filter(User.email == user_in.email).first():
            logger.warning(f"Email {user_in.email} already exists")
            raise HTTPException(status_code=400, detail="Email already registered")
        
        hashed_pw = get_password_hash(user_in.password)
        new_user = User(
            username=user_in.username,
            email=user_in.email,
            hashed_password=hashed_pw
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        logger.info(f"User {user_in.username} registered successfully")
        return new_user
    except Exception as e:
        logger.error(f"Registration error: {str(e)}", exc_info=True)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/login", response_model=Token)
async def login(login_data: UserLogin, db: Session = Depends(get_db)):
    email = login_data.email
    password = login_data.password
    logger.info(f"Login attempt for email: {email}")
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        logger.warning(f"Failed login attempt for email: {email}")
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": user.username})
    logger.info(f"User {user.username} logged in successfully")
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/verify-email")
async def verify_email(payload: dict, db: Session = Depends(get_db)):
    token = payload.get("token")
    logger.info(f"Verification attempt for token/email: {token}")
    user = db.query(User).filter(User.email == token).first()
    if not user:
        logger.warning(f"Verification failed: user {token} not found")
        raise HTTPException(status_code=404, detail="User not found")
    user.is_verified = True
    db.commit()
    logger.info(f"User {user.email} verified successfully")
    return {"message": "Email verified successfully"}

@router.post("/reset-balance")
async def reset_balance(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    logger.info(f"Resetting balance for user {current_user.username}")
    current_user.balance = 100000.0
    db.commit()
    db.refresh(current_user)
    return {"message": "Balance reset successfully", "balance": current_user.balance}

