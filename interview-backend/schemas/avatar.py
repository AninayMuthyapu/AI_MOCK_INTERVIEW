"""Avatar generation Pydantic models."""
from pydantic import BaseModel, Field


class GenerateAvatarRequest(BaseModel):
    text: str
    voice: str = Field(default="en_male")
    emotion: str = Field(default="neutral")


class GenerateAvatarResponse(BaseModel):
    video_url: str
