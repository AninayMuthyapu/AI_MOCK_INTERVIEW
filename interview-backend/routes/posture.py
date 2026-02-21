"""Posture analysis route — raw report endpoint."""
from typing import Optional
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api", tags=["posture"])


@router.get("/posture-report/{session_id}")
async def get_posture_report(session_id: str):
    """Returns the raw posture analysis report for a session."""
    try:
        from services.posture_service import posture_service
    except ImportError:
        raise HTTPException(status_code=503, detail="Posture service unavailable")

    report = posture_service.get_report(session_id)
    if report is None:
        # Try stopping (in case interview is still running)
        report = posture_service.stop_background(session_id)

    if report is None:
        raise HTTPException(status_code=404, detail="No posture report found for this session")

    return report
