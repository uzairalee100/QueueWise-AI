"""
QueueWise AI — Voice & Speech REST API Endpoints

Exposes the Voice Adapter for low-literacy citizen inquiries and audio announcements:
- POST /api/v1/voice/query         -> Spoken query resolution with TTS speech output
- GET  /api/v1/voice/announcements -> Low-literacy standard announcement templates
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.localization.voice_adapter import VoiceAdapter
from app.schemas.voice import (
    VoiceQueryRequest,
    VoiceQueryResponse,
    VoiceAnnouncementsResponse,
)

router = APIRouter()


@router.post(
    "/query",
    response_model=VoiceQueryResponse,
    summary="Process Voice Query",
    description=(
        "Process a spoken or typed citizen inquiry in English, native Urdu, or Roman Urdu. "
        "Returns synthesized spoken text ready for Web Speech API Text-to-Speech (TTS)."
    ),
)
async def process_voice_query(
    request: VoiceQueryRequest,
    session: AsyncSession = Depends(get_db),
) -> VoiceQueryResponse:
    """Process a voice utterance and return spoken response."""
    result = await VoiceAdapter.process_voice_query(
        session=session,
        query=request.query,
        token_identifier=request.token_identifier,
        session_id=request.session_id,
    )
    return VoiceQueryResponse(**result)


@router.get(
    "/announcements",
    response_model=VoiceAnnouncementsResponse,
    summary="Get Standard Announcement Templates",
    description="Retrieve registered bilingual announcement templates (English, Urdu, Roman Urdu).",
)
async def get_announcements() -> VoiceAnnouncementsResponse:
    """Return standard announcement templates."""
    return VoiceAnnouncementsResponse(
        announcements=VoiceAdapter.get_standard_announcements()
    )
