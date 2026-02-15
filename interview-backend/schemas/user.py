"""User authentication Pydantic models."""
from typing import Optional
from pydantic import BaseModel


class UserSyncRequest(BaseModel):
    """Request model for syncing user from NextAuth to backend."""
    email: str
    name: Optional[str] = None
    image: Optional[str] = None
    provider: str = "google"
    provider_id: Optional[str] = None


class UserSyncResponse(BaseModel):
    """Response model for user sync."""
    success: bool
    user_id: str
    message: str


class UserProfileResponse(BaseModel):
    """Response model for user profile."""
    id: str
    email: str
    name: Optional[str]
    image: Optional[str]
    provider: str
    created_at: str
    interview_count: int
