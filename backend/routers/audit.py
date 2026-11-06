"""Read-only Director audit log endpoint."""
from fastapi import APIRouter, Depends, Query

from api_helpers import DB, audit_response, director_only
from models import AuditLog, User

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
def list_audit(
    db: DB,
    limit: int = Query(default=100, ge=1, le=500),
    user: User = Depends(director_only),
):
    entries = (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
        .all()
    )
    return [audit_response(entry, db) for entry in entries]
