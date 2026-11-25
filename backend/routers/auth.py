"""Authentication endpoints."""
from datetime import datetime, timedelta
import hashlib
import secrets
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api_helpers import DB, audit, current_user, director_only, user_response
from models import ApplicantProfile, PasswordResetToken, User
from schemas import AuthResponse, LoginRequest, PasswordResetConfirm, PasswordResetRequest, RegisterRequest, UserResponse
from security import create_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DB):
    if not payload.consent:
        raise HTTPException(status_code=400, detail="Recruitment processing consent is required")
    if payload.password_confirmation is not None and payload.password != payload.password_confirmation:
        raise HTTPException(status_code=400, detail="Password confirmation does not match")
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if not any(ch.isupper() for ch in payload.password) or not any(ch.isdigit() for ch in payload.password):
        raise HTTPException(status_code=400, detail="Password must include one uppercase letter and one number")
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
    audit(db, "Registered account", user.id, "user", str(user.id), {"email": email, "role": "applicant"})
    db.commit()
    db.refresh(user)
    return AuthResponse(access_token=create_token(str(user.id), str(user.role)), user=user_response(user))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: DB):
    email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email).one_or_none()
    if not user or not bool(user.is_active) or not verify_password(payload.password, str(user.password_hash)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    audit(db, "Signed in", user.id, "user", str(user.id))
    db.commit()
    return AuthResponse(access_token=create_token(str(user.id), str(user.role)), user=user_response(user))


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(current_user)):
    return user_response(user)


@router.get("/users", response_model=list[UserResponse])
def list_users(db: DB, _user: User = Depends(director_only)):
    users = db.query(User).order_by(User.created_at.asc()).all()
    return [user_response(user) for user in users]


@router.post("/forgot-password")
def forgot_password(payload: PasswordResetRequest, db: DB):
    email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email).one_or_none()
    if user:
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        db.add(PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(minutes=30),
        ))
        db.commit()
        # Return the token for the local deployment UI; production email delivery
        # should replace this with an emailed link and omit the token from responses.
        return {"message": "If the email exists, password reset instructions are available.", "reset_token": raw_token}
    return {"message": "If the email exists, password reset instructions are available."}


@router.post("/reset-password")
def reset_password(payload: PasswordResetConfirm, db: DB):
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    reset = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash,
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.expires_at > datetime.utcnow(),
    ).one_or_none()
    if not reset:
        raise HTTPException(status_code=400, detail="Reset link is invalid or has expired")
    if len(payload.password) < 8 or not any(ch.isupper() for ch in payload.password) or not any(ch.isdigit() for ch in payload.password):
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters and include an uppercase letter and number")
    if payload.password != payload.password_confirmation:
        raise HTTPException(status_code=400, detail="Password confirmation does not match")
    user = db.get(User, reset.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Account not found")
    setattr(user, "password_hash", hash_password(payload.password))
    setattr(reset, "used_at", datetime.utcnow())
    audit(db, "Reset password", user.id, "user", str(user.id))
    db.commit()
    return {"message": "Password reset successfully"}


@router.delete("/users/{user_id}")
def delete_user(user_id: str, db: DB, director: User = Depends(director_only)):
    from api_helpers import _parse_uuid
    user = db.get(User, _parse_uuid(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if str(user.id) == str(director.id):
        raise HTTPException(status_code=400, detail="You cannot delete your own Director account")
    name = user.full_name
    audit(db, "Deleted account", director.id, "user", str(user.id), {"name": name, "email": user.email})
    db.delete(user)
    db.commit()
    return {"message": "Account deleted successfully"}
