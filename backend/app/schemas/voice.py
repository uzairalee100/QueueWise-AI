"""
QueueWise AI — Voice & Speech Pydantic Schemas

Request and response models for voice queries and audio announcements.
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class VoiceQueryRequest(BaseModel):
    """Voice inquiry from citizen or supervisor."""
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Spoken utterance transcript in English, native Urdu, or Roman Urdu",
        examples=["Mera token kab aayega?", "What is my wait time for GEN-001?"],
    )
    token_identifier: Optional[str] = Field(
        default=None,
        description="Optional explicitly provided token identifier (e.g. GEN-001 or public_id)",
    )
    session_id: str = Field(
        default="default",
        description="Queue session ID",
    )


class VoiceQueryResponse(BaseModel):
    """Response containing TTS-formatted speech text and localization metadata."""
    query: str = Field(description="Original input utterance")
    detected_language: str = Field(description="Detected language (en, ur, roman_ur)")
    intent: str = Field(description="Classified voice intent")
    spoken_text: str = Field(description="Primary text formulated for immediate Text-to-Speech playback")
    spoken_text_en: str = Field(description="English translation of spoken output")
    spoken_text_ur: str = Field(description="Urdu script of spoken output")
    spoken_text_roman: str = Field(description="Roman Urdu phonetic text for easy reading")
    chime_hint: str = Field(
        default="info",
        description="Audio cue suggestion (turn_called, approaching, info, warning)",
    )
    token_resolved: bool = Field(description="Whether a specific token record was matched")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Operational queue data backing the response")
    timestamp: str = Field(description="Timestamp of the response")


class VoiceAnnouncementsResponse(BaseModel):
    """Registered public service broadcast announcement templates."""
    announcements: Dict[str, Dict[str, str]]
