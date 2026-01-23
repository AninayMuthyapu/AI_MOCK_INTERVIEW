"""
Database Models for AI Mock Interview Platform
Defines User, InterviewSession, Question, and SoftSkillsMetric tables
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base
import uuid


def generate_uuid() -> str:
    """Generate a unique session ID."""
    return str(uuid.uuid4())


class User(Base):
    """User account model for OAuth authentication."""
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    image: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    provider: Mapped[str] = mapped_column(String(50), default="google")  # OAuth provider
    provider_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # OAuth provider user ID
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    interview_sessions: Mapped[List["InterviewSession"]] = relationship(
        "InterviewSession", back_populates="user", cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class InterviewSession(Base):
    """Interview session model - tracks a complete interview."""
    __tablename__ = "interview_sessions"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    
    # Job details
    job_role: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    years_of_experience: Mapped[int] = mapped_column(Integer, default=0)
    job_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resume_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Interview plan
    interview_plan: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Current state
    current_round_index: Mapped[int] = mapped_column(Integer, default=0)
    current_question_index: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, completed, abandoned
    
    # Scores and feedback
    overall_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="interview_sessions")
    questions: Mapped[List["Question"]] = relationship(
        "Question", back_populates="session", cascade="all, delete-orphan"
    )
    soft_skills_metrics: Mapped[List["SoftSkillsMetric"]] = relationship(
        "SoftSkillsMetric", back_populates="session", cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<InterviewSession(id={self.id}, role={self.job_role}, status={self.status})>"


class Question(Base):
    """Individual question in an interview session."""
    __tablename__ = "questions"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("interview_sessions.id"), nullable=False, index=True)
    
    # Question details
    round_title: Mapped[str] = mapped_column(String(255), nullable=False)
    round_type: Mapped[str] = mapped_column(String(50), nullable=False)  # behavioral, technical, dsa, mcq
    question_number: Mapped[int] = mapped_column(Integer, default=1)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    
    # For coding questions
    initial_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # For MCQ questions
    mcq_options: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    mcq_correct_answer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # User's answer
    user_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Feedback
    score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0-10
    feedback_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    strengths: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    weaknesses: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    # Timing
    time_spent_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    answered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    session: Mapped["InterviewSession"] = relationship("InterviewSession", back_populates="questions")
    
    def __repr__(self):
        return f"<Question(id={self.id}, type={self.round_type}, score={self.score})>"


class SoftSkillsMetric(Base):
    """Soft skills analysis for a session or round."""
    __tablename__ = "soft_skills_metrics"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("interview_sessions.id"), nullable=False, index=True)
    
    # Which round this metric is for (optional - null means overall session)
    round_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Metric details
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "eye_contact", "confidence", "clarity"
    score: Mapped[float] = mapped_column(Float, nullable=False)  # 0-5 scale
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="ai")  # "ai" or "opensmile" or "mediapipe"
    
    # Raw data (for debugging/analysis)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session: Mapped["InterviewSession"] = relationship("InterviewSession", back_populates="soft_skills_metrics")
    
    def __repr__(self):
        return f"<SoftSkillsMetric(metric={self.metric_name}, score={self.score})>"


class TokenUsage(Base):
    """Track AI token usage per session."""
    __tablename__ = "token_usage"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("interview_sessions.id"), nullable=True, index=True)
    
    # Token counts
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    
    # API call type
    endpoint: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "generate_question", "evaluate_answer"
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<TokenUsage(session={self.session_id}, tokens={self.total_tokens})>"
