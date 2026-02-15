"""Vision analysis Pydantic models."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class VisionAnalysisRequest(BaseModel):
    image: str = Field(..., description="Base64 encoded image from webcam")
    sessionId: Optional[str] = Field(None, description="Session ID to track behavior over time")


class VisionAnalysisResponse(BaseModel):
    presence: bool
    eye_contact: str
    confidence_score: int
    posture: Dict[str, Any]
    head_pose: Dict[str, float]
    feedback: List[str]
    overall: str
    timestamp: float
    # Enhanced fields from posture analysis engine
    attention_score: Optional[float] = None
    attention_state: Optional[str] = None
    posture_quality: Optional[str] = None
    posture_score: Optional[float] = None
    eye_contact_score: Optional[float] = None
    gaze_direction: Optional[str] = None
    movement_score: Optional[float] = None
    nervousness_level: Optional[str] = None
    confidence_level: Optional[str] = None
