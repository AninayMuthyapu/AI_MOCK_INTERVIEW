"""Resume and plan preview Pydantic models."""
from typing import List
from pydantic import BaseModel


class ATSReviewResponse(BaseModel):
    ats_score: int
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    keyword_match_percentage: int
    overall_feedback: str


class PlanItem(BaseModel):
    title: str
    type: str
    question_count: int
    estimated_minutes: int


class PlanPreviewResponse(BaseModel):
    inferred_role: str
    inferred_years_of_experience: int
    inferred_company: str
    rounds: List[PlanItem]
    total_questions: int
    total_estimated_minutes: int
    is_ai_generated: bool
    generation_source: str
