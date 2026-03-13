"""Interview-related Pydantic models."""
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from schemas.voice import SoftSkillsFeedback


class InterviewAnswer(BaseModel):
    sessionId: str
    userAnswer: str
    behaviorData: Optional[dict] = Field(default=None, description="Optional behavioral scores array/dict")


# Question response types
class QuestionResponse(BaseModel):
    question: str = Field(..., description="The interview question.")
    type: str = Field(..., description="Type of the question, e.g., 'behavioral'.")


class CodingQuestionResponse(BaseModel):
    question: str = Field(..., description="The coding problem description.")
    initial_code: str = Field(..., description="Initial code snippet for the problem.")
    type: str = Field(..., description="Type of the question, e.g., 'technical'.")


class MCQQuestionResponse(BaseModel):
    question: str = Field(..., description="The multiple-choice question.")
    options: List[str] = Field(..., description="An array of possible answers.")
    correct_answer: str = Field(..., description="The correct answer to the question.")
    type: str = Field(..., description="Type of the question, 'mcq'.")


# Feedback
class FeedbackResponse(BaseModel):
    score: int
    strengths: List[str]
    weaknesses: List[str]
    feedback_text: str


# Composite responses
class InterviewStartResponse(BaseModel):
    message: str
    sessionId: str
    questionData: Union[QuestionResponse, CodingQuestionResponse, MCQQuestionResponse]
    roundTitle: str
    isComplete: bool
    feedback: FeedbackResponse | None = Field(default=None)


class InterviewSubmitResponse(BaseModel):
    questionData: Union[QuestionResponse, CodingQuestionResponse, MCQQuestionResponse]
    roundTitle: str
    isComplete: bool
    feedback: FeedbackResponse | None = Field(default=None)
    softSkills: Optional[SoftSkillsFeedback] = Field(default=None, description="Soft skills analysis per round")


# Hint
class HintRequest(BaseModel):
    sessionId: str
    currentAnswer: str = Field(default="", description="User's current partial answer")


class HintResponse(BaseModel):
    hint: str
    hint_type: str = Field(default="guidance", description="Type: guidance, example, or clarification")


# Interview summary
class InterviewSummaryResponse(BaseModel):
    session_id: str
    total_questions: int
    total_rounds: int
    overall_score: float
    time_taken_minutes: int
    round_summaries: List[dict]
    strengths: List[str]
    areas_for_improvement: List[str]
    recommendations: List[str]
    overall_feedback: str
    posture_report: Optional[dict] = Field(default=None, description="Behavioral analysis report from background posture engine")

