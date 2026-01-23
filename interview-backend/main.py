import os
import json
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from dotenv import load_dotenv
import base64
import docx
from PyPDF2 import PdfReader

# Import the Gemini SDK
import google.generativeai as genai
from voice_service import VoiceService
from avatar_service import AvatarService
from vision_service import VisionService
from opensmile_service import get_opensmile_service

# Logging setup
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable not set. Please create interview-backend/.env with GOOGLE_API_KEY=<your_key>.")

# Configure the Gemini client
genai.configure(api_key=API_KEY)

# Safety settings to prevent blocking (use proper enum values)
from google.generativeai.types import HarmCategory, HarmBlockThreshold

SAFETY_SETTINGS = [
    {
        "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
]

# Initialize the Gemini model - using flash for lower quota usage
model = genai.GenerativeModel(
    'gemini-2.5-flash',
    safety_settings=SAFETY_SETTINGS
)

app = FastAPI()

# Initialize services with error handling
try:
    voice_service = VoiceService()
    logger.info("Voice service initialized successfully")
except Exception as e:
    logger.warning(f"Voice service initialization failed: {e}")
    voice_service = None

try:
    avatar_service = AvatarService()
    logger.info("Avatar service initialized successfully")
except Exception as e:
    logger.warning(f"Avatar service initialization failed: {e}")
    avatar_service = None

try:
    vision_service = VisionService()
    logger.info("Vision service initialized successfully")
except Exception as e:
    logger.warning(f"Vision service initialization failed: {e}")
    vision_service = None

# Loosen CORS for local development including IDE/browser preview proxies
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all for local dev and preview proxies
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_data: Dict[str, Any] = {}
sessions: Dict[str, Any] = {}  # New session storage for comprehensive tracking

# Token tracking for AI usage
class TokenTracker:
    """Tracks Gemini API token usage globally and per session."""
    
    def __init__(self):
        self.global_input_tokens = 0
        self.global_output_tokens = 0
        self.global_total_tokens = 0
        self.api_calls = 0
        self.session_tokens: Dict[str, Dict[str, int]] = {}
    
    def track(self, response, session_id: str = None) -> Dict[str, int]:
        """Extract token usage from a Gemini response and track it."""
        usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        
        try:
            # Gemini API returns usage_metadata with token counts
            if hasattr(response, 'usage_metadata'):
                metadata = response.usage_metadata
                usage["input_tokens"] = getattr(metadata, 'prompt_token_count', 0) or 0
                usage["output_tokens"] = getattr(metadata, 'candidates_token_count', 0) or 0
                usage["total_tokens"] = getattr(metadata, 'total_token_count', 0) or 0
                
                # Update global counts
                self.global_input_tokens += usage["input_tokens"]
                self.global_output_tokens += usage["output_tokens"]
                self.global_total_tokens += usage["total_tokens"]
                self.api_calls += 1
                
                # Update session-specific counts
                if session_id:
                    if session_id not in self.session_tokens:
                        self.session_tokens[session_id] = {
                            "input_tokens": 0, "output_tokens": 0, 
                            "total_tokens": 0, "api_calls": 0
                        }
                    self.session_tokens[session_id]["input_tokens"] += usage["input_tokens"]
                    self.session_tokens[session_id]["output_tokens"] += usage["output_tokens"]
                    self.session_tokens[session_id]["total_tokens"] += usage["total_tokens"]
                    self.session_tokens[session_id]["api_calls"] += 1
                
                logger.debug(f"Token usage: {usage}")
        except Exception as e:
            logger.warning(f"Failed to extract token usage: {e}")
        
        return usage
    
    def get_global_stats(self) -> Dict[str, int]:
        """Get global token usage statistics."""
        return {
            "input_tokens": self.global_input_tokens,
            "output_tokens": self.global_output_tokens,
            "total_tokens": self.global_total_tokens,
            "api_calls": self.api_calls
        }
    
    def get_session_stats(self, session_id: str) -> Dict[str, int]:
        """Get token usage for a specific session."""
        return self.session_tokens.get(session_id, {
            "input_tokens": 0, "output_tokens": 0, 
            "total_tokens": 0, "api_calls": 0
        })

# Global token tracker instance
token_tracker = TokenTracker()

# Ensure static directories exist and mount static files for serving generated avatar videos
BASE_DIR = os.path.dirname(__file__)
STATIC_DIR = os.path.join(BASE_DIR, "static")
STATIC_OUTPUT_DIR = os.path.join(STATIC_DIR, "output")
os.makedirs(STATIC_OUTPUT_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

class InterviewAnswer(BaseModel):
    sessionId: str
    userAnswer: str

# Pydantic models for different response types
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
    
# Pydantic models for feedback
class FeedbackResponse(BaseModel):
    score: int
    strengths: List[str]
    weaknesses: List[str]
    feedback_text: str

# Pydantic models for Soft Skills Feedback
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

class HintRequest(BaseModel):
    sessionId: str
    currentAnswer: str = Field(default="", description="User's current partial answer")

class HintResponse(BaseModel):
    hint: str
    hint_type: str = Field(default="guidance", description="Type: guidance, example, or clarification")

# Pydantic models for avatar generation
class GenerateAvatarRequest(BaseModel):
    text: str
    voice: str = Field(default="en_male")
    emotion: str = Field(default="neutral")

class GenerateAvatarResponse(BaseModel):
    video_url: str

# Models for plan preview
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

# New Pydantic model for TTS request (used by ElevenLabs VoiceService)
class TTSRequest(BaseModel):
    text: str
    voice: str = "rachel"

# Pydantic model for ATS Review
class ATSReviewResponse(BaseModel):
    ats_score: int
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    keyword_match_percentage: int
    overall_feedback: str

# Pydantic model for Interview Summary
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

class ResumeParserService:
    @staticmethod
    def extract_text_from_pdf(file_path):
        text = ""
        with open(file_path, "rb") as file:
            reader = PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() or ""
        return text

    @staticmethod
    def extract_text_from_docx(file_path):
        doc = docx.Document(file_path)
        text = [paragraph.text for paragraph in doc.paragraphs]
        return "\n".join(text)

# =============================
# User Authentication & Sync
# =============================

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

# In-memory user store (will be replaced with PostgreSQL in production)
users_store: Dict[str, Dict[str, Any]] = {}

# Trial period duration (20 days)
TRIAL_DAYS = 20

def calculate_trial_status(created_at: str) -> Dict[str, Any]:
    """Calculate trial status based on account creation date."""
    from datetime import timedelta
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

@app.post("/api/auth/sync-user", response_model=UserSyncResponse)
async def sync_user(request: UserSyncRequest):
    """
    Sync user from NextAuth OAuth to backend database.
    Called automatically when a user signs in via Google OAuth.
    New users get a 20-day free trial.
    """
    try:
        # Check if user already exists
        user_id = None
        for uid, user in users_store.items():
            if user["email"] == request.email:
                # Update existing user
                user["name"] = request.name or user["name"]
                user["image"] = request.image or user["image"]
                user["provider_id"] = request.provider_id or user["provider_id"]
                user["updated_at"] = datetime.utcnow().isoformat()
                user_id = uid
                logger.info(f"Updated existing user: {request.email}")
                return UserSyncResponse(
                    success=True,
                    user_id=uid,
                    message="User updated successfully"
                )
        
        # Create new user with 20-day trial
        import uuid
        from datetime import timedelta
        
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
            "subscription_status": "trial",  # trial, active, expired
            "interview_sessions": []
        }
        
        logger.info(f"Created new user: {request.email} with ID: {user_id} (20-day trial started)")
        return UserSyncResponse(
            success=True,
            user_id=user_id,
            message="User created successfully with 20-day free trial"
        )
        
    except Exception as e:
        logger.error(f"Error syncing user: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to sync user: {str(e)}")

@app.get("/api/auth/user/{email}")
async def get_user_by_email(email: str):
    """
    Get user profile by email with trial status.
    """
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

@app.get("/api/auth/trial-status/{email}")
async def get_trial_status(email: str):
    """
    Get trial status for a user.
    """
    for uid, user in users_store.items():
        if user["email"] == email:
            trial_status = calculate_trial_status(user.get("created_at", datetime.utcnow().isoformat()))
            return {
                "email": email,
                "subscription_status": user.get("subscription_status", "trial"),
                **trial_status
            }
    raise HTTPException(status_code=404, detail="User not found")

@app.get("/api/auth/me")
async def get_current_user_placeholder():
    """
    Placeholder endpoint for getting current user.
    In production, this would validate JWT token from NextAuth.
    """
    return {"message": "Use NextAuth session on frontend to get current user"}

# =============================
# Avatar video generation route
# =============================
@app.post("/generate_avatar", response_model=GenerateAvatarResponse)
async def generate_avatar(req: GenerateAvatarRequest):
    try:
        out_path = avatar_service.generate_video(req.text, voice=req.voice, emotion=req.emotion)
        if not out_path:
            raise HTTPException(status_code=500, detail="Avatar generation failed.")

        # Ensure the output is under STATIC_OUTPUT_DIR
        # Build a URL path relative to /static
        rel_path = os.path.relpath(out_path, STATIC_DIR)
        video_url = f"/static/{rel_path.replace(os.sep, '/')}"
        return GenerateAvatarResponse(video_url=video_url)
    except HTTPException:
        raise
    except Exception as e:
        print(f"/generate_avatar error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error generating avatar")

class GeminiService:
    @staticmethod
    async def extract_candidate_profile(resume_text: str | None, job_description: str | None) -> Dict[str, Any]:
        """
        Deprecated in current flow: We now strictly use user-provided role, years_of_experience, and company.
        Kept for backward compatibility; returns empty inference.
        """
        return {"role": "", "years_of_experience": 0, "company_name": ""}

    @staticmethod
    async def generate_interview_plan(company_name: str, job_role: str, years_of_experience: int) -> tuple[List[Dict[str, Any]], bool, str]:
        try:
            import uuid
            nonce = uuid.uuid4().hex[:8]
            prompt = f"""
            As an expert interviewer up-to-date with current hiring trends, propose a realistic interview plan for a {job_role} at {company_name}.
            Candidate experience level: {years_of_experience} years.

            IMPORTANT: Real companies typically have 6-8 rounds for senior roles, 4-6 for mid-level, and 3-5 for junior roles.

            Make the plan reflect typical practices for the specific company:
            - Amazon: Leadership Principles behavioral (2-3 rounds), multiple coding rounds (2-3), system design (>=5 YOE), bar raiser round
            - Google: Phone screen, multiple coding rounds (3-4), system design (>=4 YOE), behavioral/googliness, hiring committee
            - Microsoft: Phone screen, coding rounds (2-3), system design, behavioral, as-appropriate round
            - Meta: Phone screen, coding rounds (2-3), system design (>=3 YOE), behavioral, final round
            - Startups: Culture fit, coding rounds (1-2), technical discussion, founder/team round

            Experience-based guidelines:
            - Junior (0-2 YOE): 3-5 rounds, focus on coding fundamentals, MCQs, basic behavioral
            - Mid-level (3-5 YOE): 5-6 rounds, coding + some design, behavioral leadership
            - Senior (6+ YOE): 6-8 rounds, multiple coding, system design, leadership behavioral, bar raiser

            Return ONLY a valid JSON array of objects. Each object MUST have keys:
            - "title": string, name of the round
            - "type": string, one of ["behavioral", "technical", "dsa", "mcq"]
            - "question_count": integer, number of questions in this round
            - "estimated_minutes": integer, estimated minutes for the round

            Ensure variety across calls and realistic round counts. Randomization hint: {nonce}
            """
            
            # Try with simpler prompt first to avoid quota issues
            simple_prompt = f"""Create an interview plan for {job_role} at {company_name} with {years_of_experience} years experience.

Guidelines:
- Senior (6+ YOE): 6-8 rounds
- Mid-level (3-5 YOE): 5-6 rounds  
- Junior (0-2 YOE): 3-5 rounds

Return ONLY a JSON array in this format:
[
  {{"title": "Round Name", "type": "behavioral", "question_count": 2, "estimated_minutes": 30}},
  {{"title": "Coding Round", "type": "dsa", "question_count": 2, "estimated_minutes": 45}}
]

Types: behavioral, technical, dsa, mcq
Vary rounds based on company culture. Token: {nonce}"""
            
            response = model.generate_content(
                simple_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=2000
                )
            )
            token_tracker.track(response)  # Track token usage
            raw = (response.text or "").strip()
            # Extract JSON array from response
            start = raw.find('[')
            end = raw.rfind(']') + 1
            if start >= 0 and end > start:
                json_str = raw[start:end]
                plan = json.loads(json_str)
            else:
                raise ValueError("No JSON array found in response")
            
            # Validate and normalize the plan
            for r in plan:
                # Normalize type field to expected values
                raw_type = (r.get("type") or "").lower()
                if "system" in raw_type or "design" in raw_type:
                    r["type"] = "technical"
                elif "dsa" in raw_type or "coding" in raw_type or "algorithm" in raw_type:
                    r["type"] = "dsa"
                elif "mcq" in raw_type or "assessment" in raw_type:
                    r["type"] = "mcq"
                elif "|" in raw_type:  # Handle mixed types like "behavioral|technical"
                    r["type"] = "behavioral"  # Default to behavioral for mixed
                elif raw_type in ["behavioral", "technical", "dsa", "mcq"]:
                    r["type"] = raw_type
                else:
                    r["type"] = "behavioral"  # Default fallback
                
                # Ensure estimated_minutes is present and valid
                if "estimated_minutes" not in r or not isinstance(r.get("estimated_minutes"), int):
                    q = int(r.get("question_count", 1) or 1)
                    t = r["type"]
                    if t in ["technical", "dsa"]:
                        r["estimated_minutes"] = max(20, q * 25)
                    elif t == "mcq":
                        r["estimated_minutes"] = max(10, q * 2)
                    else:  # behavioral/other
                        r["estimated_minutes"] = max(10, q * 8)
            return plan, True, f"AI-generated plan using Gemini for {company_name} {job_role} with {years_of_experience} years experience"
        except Exception as e:
            print(f"Error generating interview plan: {e}")
            # Check if it's a quota error and wait briefly
            if "quota" in str(e).lower() or "429" in str(e):
                print("Quota exceeded - using enhanced fallback plan")
            
            # Enhanced realistic fallback with some randomization
            import random
            import time
            random.seed(int(time.time()) % 1000)  # Add some time-based randomization
            
            base: List[Dict[str, Any]] = []
            if years_of_experience >= 6:
                if company_name.lower().startswith("amazon"):
                    # Amazon-specific with variations
                    variations = [
                        [
                            {"title": "Phone Screen", "type": "behavioral", "question_count": 2, "estimated_minutes": 30},
                            {"title": "Leadership Principles Deep Dive", "type": "behavioral", "question_count": 3, "estimated_minutes": 45},
                            {"title": "Coding Round 1 - Algorithms", "type": "dsa", "question_count": 2, "estimated_minutes": 45},
                            {"title": "Coding Round 2 - Data Structures", "type": "dsa", "question_count": 2, "estimated_minutes": 45},
                            {"title": "System Design", "type": "technical", "question_count": 1, "estimated_minutes": 60},
                            {"title": "Bar Raiser Interview", "type": "behavioral", "question_count": 2, "estimated_minutes": 30},
                        ],
                        [
                            {"title": "Recruiter Screen", "type": "behavioral", "question_count": 1, "estimated_minutes": 20},
                            {"title": "Online Assessment", "type": "mcq", "question_count": 20, "estimated_minutes": 30},
                            {"title": "Technical Phone Screen", "type": "dsa", "question_count": 1, "estimated_minutes": 45},
                            {"title": "Onsite - Leadership Principles", "type": "behavioral", "question_count": 3, "estimated_minutes": 45},
                            {"title": "Onsite - Coding Interview", "type": "dsa", "question_count": 2, "estimated_minutes": 45},
                            {"title": "Onsite - System Design", "type": "technical", "question_count": 1, "estimated_minutes": 60},
                            {"title": "Bar Raiser Round", "type": "behavioral", "question_count": 2, "estimated_minutes": 30},
                        ]
                    ]
                    base = random.choice(variations)
                elif company_name.lower().startswith("google"):
                    variations = [
                        [
                            {"title": "Phone Screen", "type": "dsa", "question_count": 1, "estimated_minutes": 45},
                            {"title": "Coding Round 1", "type": "dsa", "question_count": 2, "estimated_minutes": 45},
                            {"title": "Coding Round 2", "type": "dsa", "question_count": 2, "estimated_minutes": 45},
                            {"title": "Coding Round 3", "type": "dsa", "question_count": 2, "estimated_minutes": 45},
                            {"title": "System Design", "type": "technical", "question_count": 1, "estimated_minutes": 60},
                            {"title": "Googliness & Leadership", "type": "behavioral", "question_count": 3, "estimated_minutes": 30},
                        ],
                        [
                            {"title": "Technical Phone Screen", "type": "dsa", "question_count": 1, "estimated_minutes": 45},
                            {"title": "Virtual Onsite - Coding 1", "type": "dsa", "question_count": 2, "estimated_minutes": 45},
                            {"title": "Virtual Onsite - Coding 2", "type": "dsa", "question_count": 2, "estimated_minutes": 45},
                            {"title": "Virtual Onsite - System Design", "type": "technical", "question_count": 1, "estimated_minutes": 60},
                            {"title": "Virtual Onsite - Behavioral", "type": "behavioral", "question_count": 2, "estimated_minutes": 30},
                            {"title": "Hiring Committee Review", "type": "behavioral", "question_count": 1, "estimated_minutes": 15},
                        ]
                    ]
                    base = random.choice(variations)
                else:
                    # Generic senior plan with variations
                    base = [
                        {"title": "Initial Screen", "type": "behavioral", "question_count": 2, "estimated_minutes": 30},
                        {"title": "Technical Assessment", "type": "dsa", "question_count": 2, "estimated_minutes": 45},
                        {"title": "Advanced Coding", "type": "dsa", "question_count": 2, "estimated_minutes": 45},
                        {"title": "System Design", "type": "technical", "question_count": 1, "estimated_minutes": 60},
                        {"title": "Leadership & Culture", "type": "behavioral", "question_count": 2, "estimated_minutes": 30},
                        {"title": "Final Interview", "type": "behavioral", "question_count": random.choice([1, 2]), "estimated_minutes": random.choice([20, 30])},
                    ]
            elif years_of_experience >= 3:
                base = [
                    {"title": "Phone Screen", "type": "behavioral", "question_count": 2, "estimated_minutes": 30},
                    {"title": "Coding Challenge", "type": "dsa", "question_count": 2, "estimated_minutes": 45},
                    {"title": "Technical Interview", "type": "dsa", "question_count": 2, "estimated_minutes": 45},
                    {"title": "System Design Discussion", "type": "technical", "question_count": 1, "estimated_minutes": random.choice([40, 45, 50])},
                    {"title": "Team Fit Interview", "type": "behavioral", "question_count": 2, "estimated_minutes": 30},
                ]
            else:
                base = [
                    {"title": "Recruiter Call", "type": "behavioral", "question_count": 1, "estimated_minutes": 20},
                    {"title": "Online Assessment", "type": "mcq", "question_count": random.choice([20, 25, 30]), "estimated_minutes": random.choice([40, 45, 50])},
                    {"title": "Coding Interview", "type": "dsa", "question_count": random.choice([1, 2]), "estimated_minutes": random.choice([45, 60])},
                    {"title": "Technical Discussion", "type": "technical", "question_count": 1, "estimated_minutes": 45},
                ]
            return base, False, f"Enhanced fallback plan for {company_name} {job_role} ({years_of_experience} YOE) - AI temporarily unavailable"

    @staticmethod
    async def generate_question(job_role: str, years_of_experience: int, company_name: str, round_title: str) -> QuestionResponse:
        try:
            import uuid
            import time
            # Use timestamp + uuid for better uniqueness
            nonce = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
            
            prompt = f"""
            You are conducting a '{round_title}' interview for {job_role} at {company_name} ({years_of_experience} YOE).
            
            Create ONE unique behavioral question. Company focus:
            - Amazon: Leadership Principles (Ownership, Customer Obsession, Dive Deep, etc.)
            - Google: Collaboration, innovation, problem-solving, Googleyness
            - Microsoft: Growth mindset, inclusive leadership, customer focus
            - Meta: Move fast, be bold, build for impact
            
            Experience level:
            - Junior (0-2): Learning, feedback, basic teamwork
            - Mid (3-5): Leadership, mentoring, technical decisions  
            - Senior (6+): Strategy, cross-team impact, driving results
            
            Make it specific and unique. Avoid generic questions. Token: {nonce}
            Return only the question text.
            """
            
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.95,  # Higher temperature for more variety
                    max_output_tokens=150
                )
            )
            token_tracker.track(response)  # Track token usage
            
            question_text = response.text.strip().replace('```', '').replace('"', '').strip()
            return QuestionResponse(question=question_text, type="behavioral")
        except Exception as e:
            print(f"Error generating question: {e}")
            # More varied fallback questions based on company/level
            fallback_sets = {
                "amazon": [
                    "Tell me about a time you had to dive deep into a problem to find the root cause.",
                    "Describe a situation where you had to be right, a lot, despite initial disagreement.",
                    "Give me an example of when you took ownership of a problem that wasn't originally yours.",
                    "Tell me about a time you had to invent and simplify a complex process."
                ],
                "google": [
                    "Describe a time you collaborated with a team to solve a complex technical problem.",
                    "Tell me about a project where you had to think outside the box.",
                    "Give me an example of when you had to learn something completely new to accomplish a goal.",
                    "Describe a time you had to make a decision with ambiguous requirements."
                ],
                "default": [
                    "Tell me about a challenging project you led and how you ensured its success.",
                    "Describe a time you had to influence stakeholders without direct authority.",
                    "Give me an example of when you had to adapt quickly to changing priorities.",
                    "Tell me about a time you received difficult feedback and how you handled it."
                ]
            }
            
            import random
            company_key = "amazon" if "amazon" in company_name.lower() else "google" if "google" in company_name.lower() else "default"
            return QuestionResponse(question=random.choice(fallback_sets[company_key]), type="behavioral")

    @staticmethod
    async def generate_coding_question(job_role: str, years_of_experience: int, company_name: str, round_title: str) -> CodingQuestionResponse:
        try:
            import uuid
            import time
            nonce = f"{int(time.time())}-{uuid.uuid4().hex[:6]}"
            
            prompt = f"""
            Create a unique coding problem for {job_role} at {company_name} ({years_of_experience} YOE).
            
            Difficulty by experience:
            - Junior (0-2): Arrays, strings, basic loops
            - Mid (3-5): Trees, graphs, dynamic programming
            - Senior (6+): Complex algorithms, optimization, system design coding
            
            Company style:
            - Amazon: Scalability, optimization focus
            - Google: Mathematical elegance, clean solutions
            - Microsoft: Practical, real-world problems
            - Meta: Performance, user experience focus
            
            Return JSON: {{"question": "problem description", "initial_code": "def function_name():\\n    pass"}}
            Make it unique and specific. Token: {nonce}
            """
            
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.9,  # Higher for more variety
                    max_output_tokens=300
                )
            )
            token_tracker.track(response)  # Track token usage
            raw = response.text.strip()
            # Extract JSON from response
            start = raw.find('{')
            end = raw.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = raw[start:end]
                result = json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
            return CodingQuestionResponse(question=result["question"], initial_code=result["initial_code"], type="technical")
        except Exception as e:
            print(f"Error generating coding question: {e}")
            # More varied fallback problems by company/level
            problem_sets = {
                "junior": [
                    {"question": "Find the first non-repeating character in a string.", "initial_code": "def first_unique_char(s):\n    # Your solution here\n    pass"},
                    {"question": "Check if two strings are anagrams of each other.", "initial_code": "def is_anagram(s1, s2):\n    # Your solution here\n    pass"},
                    {"question": "Find the maximum element in a rotated sorted array.", "initial_code": "def find_max(nums):\n    # Your solution here\n    pass"}
                ],
                "mid": [
                    {"question": "Implement a function to serialize and deserialize a binary tree.", "initial_code": "def serialize(root):\n    # Your solution here\n    pass\n\ndef deserialize(data):\n    # Your solution here\n    pass"},
                    {"question": "Find the longest increasing subsequence in an array.", "initial_code": "def longest_increasing_subsequence(nums):\n    # Your solution here\n    pass"},
                    {"question": "Design a data structure that supports insert, delete, and getRandom in O(1).", "initial_code": "class RandomizedSet:\n    def __init__(self):\n        # Your implementation here\n        pass"}
                ],
                "senior": [
                    {"question": "Design a distributed cache system with LRU eviction policy.", "initial_code": "class DistributedLRUCache:\n    def __init__(self, capacity):\n        # Your implementation here\n        pass"},
                    {"question": "Implement a rate limiter that can handle millions of requests per second.", "initial_code": "class RateLimiter:\n    def __init__(self, max_requests, time_window):\n        # Your implementation here\n        pass"},
                    {"question": "Design an algorithm to find the shortest path in a weighted graph with negative edges.", "initial_code": "def shortest_path_negative_edges(graph, start, end):\n    # Your solution here\n    pass"}
                ]
            }
            
            import random
            level = "junior" if years_of_experience <= 2 else "senior" if years_of_experience >= 6 else "mid"
            selected = random.choice(problem_sets[level])
            return CodingQuestionResponse(
                question=selected["question"],
                initial_code=selected["initial_code"],
                type="technical"
            )

    @staticmethod
    async def generate_mcq_questions(job_role: str) -> MCQQuestionResponse:
        try:
            prompt = f"""
            Generate a single, varied multiple-choice question for a {job_role} role. The question should have exactly four options (A, B, C, D) and a single correct answer.
            Ensure the question is not repeated across calls for identical inputs.
            Return the response as a valid JSON object with the following keys: "question", "options" (an array of strings), and "correct_answer" (a string corresponding to one of the options).
            Do not include any other text or explanation.

            Example JSON:
            {
{
              "question": "What is a closure in Python?",
              "options": ["A: A function that returns a dictionary.", "B: A function that remembers the values from its enclosing scope even if the scope is no longer active.", "C: A type of data structure.", "D: A form of object-oriented programming."],
              "correct_answer": "B: A function that remembers the values from its enclosing scope even if the scope is no longer active."
            }}
            """
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7
                )
            )
            raw = response.text.strip()
            # Extract JSON from response
            start = raw.find('{')
            end = raw.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = raw[start:end]
                result = json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
            return MCQQuestionResponse(
                question=result["question"],
                options=result["options"],
                correct_answer=result["correct_answer"],
                type="mcq"
            )
        except Exception as e:
            print(f"Error generating MCQ: {e}")
            return MCQQuestionResponse(
                question="Which of the following is not a programming language?",
                options=["A: Python", "B: JavaScript", "C: HTML", "D: C++"],
                correct_answer="C: HTML",
                type="mcq"
            )
    
    # Removed Gemini TTS/STT helpers; ElevenLabs VoiceService is used instead.
    
    @staticmethod
    async def review_resume_ats(resume_text: str, job_description: str) -> ATSReviewResponse:
        """
        Analyzes resume against job description and provides ATS score and feedback.
        """
        try:
            prompt = f"""Analyze this resume for ATS compatibility and job fit.

RESUME:
{resume_text[:3000]}

JOB DESCRIPTION:
{job_description[:2000]}

Provide detailed analysis in this JSON format:
{{
  "ats_score": 85,
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "weaknesses": ["weakness 1", "weakness 2"],
  "recommendations": ["recommendation 1", "recommendation 2", "recommendation 3"],
  "keyword_match_percentage": 75,
  "overall_feedback": "2-3 sentences of constructive feedback"
}}

Focus on:
- Keyword matching
- Skills alignment  
- Experience relevance
- ATS-friendly formatting
- Missing requirements"""
            
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=1000
                )
            )
            
            if not response.text:
                raise ValueError("Empty response from model")
            
            # Extract JSON from response robustly (handles code fences and prose)
            raw = response.text.strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                first_nl = raw.find("\n")
                if first_nl != -1:
                    raw = raw[first_nl + 1:]
                if raw.endswith("```"):
                    raw = raw[:-3]
            raw = raw.strip()
            
            # Find first JSON object
            start = raw.find('{')
            end = raw.rfind('}') + 1
            if start < 0 or end <= start:
                raise ValueError("No JSON found in response")
            json_str = raw[start:end]
            result = json.loads(json_str)
            
            return ATSReviewResponse(
                ats_score=result.get("ats_score", 60),
                strengths=result.get("strengths", ["Resume uploaded successfully"]),
                weaknesses=result.get("weaknesses", ["Could be more specific"]),
                recommendations=result.get("recommendations", ["Tailor resume to job description"]),
                keyword_match_percentage=result.get("keyword_match_percentage", 50),
                overall_feedback=result.get("overall_feedback", "Resume needs improvement for better ATS compatibility.")
            )
        except Exception as e:
            logger.error(f"Error in ATS review: {e}")
            # Fallback response
            return ATSReviewResponse(
                ats_score=65,
                strengths=["Resume format is readable", "Contains relevant experience"],
                weaknesses=["Could include more keywords from job description", "May need better formatting"],
                recommendations=["Add more specific skills mentioned in job posting", "Use bullet points for better readability"],
                keyword_match_percentage=45,
                overall_feedback="Unable to perform detailed ATS analysis. Consider reviewing your resume against the job requirements and adding relevant keywords."
            )

    @staticmethod
    async def generate_interview_summary(session_data: dict, company_name: str, job_role: str) -> InterviewSummaryResponse:
        """
        Generates a comprehensive interview summary with overall feedback and recommendations.
        """
        try:
            # Extract data from session
            questions_and_answers = session_data.get("questions_and_answers", [])
            total_questions = len(questions_and_answers)
            
            # Calculate overall score
            scores = [qa.get("score", 0) for qa in questions_and_answers if qa.get("score")]
            overall_score = sum(scores) / len(scores) if scores else 0
            
            # Group by rounds
            rounds = {}
            for qa in questions_and_answers:
                round_title = qa.get("round_title", "General")
                if round_title not in rounds:
                    rounds[round_title] = []
                rounds[round_title].append(qa)
            
            round_summaries = []
            for round_title, round_qas in rounds.items():
                round_scores = [qa.get("score", 0) for qa in round_qas if qa.get("score")]
                round_avg = sum(round_scores) / len(round_scores) if round_scores else 0
                round_summaries.append({
                    "round_title": round_title,
                    "questions_count": len(round_qas),
                    "average_score": round_avg,
                    "question_types": list(set(qa.get("type", "unknown") for qa in round_qas))
                })
            
            # Prepare context for AI summary
            context = f"""
            Interview Summary for {job_role} at {company_name}:
            - Total Questions: {total_questions}
            - Overall Score: {overall_score:.1f}/10
            - Rounds: {len(rounds)}
            
            Round Performance:
            {chr(10).join([f"- {r['round_title']}: {r['average_score']:.1f}/10 ({r['questions_count']} questions)" for r in round_summaries])}
            
            Sample Q&As:
            {chr(10).join([f"Q: {qa.get('question', '')[:100]}... A: {qa.get('answer', '')[:100]}... Score: {qa.get('score', 0)}/10" for qa in questions_and_answers[:3]])}
            """
            
            prompt = f"""
            Generate a comprehensive interview summary based on this performance data:
            
            {context}
            
            Provide analysis in JSON format:
            {{
                "strengths": ["strength1", "strength2", "strength3"],
                "areas_for_improvement": ["area1", "area2", "area3"],
                "recommendations": ["recommendation1", "recommendation2", "recommendation3"],
                "overall_feedback": "detailed overall feedback paragraph"
            }}
            
            Focus on:
            - Technical competency demonstrated
            - Communication skills
            - Problem-solving approach
            - Areas that need development
            - Specific actionable recommendations
            """
            
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=600
                )
            )
            
            raw = response.text.strip()
            # Extract JSON from response
            start = raw.find('{')
            end = raw.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = raw[start:end]
                result = json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
            
            return InterviewSummaryResponse(
                session_id=session_data.get("session_id", ""),
                total_questions=total_questions,
                total_rounds=len(rounds),
                overall_score=overall_score,
                time_taken_minutes=session_data.get("duration_minutes", 0),
                round_summaries=round_summaries,
                strengths=result.get("strengths", ["Completed the interview", "Showed engagement"]),
                areas_for_improvement=result.get("areas_for_improvement", ["Practice more technical questions"]),
                recommendations=result.get("recommendations", ["Continue practicing", "Review fundamentals"]),
                overall_feedback=result.get("overall_feedback", "Good effort in completing the interview. Keep practicing to improve your skills.")
            )
        except Exception as e:
            print(f"Error generating interview summary: {e}")
            # Fallback summary
            return InterviewSummaryResponse(
                session_id=session_data.get("session_id", ""),
                total_questions=len(session_data.get("questions_and_answers", [])),
                total_rounds=len(set(qa.get("round_title", "General") for qa in session_data.get("questions_and_answers", []))),
                overall_score=5.0,
                time_taken_minutes=session_data.get("duration_minutes", 0),
                round_summaries=[],
                strengths=["Completed the interview", "Showed engagement"],
                areas_for_improvement=["Practice more questions", "Improve technical skills"],
                recommendations=["Continue practicing", "Review core concepts", "Work on communication"],
                overall_feedback="Thank you for completing the interview. Keep practicing to improve your skills and confidence."
            )

    @staticmethod
    async def get_feedback_and_score(question: str, userAnswer: str, company_name: str, job_role: str, extracted_resume_text: str | None = None) -> FeedbackResponse:
        """
        Generates feedback and a score for the user's answer, considering the resume.
        """
        try:
            prompt = f"""Evaluate this interview answer for a {job_role} position.

Question: {question}

Candidate's Answer: {userAnswer}

Provide your evaluation in this exact JSON format:
{{
  "score": 7,
  "strengths": ["strength point 1", "strength point 2"],
  "weaknesses": ["area for improvement 1"],
  "feedback_text": "Overall constructive feedback in 2-3 sentences"
}}

Rate from 1-10. Be constructive and specific."""
            
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.5,
                    max_output_tokens=600
                )
            )
            
            if not response.text:
                raise ValueError("Empty response from model")
            
            # Extract JSON from response
            raw = response.text.strip()
            # Find JSON object in the response
            start = raw.find('{')
            end = raw.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = raw[start:end]
                result = json.loads(json_str)
                return FeedbackResponse(
                    score=result.get("score", 6),
                    strengths=result.get("strengths", ["Good attempt"]),
                    weaknesses=result.get("weaknesses", ["Could be more specific"]),
                    feedback_text=f"🤖 AI Feedback: {result.get('feedback_text', 'Keep practicing!')}"
                )
            else:
                raise ValueError("No JSON found in response")
        except Exception as e:
            print(f"Error generating feedback: {e}")
            # Better fallback feedback based on answer length and content
            score = 7 if len(userAnswer) > 100 else 5
            has_example = any(word in userAnswer.lower() for word in ["when", "time", "example", "situation"])
            has_result = any(word in userAnswer.lower() for word in ["result", "outcome", "improved", "increased", "decreased"])
            
            strengths = []
            weaknesses = []
            
            if has_example:
                strengths.append("Provided a specific example")
            if has_result:
                strengths.append("Mentioned concrete results")
            if len(userAnswer) > 150:
                strengths.append("Detailed response")
            
            if not has_example:
                weaknesses.append("Could include a more specific example")
            if not has_result:
                weaknesses.append("Could quantify the impact or results")
            if len(userAnswer) < 50:
                weaknesses.append("Could provide more detail")
            
            return FeedbackResponse(
                score=score,
                strengths=strengths if strengths else ["Good effort"],
                weaknesses=weaknesses if weaknesses else ["Consider using the STAR method"],
                feedback_text=f"📋 Smart Analysis: Your answer shows understanding. {'Great use of specific examples!' if has_example else 'Try to include specific examples next time.'}"
            )

    @staticmethod
    async def generate_soft_skills_feedback(
        user_answer: str, 
        question: str,
        round_title: str,
        behavior_data: Optional[Dict[str, Any]] = None,
        opensmile_features: Optional[Dict[str, Any]] = None
    ) -> SoftSkillsFeedback:
        """
        Generates soft skills feedback based on the user's answer, behavior, and voice features.
        
        Args:
            user_answer: The text of the user's response
            question: The question being asked
            round_title: Current round (HR, Technical, etc.)
            behavior_data: Data from BehaviorMonitor (posture, eye contact, etc.)
            opensmile_features: Voice features from openSMILE analysis
        
        Returns:
            SoftSkillsFeedback with 5 key metrics and optional detailed breakdown
        """
        try:
            # Build context for AI analysis
            context_parts = []
            
            # Add voice features context if available
            voice_context = ""
            voice_metrics = {}
            if opensmile_features:
                derived = opensmile_features.get("derived_scores", {})
                voice_context = f"""
Voice Analysis (from openSMILE):
- Tone Score: {derived.get('tone', 'N/A')}/5
- Confidence Score: {derived.get('confidence', 'N/A')}/5
- Pace Score: {derived.get('pace', 'N/A')}/5
- Pitch variance: {opensmile_features.get('pitch', {}).get('variance', 'N/A')}
- Pause ratio: {opensmile_features.get('temporal', {}).get('pause_ratio', 'N/A')}
"""
                voice_metrics = {
                    "tone": derived.get("tone", 3.0),
                    "confidence": derived.get("confidence", 3.0),
                    "pace": derived.get("pace", 3.0)
                }
                context_parts.append(voice_context)
            
            # Add behavior context if available
            behavior_context = ""
            body_language_score = 3.0
            if behavior_data:
                behavior_context = f"""
Behavior Analysis:
- Eye Contact: {behavior_data.get('eye_contact', 'N/A')}
- Confidence Score: {behavior_data.get('confidence_score', 'N/A')}/100
- Posture: {'Good' if behavior_data.get('posture', {}).get('is_good', True) else 'Needs improvement'}
"""
                context_parts.append(behavior_context)
                # Convert confidence score (0-100) to 0-5 scale
                body_language_score = min(5.0, behavior_data.get('confidence_score', 60) / 20)
            
            prompt = f"""Analyze this interview response for SOFT SKILLS only.

Round: {round_title}
Question: {question}

Candidate Response: {user_answer}

{chr(10).join(context_parts)}

Evaluate these 5 dimensions on a 0-5 scale with brief 1-line feedback each:

1. Communication Clarity - How clear, articulate, and well-structured is the response?
2. Voice Quality - Tone, pitch variation, and vocal presence ({"use openSMILE data above" if opensmile_features else "estimate from text style"})
3. Speech Delivery - Pace, use of fillers (um, uh), repetition
4. Body Language - {"use behavior data above" if behavior_data else "cannot assess from text, give neutral 3.0"}
5. Confidence/Presence - Overall confidence, professionalism, executive presence

Return ONLY this JSON:
{{
  "overallScore": 75,
  "metrics": [
    {{"name": "Communication", "score": 4.0, "feedback": "Clear structure with good examples."}},
    {{"name": "Voice", "score": 3.5, "feedback": "Good tone variation.", "source": "openSMILE"}},
    {{"name": "Speech Delivery", "score": 3.0, "feedback": "Moderate pace, few fillers."}},
    {{"name": "Body Language", "score": 3.5, "feedback": "Good posture maintained."}},
    {{"name": "Confidence", "score": 3.8, "feedback": "Speaks with conviction."}}
  ]
}}"""
            
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.4,
                    max_output_tokens=500
                )
            )
            
            if not response.text:
                raise ValueError("Empty response from model")
            
            # Extract JSON from response
            raw = response.text.strip()
            start = raw.find('{')
            end = raw.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = raw[start:end]
                result = json.loads(json_str)
                
                # Build metrics list, enriching with openSMILE data where available
                metrics = []
                for m in result.get("metrics", []):
                    metric_name = m.get("name", "Unknown")
                    # Override voice metrics with openSMILE data if available
                    if metric_name == "Voice" and voice_metrics:
                        m["score"] = round((voice_metrics.get("tone", 3) + voice_metrics.get("confidence", 3)) / 2, 1)
                        m["source"] = "openSMILE"
                    elif metric_name == "Speech Delivery" and voice_metrics:
                        m["score"] = voice_metrics.get("pace", m.get("score", 3.0))
                        m["source"] = "openSMILE"
                    elif metric_name == "Body Language" and behavior_data:
                        m["score"] = round(body_language_score, 1)
                        m["source"] = "behavior_monitor"
                    
                    metrics.append(SoftSkillMetric(
                        name=m.get("name", "Unknown"),
                        score=float(m.get("score", 3.0)),
                        feedback=m.get("feedback", "--"),
                        source=m.get("source", "ai")
                    ))
                
                return SoftSkillsFeedback(
                    overallScore=int(result.get("overallScore", 70)),
                    metrics=metrics,
                    details=None,  # Detailed breakdown can be added later
                    openSmileFeatures=opensmile_features
                )
            else:
                raise ValueError("No JSON found in response")
                
        except Exception as e:
            logger.error(f"Error generating soft skills feedback: {e}")
            # Return fallback soft skills feedback
            return SoftSkillsFeedback(
                overallScore=70,
                metrics=[
                    SoftSkillMetric(name="Communication", score=3.5, feedback="Clear response structure.", source="ai"),
                    SoftSkillMetric(name="Voice", score=3.0, feedback="--", source="ai"),
                    SoftSkillMetric(name="Speech Delivery", score=3.0, feedback="--", source="ai"),
                    SoftSkillMetric(name="Body Language", score=3.0, feedback="--", source="ai"),
                    SoftSkillMetric(name="Confidence", score=3.5, feedback="Shows good engagement.", source="ai")
                ],
                details=None,
                openSmileFeatures=opensmile_features
            )


