"""Resume routes — parse, ATS review, preview plan."""
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, File, UploadFile, Form

from schemas.resume import ATSReviewResponse, PlanPreviewResponse, PlanItem
from services.resume_parser import ResumeParserService
from services.gemini_service import GeminiService

router = APIRouter(prefix="/api", tags=["resume"])


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
