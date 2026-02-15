"""Token usage tracking routes."""
from fastapi import APIRouter

from services.token_tracker import token_tracker

router = APIRouter(prefix="/api", tags=["tokens"])


@router.get("/token-stats/{session_id}")
async def get_token_stats(session_id: str):
    """Get AI token usage statistics for a session."""
    session_stats = token_tracker.get_session_stats(session_id)
    global_stats = token_tracker.get_global_stats()

    return {
        "session": session_stats,
        "global": global_stats,
        "session_id": session_id
    }


@router.get("/token-stats")
async def get_global_token_stats():
    """Get global AI token usage statistics across all sessions."""
    return token_tracker.get_global_stats()
