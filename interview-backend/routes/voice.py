"""Voice routes — TTS, STT, voice analysis."""
import os
import tempfile
import base64
from typing import Optional

from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from fastapi.responses import Response

from config import logger
from schemas.voice import TTSRequest, VoiceAnalysisResponse
from services.session_manager import sessions

router = APIRouter(prefix="/api", tags=["voice"])


@router.post("/tts")
async def tts(tts_request: TTSRequest):
    """Convert text to speech using ElevenLabs and return audio/mpeg bytes."""
    from main import voice_service  # lazy import to avoid circular dependency

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
    except HTTPException:
        raise
    except Exception as e:
        return {
            "fallback": "client_tts",
            "reason": "tts_error",
            "message": "Using client-side TTS due to server TTS error",
            "text": tts_request.text,
            "voice": tts_request.voice,
        }


@router.get("/voices")
async def list_voices():
    """Return available ElevenLabs voices (name -> id)."""
    from main import voice_service

    try:
        return voice_service.list_voices()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stt")
async def speech_to_text(
    audio_file: UploadFile = File(...),
    sessionId: Optional[str] = Form(None)
):
    """Transcribe audio to text AND extract openSMILE voice features."""
    from opensmile_service import get_opensmile_service
    from config import model as gemini_model

    try:
        audio_content = await audio_file.read()

        # Transcribe using Gemini
        try:
            audio_b64 = base64.b64encode(audio_content).decode("utf-8")
            response = gemini_model.generate_content([
                "Transcribe the following audio. Return ONLY the transcribed text, nothing else.",
                {"mime_type": "audio/webm", "data": audio_b64}
            ])
            transcribed_text = response.text.strip() if response.text else ""
        except Exception as e:
            logger.warning(f"Gemini STT failed, returning empty: {e}")
            transcribed_text = ""

        opensmile_features = None
        try:
            file_ext = audio_file.filename.split('.')[-1] if audio_file.filename else 'webm'
            with tempfile.NamedTemporaryFile(suffix=f".{file_ext}", delete=False) as temp_audio:
                temp_audio.write(audio_content)
                temp_path = temp_audio.name

            opensmile_service = get_opensmile_service()
            features = opensmile_service.extract_features(temp_path)

            if features:
                opensmile_features = features.to_dict()
                logger.info(f"openSMILE features extracted: tone={opensmile_features.get('derived_scores', {}).get('tone')}, confidence={opensmile_features.get('derived_scores', {}).get('confidence')}")

                if sessionId and sessionId in sessions:
                    sessions[sessionId]["latest_opensmile_features"] = opensmile_features
                    logger.info(f"Stored openSMILE features for session {sessionId}")

            if os.path.exists(temp_path):
                os.remove(temp_path)

        except Exception as e:
            logger.warning(f"openSMILE feature extraction failed: {e}")

        return {
            "text": transcribed_text,
            "openSmileFeatures": opensmile_features
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT error: {e}")


@router.post("/analyze-voice", response_model=VoiceAnalysisResponse)
async def analyze_voice(
    audio_file: UploadFile = File(...),
    sessionId: Optional[str] = Form(None)
):
    """Analyze voice features from audio using openSMILE."""
    from opensmile_service import get_opensmile_service

    try:
        audio_content = await audio_file.read()

        file_ext = audio_file.filename.split('.')[-1] if audio_file.filename else 'webm'
        with tempfile.NamedTemporaryFile(suffix=f".{file_ext}", delete=False) as temp_audio:
            temp_audio.write(audio_content)
            temp_path = temp_audio.name

        try:
            opensmile_service = get_opensmile_service()
            features = opensmile_service.extract_features(temp_path)

            if not features:
                raise HTTPException(status_code=422, detail="Could not extract voice features from audio")

            opensmile_features = features.to_dict()

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
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Voice analysis error: {e}")
