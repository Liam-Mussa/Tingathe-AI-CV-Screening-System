"""Authentication endpoints."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api_helpers import DB, current_user, user_response
from models import ApplicantProfile, User
from schemas import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from security import create_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DB):
    if not payload.consent:
        raise HTTPException(status_code=400, detail="Recruitment processing consent is required")
    email = payload.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="An account with that email already exists")

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        phone=payload.phone.strip() if payload.phone else None,
        role="applicant",
        preferred_language=payload.preferred_language,
    )
    db.add(user)
    db.flush()
    db.add(ApplicantProfile(user_id=user.id, district=payload.district, consent_at=datetime.utcnow()))
    db.commit()
    db.refresh(user)
    return AuthResponse(access_token=create_token(user.id, user.role), user=user_response(user))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: DB):
    email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email).one_or_none()
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return AuthResponse(access_token=create_token(user.id, user.role), user=user_response(user))


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(current_user)):
    return user_response(user)
