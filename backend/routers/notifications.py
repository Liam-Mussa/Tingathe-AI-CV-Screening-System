"""Applicant notifications and administrator notification catalogue."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from typing import cast

from api_helpers import DB, current_user, director_only
from models import Notification, User
from schemas import NotificationResponse

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationResponse])
def list_notifications(db: DB, user: User = Depends(current_user)):
    entries = db.query(Notification).filter(Notification.recipient_id == user.id).order_by(Notification.created_at.desc()).all()
    return [NotificationResponse(id=str(entry.id), category=str(entry.category), title=str(entry.title), message=str(entry.message), is_read=bool(entry.is_read), created_at=datetime.fromisoformat(str(entry.created_at))) for entry in entries]


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_read(notification_id: str, db: DB, user: User = Depends(current_user)):
    entry = db.get(Notification, notification_id)
    if not entry or str(entry.recipient_id) != str(user.id):
        raise HTTPException(status_code=404, detail="Notification not found")
    setattr(entry, "is_read", True)
    db.commit()
    db.refresh(entry)
    return NotificationResponse(id=str(entry.id), category=str(entry.category), title=str(entry.title), message=str(entry.message), is_read=bool(entry.is_read), created_at=datetime.fromisoformat(str(entry.created_at)))


@router.get("/catalogue")
def catalogue(db: DB, _user: User = Depends(director_only)):
    types = [
        {"name": "Application decision", "category": "decision", "enabled": True, "description": "Sent when an application is shortlisted, held, or unsuccessful."},
        {"name": "Application received", "category": "application", "enabled": True, "description": "Sent when an applicant submits documents."},
        {"name": "Vacancy updates", "category": "vacancy", "enabled": True, "description": "Sent for vacancy publication and update events."},
        {"name": "Account security", "category": "security", "enabled": True, "description": "Sent for password and account security events."},
    ]
    return types
