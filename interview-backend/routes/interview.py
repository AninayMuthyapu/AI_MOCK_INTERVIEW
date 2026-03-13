"""Interview routes — start, submit, hint, summary, current session."""
from datetime import datetime
from typing import Dict, Any, Optional, Union

from fastapi import APIRouter, HTTPException, File, UploadFile, Form

from config import model
from schemas.interview import (
    InterviewAnswer, InterviewStartResponse, InterviewSubmitResponse,
    InterviewSummaryResponse, HintRequest, HintResponse,
    QuestionResponse, CodingQuestionResponse, MCQQuestionResponse,
    FeedbackResponse,
)
from schemas.resume import PlanItem
from services.gemini_service import GeminiService, get_next_question_data
from services.session_manager import session_data, sessions

router = APIRouter(prefix="/api", tags=["interview"])

HR_QUESTIONS = [
    "Tell me about yourself.",
    "Why do you want to work here?",
    "What are your strengths and weaknesses?",
    "Tell me about a challenge you faced and how you handled it.",
    "Where do you see yourself in 5 years?"
]


@router.get("/current-session")
async def get_current_session():
    """Returns current session if exists, otherwise 404."""
    raise HTTPException(status_code=404, detail="No active session")


@router.post("/start-interview", response_model=InterviewStartResponse)
async def start_interview(
    resumeFile: UploadFile | None = File(None),
    jobDescription: str = Form(""),
    yearsOfExperience: int = Form(...),
    jobRole: str = Form(...),
    companyName: str = Form(...)
):
    if not all([yearsOfExperience, jobRole, companyName]):
        raise HTTPException(status_code=400, detail="Missing required form data.")

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

    sessions[session_id] = {
        "company_name": effective_company,
        "job_role": effective_role,
        "years_of_experience": effective_yoe,
        "extracted_resume_text": "",
        "current_round": 0,
        "current_question": initial_question_data.question,
        "current_question_type": initial_round["type"],
        "interview_plan": interview_plan,
        "current_round_index": 0,
        "current_question_index": 0,
        "interview_history": [],
        "questions_and_answers": [],
        "is_complete": False,
        "start_time": datetime.now(),
        "session_id": session_id
    }

    # Start background posture analysis
    try:
        from services.posture_service import posture_service
        posture_service.start_background(session_id)
    except Exception as e:
        print(f"Posture analysis could not start: {e}")

    return InterviewStartResponse(
        message="Interview session started successfully.",
        sessionId=session_id,
        questionData=initial_question_data,
        roundTitle=initial_round["title"],
        isComplete=False,
        feedback=None
    )


@router.post("/start-hr-interview", response_model=InterviewStartResponse)
async def start_hr_interview():
    """Starts a specialized HR mock interview sequence."""
    
    # Generate unique session ID
    session_id = "hr_" + str(hash(datetime.now().isoformat()))[2:10]
    
    sessions[session_id] = {
        "company_name": "General",
        "job_role": "HR Interview",
        "years_of_experience": 0,
        "extracted_resume_text": "",
        "current_round": 0,
        "current_question": HR_QUESTIONS[0],
        "current_question_type": "behavioral",
        "interview_plan": [{"title": "HR Interview", "type": "behavioral", "question_count": 5}],
        "current_round_index": 0,
        "current_question_index": 0,
        "interview_history": [],
        "questions_and_answers": [],
        "is_complete": False,
        "start_time": datetime.now(),
        "session_id": session_id,
        "is_hr_interview": True
    }

    # Start background posture analysis
    try:
        from services.posture_service import posture_service
        posture_service.start_background(session_id)
    except Exception as e:
        print(f"Posture analysis could not start: {e}")

    return InterviewStartResponse(
        message="HR Interview session started successfully.",
        sessionId=session_id,
        questionData=QuestionResponse(question=HR_QUESTIONS[0], type="behavioral"),
        roundTitle="HR Round",
        isComplete=False,
        feedback=None
    )


@router.post("/submit-answer", response_model=InterviewSubmitResponse)
async def submit_answer(answer_data: InterviewAnswer):
    session = session_data.get(answer_data.sessionId)
    session_new = sessions.get(answer_data.sessionId)

    if not session and not session_new:
        raise HTTPException(status_code=404, detail="Session not found.")

    if session_new:
        session = session_new

    interview_plan = session["interview_plan"]
    current_round_index = session["current_round_index"]
    current_question_index = session["current_question_index"]
    current_round = interview_plan[current_round_index]

    # Get question text for feedback
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

    feedback = await GeminiService.get_feedback_and_score(
        question=question_to_feedback,
        userAnswer=answer_data.userAnswer,
        company_name=session["company_name"],
        job_role=session["job_role"],
        extracted_resume_text=None
    )

    behavior_data = answer_data.behaviorData or session.get("latest_behavior_data", None)
    opensmile_features = session.get("latest_opensmile_features", None)

    soft_skills = await GeminiService.generate_soft_skills_feedback(
        user_answer=answer_data.userAnswer,
        question=question_to_feedback,
        round_title=current_round["title"],
        behavior_data=behavior_data,
        opensmile_features=opensmile_features
    )

    if "interview_history" in session:
        session["interview_history"].append({
            "question": question_to_feedback,
            "user_answer": answer_data.userAnswer,
            "feedback": feedback.dict(),
            "soft_skills": soft_skills.dict()
        })

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

        if session.get("is_complete", False):
            start_time = sessions[answer_data.sessionId].get("start_time")
            if start_time:
                duration = (datetime.now() - start_time).total_seconds() / 60
                sessions[answer_data.sessionId]["duration_minutes"] = int(duration)
            sessions[answer_data.sessionId]["is_complete"] = True

    if current_question_index + 1 < current_round["question_count"]:
        session["current_question_index"] += 1
        
        # If HR interview, pick next static question
        if session.get("is_hr_interview"):
            next_question = HR_QUESTIONS[session["current_question_index"]]
            next_question_data = QuestionResponse(question=next_question, type="behavioral")
        else:
            next_question_data = await get_next_question_data(session, current_round)
            
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


@router.post("/get-hint", response_model=HintResponse)
async def get_hint(hint_request: HintRequest):
    """Provide a helpful hint when the user is stuck on a question."""
    try:
        session_id = hint_request.sessionId

        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")

        session = sessions[session_id]
        current_question = session.get("current_question", "")
        question_type = session.get("current_question_type", "behavioral")
        job_role = session.get("job_role", "")
        current_answer = hint_request.currentAnswer

        if "hints_used" not in session:
            session["hints_used"] = 0
        session["hints_used"] += 1

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
        return HintResponse(
            hint="Take a moment to think about your past experiences. What situation comes to mind? Try using the STAR method: Situation, Task, Action, Result.",
            hint_type="guidance"
        )


@router.get("/interview-summary/{session_id}", response_model=InterviewSummaryResponse)
async def get_interview_summary(session_id: str):
    """Returns comprehensive interview summary with overall feedback."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    sess = sessions[session_id]
    company_name = sess.get("company_name", "Unknown Company")
    job_role = sess.get("job_role", "Unknown Role")

    # Stop background posture analysis and collect report
    posture_report = None
    try:
        from services.posture_service import posture_service
        posture_report = posture_service.stop_background(session_id)
    except Exception as e:
        print(f"Could not get posture report: {e}")

    summary = await GeminiService.generate_interview_summary(
        sess, company_name, job_role, posture_report=posture_report
    )
    return summary
