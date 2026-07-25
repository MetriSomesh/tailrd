"""Account management: deletion and data export (DPDP Act 2023 compliance).

DELETE /account — marks for deletion with grace period
GET /account/export — returns a JSON bundle of all user data
POST /account/recover — cancels a pending deletion within the grace period
"""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user, require_csrf
from app.core.errors import BadRequestError, ConflictError
from app.db.base import utcnow
from app.db.models.consent import ConsentRecord
from app.db.models.user import User
from app.db.session import get_session
from app.schemas.auth import MessageResponse
from app.services import auth as auth_service

router = APIRouter(prefix="/account", tags=["account"])


@router.delete("", response_model=MessageResponse, dependencies=[Depends(require_csrf)])
async def delete_account(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Initiate account deletion with a grace period.

    During the grace period the account is deactivated but not purged. The user
    can recover by logging in and calling POST /account/recover.

    After the grace period, a background job hard-deletes all user data including
    S3 objects. This is a non-reversible operation.
    """
    if user.deleted_at is not None:
        raise ConflictError("Account is already scheduled for deletion.")

    user.deleted_at = utcnow()
    user.is_active = False

    # Revoke all sessions immediately
    await auth_service.revoke_all_sessions(db, user_id=user.id)

    # Record consent withdrawal
    result = await db.execute(
        select(ConsentRecord)
        .where(ConsentRecord.user_id == user.id, ConsentRecord.withdrawn_at.is_(None))
    )
    for consent in result.scalars():
        consent.withdrawn_at = utcnow()

    await db.commit()

    grace_days = settings.ACCOUNT_DELETION_GRACE_DAYS
    return MessageResponse(
        message=f"Account scheduled for deletion. You have {grace_days} days to recover it by logging in."
    )


@router.post("/recover", response_model=MessageResponse)
async def recover_account(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Cancel a pending deletion if within the grace period."""
    if user.deleted_at is None:
        raise BadRequestError("Account is not scheduled for deletion.")

    deadline = user.deleted_at + timedelta(days=settings.ACCOUNT_DELETION_GRACE_DAYS)
    if utcnow() > deadline:
        raise BadRequestError("Grace period has passed. Account cannot be recovered.")

    user.deleted_at = None
    user.is_active = True
    await db.commit()

    return MessageResponse(message="Account recovered successfully.")


@router.get("/export")
async def export_data(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Export all user data as a JSON document (DPDP Act right to data portability).

    Returns profile, sessions, consent records, and run metadata. DOCX files are
    referenced by their download URL (they can be fetched separately).
    """
    # Consent records
    consent_result = await db.execute(
        select(ConsentRecord).where(ConsentRecord.user_id == user.id)
    )
    consents = [
        {
            "policy_version": c.policy_version,
            "consented_at": c.consented_at.isoformat() if c.consented_at else None,
            "withdrawn_at": c.withdrawn_at.isoformat() if c.withdrawn_at else None,
        }
        for c in consent_result.scalars()
    ]

    return {
        "export_version": "1.0",
        "exported_at": utcnow().isoformat(),
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "auth_provider": user.auth_provider,
            "email_verified": user.is_email_verified,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        },
        "consent_records": consents,
        # Profile, runs, and billing data added in later phases as those models exist.
        "profile": None,
        "runs": [],
        "billing": None,
    }