async def get_next_question_data(session: Dict[str, Any], next_round_info: Dict[str, Any]) -> Union[QuestionResponse, CodingQuestionResponse, MCQQuestionResponse]:
    """Helper function to get the next question based on the round type."""
    if next_round_info["type"] in ["technical", "dsa"]:
        return await GeminiService.generate_coding_question(
            job_role=session["job_role"],
            years_of_experience=session["years_of_experience"],
            company_name=session["company_name"],
            round_title=next_round_info["title"]
        )
    elif next_round_info["type"] == "mcq":
        return await GeminiService.generate_mcq_questions(session["job_role"])
    else:
        return await GeminiService.generate_question(
            job_role=session["job_role"],
            years_of_experience=session["years_of_experience"],
            company_name=session["company_name"],
            round_title=next_round_info["title"]
        )

# New endpoint for parsing the resume
@app.post("/api/parse-resume")
async def parse_resume(file: UploadFile = File(...)):
    file_extension = file.filename.split('.')[-1].lower()
    
    # Save the uploaded file temporarily
    file_path = f"/tmp/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())

    extracted_text = ""
    try:
        if file_extension == 'pdf':
            extracted_text = ResumeParserService.extract_text_from_pdf(file_path)
        elif file_extension == 'docx':
            extracted_text = ResumeParserService.extract_text_from_docx(file_path)
        else:
            raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF or DOCX file.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing file: {e}")
    finally:
        os.remove(file_path) # Clean up temporary file

    # In a real app, you would pass this to an AI to extract skills, etc.
    # For now, we'll return the full text.
    return {"filename": file.filename, "extracted_text": extracted_text}


