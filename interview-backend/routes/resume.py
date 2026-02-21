"""Resume routes — parse, ATS review, preview plan, resume analyzer."""
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from pydantic import BaseModel
from typing import List

from schemas.resume import ATSReviewResponse, PlanPreviewResponse, PlanItem
from services.resume_parser import ResumeParserService
from services.gemini_service import GeminiService

router = APIRouter(prefix="/api", tags=["resume"])


class ResumeAnalysisResponse(BaseModel):
    ats_score: int
    content_relevance: int
    clarity_score: int
    professional_language: int
    formatting_score: int
    jd_match_score: Optional[int] = None
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    keyword_match_percentage: int
    overall_feedback: str


@router.post("/parse-resume")
async def parse_resume(file: UploadFile = File(...)):
    file_extension = file.filename.split('.')[-1].lower()

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
        os.remove(file_path)

    return {"filename": file.filename, "extracted_text": extracted_text}


@router.post("/ats-review", response_model=ATSReviewResponse)
async def ats_review(
    resumeFile: UploadFile = File(...),
    jobDescription: str = Form(...)
):
    """Analyzes resume against job description and provides ATS score and feedback."""
    if not jobDescription.strip():
        raise HTTPException(status_code=400, detail="Job description is required for ATS review.")

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

        ats_result = await GeminiService.review_resume_ats(resume_text, jobDescription)
        return ats_result

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in ats_review: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing resume: {str(e)}")
    finally:
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Warning: Could not delete temporary file {file_path}: {str(e)}")


@router.post("/preview-plan", response_model=PlanPreviewResponse)
async def preview_plan(
    resumeFile: UploadFile | None = File(None),
    jobDescription: str = Form(""),
    yearsOfExperience: int = Form(0),
    jobRole: str = Form(""),
    companyName: str = Form("")
):
    """Returns an interview plan preview without creating a session."""
    effective_role = jobRole
    effective_yoe = yearsOfExperience
    effective_company = companyName

    plan, is_ai_generated, generation_source = await GeminiService.generate_interview_plan(
        effective_company, effective_role, effective_yoe
    )

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


@router.post("/analyze-resume", response_model=ResumeAnalysisResponse)
async def analyze_resume(
    resumeFile: UploadFile = File(...),
    jobDescription: str = Form(""),
):
    """Full resume analysis — works with or without a job description.
    Returns ATS score, four quality metrics, and optional JD match score.
    """
    import json
    from config import model, logger
    import google.generativeai as genai

    file_extension = (resumeFile.filename or "").split(".")[-1].lower()
    file_path = f"/tmp/{resumeFile.filename}"

    try:
        with open(file_path, "wb") as f:
            f.write(await resumeFile.read())

        if file_extension == "pdf":
            resume_text = ResumeParserService.extract_text_from_pdf(file_path)
        elif file_extension == "docx":
            resume_text = ResumeParserService.extract_text_from_docx(file_path)
        else:
            raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF or DOCX file.")

        if not resume_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from resume.")

        has_jd = bool(jobDescription.strip())
        jd_section = f"\nJOB DESCRIPTION:\n{jobDescription[:2000]}" if has_jd else ""
        jd_score_field = '"jd_match_score": 75' if has_jd else '"jd_match_score": null'

        prompt = f"""You are a brutally honest, senior technical recruiter and ATS specialist with 15+ years of experience. Analyze the resume below with no sugarcoating.

RESUME:
{resume_text[:3500]}
{jd_section}

Return ONLY a raw JSON object (no markdown, no code fences, no explanation). Use this exact structure:
{{"ats_score": 82, "content_relevance": 78, "clarity_score": 85, "professional_language": 90, "formatting_score": 75, {jd_score_field}, "keyword_match_percentage": 70, "strengths": ["specific strength 1", "specific strength 2", "specific strength 3"], "weaknesses": ["specific weakness 1", "specific weakness 2", "specific weakness 3"], "recommendations": ["actionable recommendation 1", "actionable recommendation 2", "...add as many as needed, typically 6-8 specific recommendations"], "overall_feedback": "Write 4-6 sentences of brutally honest, professional feedback. Be specific about what is wrong and why it hurts the candidate. Do not be vague. Call out missing impact metrics, weak action verbs, formatting issues, keyword gaps, and anything that would cause a recruiter to reject this resume. End with 1-2 sentences on the most critical things to fix immediately."}}

All scores must be integers 0-100. Be ruthlessly accurate. Return ONLY the JSON object."""

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(temperature=0.3, max_output_tokens=15000),
        )

        raw = (response.text or "").strip()
        # Debug: log what the model actually returned
        try:
            finish = response.candidates[0].finish_reason if response.candidates else "NO_CANDIDATES"
            print(f"[DEBUG] finish_reason={finish}, response.text={repr(raw[:500])}")
        except Exception as dbg_e:
            print(f"[DEBUG] Could not read candidates: {dbg_e}")

        # Extract JSON robustly — works even if response is truncated or wrapped in markdown fences
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end < start:
            raise ValueError(f"No JSON object found in model response. finish_reason={getattr(response.candidates[0], 'finish_reason', '?') if response.candidates else 'N/A'}, raw={repr(raw[:200])}")

        json_str = raw[start:end + 1]
        result = json.loads(json_str)

        return ResumeAnalysisResponse(
            ats_score=int(result.get("ats_score", 65)),
            content_relevance=int(result.get("content_relevance", 65)),
            clarity_score=int(result.get("clarity_score", 65)),
            professional_language=int(result.get("professional_language", 65)),
            formatting_score=int(result.get("formatting_score", 65)),
            jd_match_score=int(result["jd_match_score"]) if result.get("jd_match_score") is not None else None,
            keyword_match_percentage=int(result.get("keyword_match_percentage", 50)),
            strengths=result.get("strengths", ["Resume uploaded successfully"]),
            weaknesses=result.get("weaknesses", ["Could be more specific"]),
            recommendations=result.get("recommendations", ["Tailor resume to job description"]),
            overall_feedback=result.get("overall_feedback", "Resume analysis complete."),
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in analyze_resume: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing resume: {str(e)}")
    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
