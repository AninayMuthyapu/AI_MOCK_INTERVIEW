"""Voice and soft skills Pydantic models."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class TTSRequest(BaseModel):
    text: str
    voice: str = "rachel"


class SoftSkillMetric(BaseModel):
    name: str
    score: float  # 0-5 scale
    feedback: str
    source: str = "ai"  # "ai" or "openSMILE"


class SoftSkillsFeedback(BaseModel):
    overallScore: int  # 0-100 scale
    metrics: List[SoftSkillMetric]
    details: Optional[Dict[str, Any]] = None
    openSmileFeatures: Optional[Dict[str, Any]] = None


class VoiceAnalysisResponse(BaseModel):
    pitch: Dict[str, float]
    energy: Dict[str, Any]
    voice_quality: Dict[str, float]
    temporal: Dict[str, Any]
    derived_scores: Dict[str, float]
    source: str = "openSMILE"