@app.get("/api/voices")
async def list_voices():
    """Return available ElevenLabs voices (name -> id)."""
    try:
        return voice_service.list_voices()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/current-session")
async def get_current_session():
    """Returns current session if exists, otherwise 404."""
    # For now, return 404 since we don't have persistent session storage
    # In a real app, you'd check session storage/database
    raise HTTPException(status_code=404, detail="No active session")


@app.get("/api/token-stats/{session_id}")
async def get_token_stats(session_id: str):
    """
    Get AI token usage statistics for a session.
    Returns input tokens, output tokens, total tokens, and API call count.
    """
    session_stats = token_tracker.get_session_stats(session_id)
    global_stats = token_tracker.get_global_stats()
    
    return {
        "session": session_stats,
        "global": global_stats,
        "session_id": session_id
    }


@app.get("/api/token-stats")
async def get_global_token_stats():
    """Get global AI token usage statistics across all sessions."""
    return token_tracker.get_global_stats()


@app.get("/api/interview-summary/{session_id}", response_model=InterviewSummaryResponse)
async def get_interview_summary(session_id: str):
    """
    Returns comprehensive interview summary with overall feedback and recommendations.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_data = sessions[session_id]
    
    # Get company and role info
    company_name = session_data.get("company_name", "Unknown Company")
    job_role = session_data.get("job_role", "Unknown Role")
    
    # Generate comprehensive summary
    summary = await GeminiService.generate_interview_summary(session_data, company_name, job_role)
    return summary


@app.post("/api/tts")
async def tts(tts_request: TTSRequest):
    """Convert text to speech using ElevenLabs and return audio/mpeg bytes."""
    if not voice_service:
        raise HTTPException(
            status_code=503,
            detail="Voice service is not available. Please check your configuration."
        )
    
    try:
        audio_data = voice_service.text_to_speech(tts_request.text, tts_request.voice)
        if not audio_data:
            raise HTTPException(
                status_code=503,
                detail="Voice synthesis failed. The service might be unavailable or misconfigured."
            )
        return Response(content=audio_data, media_type="audio/mpeg")
    except HTTPException as http_err:
        # Re-raise HTTP exceptions
        raise http_err
    except Exception as e:
        # For other TTS failures, surface a structured fallback
        return {
            "fallback": "client_tts",
            "reason": "tts_error",
            "message": "Using client-side TTS due to server TTS error",
            "text": tts_request.text,
            "voice": tts_request.voice,
        }


@app.post("/api/ats-review", response_model=ATSReviewResponse)
async def ats_review(
    resumeFile: UploadFile = File(...),
    jobDescription: str = Form(...)
):
    """
    Analyzes resume against job description and provides ATS score and feedback.
    """
    if not jobDescription.strip():
        raise HTTPException(status_code=400, detail="Job description is required for ATS review.")
    
    # Save and extract resume text
    file_extension = resumeFile.filename.split('.')[-1].lower() if resumeFile.filename else ""
    file_path = f"/tmp/{resumeFile.filename}"
    
    try:
        with open(file_path, "wb") as f:
            f.write(await resumeFile.read())

        if file_extension == 'pdf':
            resume_text = ResumeParserService.extract_text_from_pdf(file_path)
        elif file_extension == 'docx':
            resume_text = ResumeParserService.extract_text_from_docx(file_path)
        else:
            raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF or DOCX file.")
        
        if not resume_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from resume. Please check the file.")
        
        # Get ATS analysis
        ats_result = await GeminiService.review_resume_ats(resume_text, jobDescription)
        return ats_result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in ats_review: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing resume: {str(e)}")
    finally:
        # Clean up temporary file
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Warning: Could not delete temporary file {file_path}: {str(e)}")
            pass


@app.post("/api/preview-plan", response_model=PlanPreviewResponse)
async def preview_plan(
    resumeFile: UploadFile | None = File(None),
    jobDescription: str = Form(""),
    yearsOfExperience: int = Form(0),
    jobRole: str = Form(""),
    companyName: str = Form("")
):
    """
    Returns an interview plan preview (rounds with estimated minutes), totals and inferred profile
    without creating a session.
    """
    # Ignore resume and job description; use provided inputs directly
    effective_role = jobRole
    effective_yoe = yearsOfExperience
    effective_company = companyName

    plan, is_ai_generated, generation_source = await GeminiService.generate_interview_plan(effective_company, effective_role, effective_yoe)

    total_questions = sum(int(r.get("question_count", 0) or 0) for r in plan)
    total_estimated_minutes = sum(int(r.get("estimated_minutes", 0) or 0) for r in plan)

    return PlanPreviewResponse(
        inferred_role=effective_role,
        inferred_years_of_experience=effective_yoe,
        inferred_company=effective_company,
        rounds=[PlanItem(**r) for r in plan],
        total_questions=total_questions,
        total_estimated_minutes=total_estimated_minutes,
        is_ai_generated=is_ai_generated,
        generation_source=generation_source,
    )

@app.post("/api/start-interview", response_model=InterviewStartResponse)
async def start_interview(
    resumeFile: UploadFile | None = File(None),
    jobDescription: str = Form(""),
    yearsOfExperience: int = Form(...),
    jobRole: str = Form(...),
    companyName: str = Form(...)
):
    if not all([yearsOfExperience, jobRole, companyName]):
        raise HTTPException(status_code=400, detail="Missing required form data.")
    
    # Do not parse or consider resume or job description; use provided values only
    effective_role = jobRole
    effective_yoe = yearsOfExperience
    effective_company = companyName

    interview_plan, _, _ = await GeminiService.generate_interview_plan(effective_company, effective_role, effective_yoe)
    
    session_id = "mock_" + str(hash(effective_company.lower() + effective_role))[2:]
    
    initial_round = interview_plan[0]
    initial_question_data = await get_next_question_data(
        {"job_role": effective_role, "years_of_experience": effective_yoe, "company_name": effective_company},
        initial_round
    )
    
    # Store interview plan and other details in the session
    sessions[session_id] = {
        "company_name": effective_company,
        "job_role": effective_role,
        "years_of_experience": effective_yoe,
        "extracted_resume_text": "",
        # Keep both legacy and new keys for compatibility
        "current_round": 0,
        "current_question": initial_question_data.question,  # Store actual question text
        "current_question_type": initial_round["type"],  # Store question type
        "interview_plan": interview_plan,
        "current_round_index": 0,
        "current_question_index": 0,
        "interview_history": [],
        "questions_and_answers": [],
        "is_complete": False,
        "start_time": datetime.now(),
        "session_id": session_id
    }
    
    return InterviewStartResponse(
        message="Interview session started successfully.",
        sessionId=session_id,
        questionData=initial_question_data,
        roundTitle=initial_round["title"],
        isComplete=False,
        feedback=None  # No feedback on the first question
    )


@app.post("/api/submit-answer", response_model=InterviewSubmitResponse)
async def submit_answer(answer_data: InterviewAnswer):
    # Check both session storages for compatibility
    session = session_data.get(answer_data.sessionId)
    session_new = sessions.get(answer_data.sessionId)
    
    if not session and not session_new:
        raise HTTPException(status_code=404, detail="Session not found.")
    
    # Use the new sessions storage if available, otherwise fall back to old one
    if session_new:
        session = session_new
    
    interview_plan = session["interview_plan"]
    current_round_index = session["current_round_index"]
    current_question_index = session["current_question_index"]
    
    current_round = interview_plan[current_round_index]
    
    # Get the actual question text from the Gemini Service for the feedback prompt
    question_to_feedback = ""
    if current_round["type"] in ["technical", "dsa"]:
        q_data = await GeminiService.generate_coding_question(
            job_role=session["job_role"],
            years_of_experience=session["years_of_experience"],
            company_name=session["company_name"],
            round_title=current_round["title"]
        )
        question_to_feedback = q_data.question
    elif current_round["type"] == "mcq":
        q_data = await GeminiService.generate_mcq_questions(session["job_role"])
        question_to_feedback = q_data.question
    else:
        q_data = await GeminiService.generate_question(
            job_role=session["job_role"],
            years_of_experience=session["years_of_experience"],
            company_name=session["company_name"],
            round_title=current_round["title"]
        )
        question_to_feedback = q_data.question

    # Generate feedback for the submitted answer
    feedback = await GeminiService.get_feedback_and_score(
        question=question_to_feedback,
        userAnswer=answer_data.userAnswer,
        company_name=session["company_name"],
        job_role=session["job_role"],
        extracted_resume_text=None
    )
    
    # Generate soft skills feedback for this round
    # Get behavior data from session if available
    behavior_data = session.get("latest_behavior_data", None)
    # openSMILE features are automatically extracted and stored when using /api/stt endpoint
    opensmile_features = session.get("latest_opensmile_features", None)
    
    soft_skills = await GeminiService.generate_soft_skills_feedback(
        user_answer=answer_data.userAnswer,
        question=question_to_feedback,
        round_title=current_round["title"],
        behavior_data=behavior_data,
        opensmile_features=opensmile_features
    )

    # Store the user's answer and feedback to the session history
    if "interview_history" in session:
        session["interview_history"].append({
            "question": question_to_feedback,
            "user_answer": answer_data.userAnswer,
            "feedback": feedback.dict(),
            "soft_skills": soft_skills.dict()
        })
    
    # Also store in the new format for comprehensive summary
    if answer_data.sessionId in sessions:
        sessions[answer_data.sessionId]["questions_and_answers"].append({
            "question": question_to_feedback,
            "answer": answer_data.userAnswer,
            "score": feedback.score,
            "round_title": current_round["title"],
            "type": current_round["type"],
            "feedback_text": feedback.feedback_text,
            "strengths": feedback.strengths,
            "weaknesses": feedback.weaknesses,
            "soft_skills": soft_skills.dict()
        })
        
        # Update completion status and duration
        if session.get("is_complete", False):
            start_time = sessions[answer_data.sessionId].get("start_time")
            if start_time:
                duration = (datetime.now() - start_time).total_seconds() / 60
                sessions[answer_data.sessionId]["duration_minutes"] = int(duration)
            sessions[answer_data.sessionId]["is_complete"] = True
    
    if current_question_index + 1 < current_round["question_count"]:
        session["current_question_index"] += 1
        
        next_question_data = await get_next_question_data(session, current_round)
        
        # Update session with new question
        session["current_question"] = next_question_data.question
        session["current_question_type"] = current_round["type"]
        
        return InterviewSubmitResponse(
            questionData=next_question_data,
            roundTitle=current_round["title"],
            isComplete=False,
            feedback=feedback,
            softSkills=soft_skills
        )
    else:
        if current_round_index + 1 < len(interview_plan):
            session["current_round_index"] += 1
            session["current_question_index"] = 0
            
            next_round = interview_plan[session["current_round_index"]]
            next_question_data = await get_next_question_data(session, next_round)
            
            # Update session with new question
            session["current_question"] = next_question_data.question
            session["current_question_type"] = next_round["type"]
            
            return InterviewSubmitResponse(
                questionData=next_question_data,
                roundTitle=next_round["title"],
                isComplete=False,
                feedback=feedback,
                softSkills=soft_skills
            )
        else:
            # Mark interview as complete in new sessions storage
            if answer_data.sessionId in sessions:
                start_time = sessions[answer_data.sessionId].get("start_time")
                if start_time:
                    duration = (datetime.now() - start_time).total_seconds() / 60
                    sessions[answer_data.sessionId]["duration_minutes"] = int(duration)
                sessions[answer_data.sessionId]["is_complete"] = True
            
            return InterviewSubmitResponse(
                questionData=QuestionResponse(question="Congratulations! You have completed the mock interview.", type="complete"),
                roundTitle="Interview Complete",
                isComplete=True,
                feedback=feedback,
                softSkills=soft_skills
            )


# New endpoint for getting hints when stuck
@app.post("/api/get-hint", response_model=HintResponse)
async def get_hint(hint_request: HintRequest):
    """
    Provide a helpful hint to the user when they're stuck on a question.
    Like a real interviewer would do.
    """
    try:
        session_id = hint_request.sessionId
        
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = sessions[session_id]
        current_question = session.get("current_question", "")
        question_type = session.get("current_question_type", "behavioral")
        job_role = session.get("job_role", "")
        current_answer = hint_request.currentAnswer
        
        # Track hint count
        if "hints_used" not in session:
            session["hints_used"] = 0
        session["hints_used"] += 1
        
        # Generate contextual hint based on question type
        hint_prompt = f"""You are a helpful interviewer. The candidate is stuck on this question:

