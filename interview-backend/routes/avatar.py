"""Avatar generation routes."""
import os

from fastapi import APIRouter, HTTPException

from config import STATIC_DIR
from schemas.avatar import GenerateAvatarRequest, GenerateAvatarResponse

router = APIRouter(tags=["avatar"])


@router.post("/generate_avatar", response_model=GenerateAvatarResponse)
async def generate_avatar(req: GenerateAvatarRequest):
    from main import avatar_service  # lazy import

    try:
        out_path = avatar_service.generate_video(req.text, voice=req.voice, emotion=req.emotion)
        if not out_path:
            raise HTTPException(status_code=500, detail="Avatar generation failed.")

        rel_path = os.path.relpath(out_path, STATIC_DIR)
        video_url = f"/static/{rel_path.replace(os.sep, '/')}"
        return GenerateAvatarResponse(video_url=video_url)
    except HTTPException:
        raise
    except Exception as e:
        print(f"/generate_avatar error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error generating avatar")
