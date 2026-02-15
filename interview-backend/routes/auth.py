"""Authentication routes — user sync, profile, trial status."""
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any

from fastapi import APIRouter, HTTPException

from config import logger, TRIAL_DAYS
from schemas.user import UserSyncRequest, UserSyncResponse, UserProfileResponse
from services.session_manager import users_store

router = APIRouter(prefix="/api/auth", tags=["auth"])


def calculate_trial_status(created_at: str) -> Dict[str, Any]:
    """Calculate trial status based on account creation date."""
    try:
        created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        trial_end = created_date + timedelta(days=TRIAL_DAYS)
        now = datetime.utcnow()

        days_remaining = (trial_end - now).days
        is_active = days_remaining > 0

        return {
            "trial_start_date": created_at,
            "trial_end_date": trial_end.isoformat(),
            "trial_days_remaining": max(0, days_remaining),
            "trial_active": is_active
        }
    except Exception:
        return {
            "trial_start_date": created_at,
            "trial_end_date": "",
            "trial_days_remaining": TRIAL_DAYS,
            "trial_active": True
        }


@router.post("/sync-user", response_model=UserSyncResponse)
async def sync_user(request: UserSyncRequest):
    """Sync user from NextAuth OAuth to backend database."""
    try:
        for uid, user in users_store.items():
            if user["email"] == request.email:
                user["name"] = request.name or user["name"]
                user["image"] = request.image or user["image"]
                user["provider_id"] = request.provider_id or user["provider_id"]
                user["updated_at"] = datetime.utcnow().isoformat()
                logger.info(f"Updated existing user: {request.email}")
                return UserSyncResponse(success=True, user_id=uid, message="User updated successfully")

        user_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        trial_end = created_at + timedelta(days=TRIAL_DAYS)

        users_store[user_id] = {
            "id": user_id,
            "email": request.email,
            "name": request.name,
            "image": request.image,
            "provider": request.provider,
            "provider_id": request.provider_id,
            "created_at": created_at.isoformat(),
            "updated_at": created_at.isoformat(),
            "trial_start_date": created_at.isoformat(),
            "trial_end_date": trial_end.isoformat(),
            "subscription_status": "trial",
            "interview_sessions": []
        }

        logger.info(f"Created new user: {request.email} with ID: {user_id} (20-day trial started)")
        return UserSyncResponse(success=True, user_id=user_id, message="User created successfully with 20-day free trial")

    except Exception as e:
        logger.error(f"Error syncing user: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to sync user: {str(e)}")


@router.get("/user/{email}")
async def get_user_by_email(email: str):
    """Get user profile by email with trial status."""
    for uid, user in users_store.items():
        if user["email"] == email:
            trial_status = calculate_trial_status(user.get("created_at", datetime.utcnow().isoformat()))
            return {
                "id": user["id"],
                "email": user["email"],
                "name": user.get("name"),
                "image": user.get("image"),
                "provider": user.get("provider", "google"),
                "created_at": user.get("created_at", ""),
                "interview_count": len(user.get("interview_sessions", [])),
                "subscription_status": user.get("subscription_status", "trial"),
                **trial_status
            }
    raise HTTPException(status_code=404, detail="User not found")


@router.get("/trial-status/{email}")
async def get_trial_status(email: str):
    """Get trial status for a user."""
    for uid, user in users_store.items():
        if user["email"] == email:
            trial_status = calculate_trial_status(user.get("created_at", datetime.utcnow().isoformat()))
            return {
                "email": email,
                "subscription_status": user.get("subscription_status", "trial"),
                **trial_status
            }
    raise HTTPException(status_code=404, detail="User not found")


@router.get("/me")
async def get_current_user_placeholder():
    """Placeholder endpoint for getting current user."""
    return {"message": "Use NextAuth session on frontend to get current user"}