Question: {current_question}
Question Type: {question_type}
Job Role: {job_role}
Current Answer (if any): {current_answer if current_answer else "Not started yet"}

Provide a helpful hint that:
1. Doesn't give away the complete answer
2. Guides them in the right direction
3. Is encouraging and supportive
4. Is specific to their situation

For behavioral questions: Suggest a framework (STAR method) or prompt them to think about specific experiences
For technical questions: Give a small clue about the approach or concept, not the solution
For coding questions: Hint at the algorithm or data structure, not the code

Keep the hint to 2-3 sentences maximum. Be warm and encouraging like a real interviewer.
"""
        
        response = model.generate_content(hint_prompt)
        hint_text = response.text.strip()
        
        # Determine hint type
        hint_type = "guidance"
        if "example" in hint_text.lower() or "for instance" in hint_text.lower():
            hint_type = "example"
        elif "clarif" in hint_text.lower() or "mean" in hint_text.lower():
            hint_type = "clarification"
        
        return HintResponse(hint=hint_text, hint_type=hint_type)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating hint: {e}")
        # Provide a generic helpful hint as fallback
        return HintResponse(
            hint="Take a moment to think about your past experiences. What situation comes to mind? Try using the STAR method: Situation, Task, Action, Result.",
            hint_type="guidance"
        )


# New endpoint for Text-to-Speech
@app.post("/api/tts")
async def text_to_speech(tts_request: TTSRequest):
    try:
        audio_data = await GeminiService.convert_text_to_speech(tts_request.text, tts_request.voice)
        audio_base64 = base64.b64encode(audio_data).decode()
        return {"audio_data": audio_base64}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS error: {e}")

# New endpoint for Speech-to-Text with openSMILE voice analysis
@app.post("/api/stt")
async def speech_to_text(
    audio_file: UploadFile = File(...),
    sessionId: Optional[str] = Form(None)
):
    """
    Transcribe audio to text AND extract openSMILE voice features.
    If sessionId is provided, stores the features for soft skills analysis.
    """
    import tempfile
    
    try:
        audio_content = await audio_file.read()
        
        # Transcribe audio to text
        transcribed_text = await GeminiService.convert_speech_to_text(audio_content)
        
        # Extract openSMILE voice features
        opensmile_features = None
        try:
            # Save audio to temp file for openSMILE processing
            file_ext = audio_file.filename.split('.')[-1] if audio_file.filename else 'webm'
            with tempfile.NamedTemporaryFile(suffix=f".{file_ext}", delete=False) as temp_audio:
                temp_audio.write(audio_content)
                temp_path = temp_audio.name
            
            # Extract features using openSMILE
            opensmile_service = get_opensmile_service()
            features = opensmile_service.extract_features(temp_path)
            
            if features:
                opensmile_features = features.to_dict()
                logger.info(f"openSMILE features extracted: tone={opensmile_features.get('derived_scores', {}).get('tone')}, confidence={opensmile_features.get('derived_scores', {}).get('confidence')}")
                
                # Store in session if sessionId provided
                if sessionId and sessionId in sessions:
                    sessions[sessionId]["latest_opensmile_features"] = opensmile_features
                    logger.info(f"Stored openSMILE features for session {sessionId}")
            
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
        except Exception as e:
            logger.warning(f"openSMILE feature extraction failed: {e}")
            # Continue without openSMILE features - transcription still works
        
        return {
            "text": transcribed_text,
            "openSmileFeatures": opensmile_features
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT error: {e}")


# Pydantic model for voice analysis response
class VoiceAnalysisResponse(BaseModel):
    pitch: Dict[str, float]
    energy: Dict[str, Any]
    voice_quality: Dict[str, float]
    temporal: Dict[str, Any]
    derived_scores: Dict[str, float]
    source: str = "openSMILE"

@app.post("/api/analyze-voice", response_model=VoiceAnalysisResponse)
async def analyze_voice(
    audio_file: UploadFile = File(...),
    sessionId: Optional[str] = Form(None)
):
    """
    Analyze voice features from audio using openSMILE.
    Extracts pitch, energy, jitter, shimmer, and derives soft skill scores.
    """
    import tempfile
    
    try:
        audio_content = await audio_file.read()
        
        # Save audio to temp file for openSMILE processing
        file_ext = audio_file.filename.split('.')[-1] if audio_file.filename else 'webm'
        with tempfile.NamedTemporaryFile(suffix=f".{file_ext}", delete=False) as temp_audio:
            temp_audio.write(audio_content)
            temp_path = temp_audio.name
        
        try:
            # Extract features using openSMILE
            opensmile_service = get_opensmile_service()
            features = opensmile_service.extract_features(temp_path)
            
            if not features:
                raise HTTPException(status_code=422, detail="Could not extract voice features from audio")
            
            opensmile_features = features.to_dict()
            
            # Store in session if sessionId provided
            if sessionId and sessionId in sessions:
                sessions[sessionId]["latest_opensmile_features"] = opensmile_features
                logger.info(f"Stored openSMILE features for session {sessionId}")
            
            return VoiceAnalysisResponse(
                pitch=opensmile_features["pitch"],
                energy=opensmile_features["energy"],
                voice_quality=opensmile_features["voice_quality"],
                temporal=opensmile_features["temporal"],
                derived_scores=opensmile_features["derived_scores"],
                source="openSMILE" if opensmile_service.smile else "librosa"
            )
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Voice analysis error: {e}")


# Pydantic model for vision analysis
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


# New endpoint for Computer Vision Behavior Analysis
@app.post("/api/analyze-behavior", response_model=VisionAnalysisResponse)
async def analyze_behavior(request: VisionAnalysisRequest):
    """
    Analyze user behavior from webcam frame using CV
    Returns real-time feedback on presence, eye contact, posture, confidence
    """
    try:
        print(f"[analyze-behavior] Received request, image length: {len(request.image) if request.image else 0}")
        result = vision_service.process_base64_frame(request.image)
        
        if "error" in result:
            print(f"[analyze-behavior] Error from vision service: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Optionally store behavior metrics in session
        if request.sessionId and request.sessionId in sessions:
            if "behavior_metrics" not in sessions[request.sessionId]:
                sessions[request.sessionId]["behavior_metrics"] = []
            
            sessions[request.sessionId]["behavior_metrics"].append({
                "timestamp": result["timestamp"],
                "confidence_score": result["confidence_score"],
                "eye_contact": result["eye_contact"],
                "posture_good": result["posture"]["is_good"]
            })
        
        return VisionAnalysisResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in behavior analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Vision analysis error: {str(e)}")


# Endpoint to get behavior summary for a session
@app.get("/api/behavior-summary/{session_id}")
async def get_behavior_summary(session_id: str):
    """Get aggregated behavior metrics for an interview session"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    metrics = sessions[session_id].get("behavior_metrics", [])
    
    if not metrics:
        return {
            "session_id": session_id,
            "total_samples": 0,
            "message": "No behavior data collected"
        }
    
    # Calculate aggregates
    avg_confidence = sum(m["confidence_score"] for m in metrics) / len(metrics)
    good_eye_contact_pct = (sum(1 for m in metrics if m["eye_contact"] == "good") / len(metrics)) * 100
    good_posture_pct = (sum(1 for m in metrics if m["posture_good"]) / len(metrics)) * 100
    
    return {
        "session_id": session_id,
        "total_samples": len(metrics),
        "average_confidence": round(avg_confidence, 1),
        "eye_contact_percentage": round(good_eye_contact_pct, 1),
        "good_posture_percentage": round(good_posture_pct, 1),
        "overall_rating": "Excellent" if avg_confidence >= 70 else "Good" if avg_confidence >= 50 else "Needs Improvement"
    }
