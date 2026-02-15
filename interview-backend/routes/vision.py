"""Vision / behavior analysis routes."""
from fastapi import APIRouter, HTTPException

from schemas.vision import VisionAnalysisRequest, VisionAnalysisResponse
from services.session_manager import sessions

router = APIRouter(prefix="/api", tags=["vision"])


@router.post("/analyze-behavior", response_model=VisionAnalysisResponse)
async def analyze_behavior(request: VisionAnalysisRequest):
    """Analyze user behavior from webcam frame using CV."""
    from main import vision_service  # lazy import

    try:
        print(f"[analyze-behavior] Received request, image length: {len(request.image) if request.image else 0}")
        result = vision_service.process_base64_frame(request.image)

        if "error" in result:
            print(f"[analyze-behavior] Error from vision service: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])

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


@router.get("/behavior-summary/{session_id}")
async def get_behavior_summary(session_id: str):
    """Get aggregated behavior metrics for an interview session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    metrics = sessions[session_id].get("behavior_metrics", [])

    if not metrics:
        return {
            "session_id": session_id,
            "total_samples": 0,
            "message": "No behavior data collected"
        }

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
