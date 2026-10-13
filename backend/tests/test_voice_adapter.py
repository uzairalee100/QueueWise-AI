"""
QueueWise AI — Bilingual Voice & Speech Adapter Test Suite

Verifies:
- Multilingual language detection (English, Native Urdu, Roman Urdu)
- Token identifier extraction from spoken utterances
- Voice intent classification for low-literacy citizen inquiries
- Live token state resolution and Text-to-Speech (TTS) response formulation
- /api/v1/voice/query and /api/v1/voice/announcements API endpoints
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.localization.voice_adapter import VoiceAdapter
from app.services.queue_engine import QueueEngine


class TestVoiceLanguageAndIntentDetection:
    """Unit tests for language detection and intent classification."""

    def test_language_detection(self):
        # Native Urdu (Arabic script)
        assert VoiceAdapter.detect_language("میرا ٹوکن کب آئے گا؟") == "ur"
        assert VoiceAdapter.detect_language("کتنے لوگ آگے ہیں؟") == "ur"

        # Roman Urdu
        assert VoiceAdapter.detect_language("mera number kab aayega?") == "roman_ur"
        assert VoiceAdapter.detect_language("kitne log mere agay hain") == "roman_ur"
        assert VoiceAdapter.detect_language("naya token chahiye") == "roman_ur"

        # English
        assert VoiceAdapter.detect_language("When will my token be called?") == "en"
        assert VoiceAdapter.detect_language("How many people are ahead of me?") == "en"

    def test_token_identifier_extraction(self):
        assert VoiceAdapter.extract_token_identifier("Status of GEN-001 please") == "GEN-001"
        assert VoiceAdapter.extract_token_identifier("mera token DOC-042 hai") == "DOC-042"
        assert VoiceAdapter.extract_token_identifier("check token 5 please") == "5"
        assert VoiceAdapter.extract_token_identifier("kitna wait hai?") is None

    def test_voice_intent_classification(self):
        assert VoiceAdapter.classify_voice_intent("mera number kab aayega") == "wait_time"
        assert VoiceAdapter.classify_voice_intent("kitne log agay hain") == "position_ahead"
        assert VoiceAdapter.classify_voice_intent("kahan jana hai") == "counter_location"
        assert VoiceAdapter.classify_voice_intent("naya token lena hai") == "issue_token_guidance"
        assert VoiceAdapter.classify_voice_intent("Salam, madad chahiye") == "greeting"


@pytest.mark.anyio
class TestVoiceQueryResolutionWithDatabase:
    """Verify end-to-end voice query resolution against stored tokens."""

    async def test_voice_query_with_waiting_token(self, db_session: AsyncSession):
        """Spoken inquiry with known token returns formatted TTS text with position and wait time."""
        token = await QueueEngine.create_token(
            session=db_session,
            service_code="GEN",
            session_id="voice-test",
        )

        res = await VoiceAdapter.process_voice_query(
            session=db_session,
            query=f"mera token {token.display_number} kab aayega",
            session_id="voice-test",
        )

        assert res["token_resolved"] is True
        assert res["detected_language"] == "roman_ur"
        assert token.display_number in res["spoken_text"]
        assert "spoken_text_en" in res
        assert "spoken_text_ur" in res
        assert "spoken_text_roman" in res

    async def test_voice_query_native_urdu(self, db_session: AsyncSession):
        """Urdu query produces primary spoken text in Urdu script."""
        # Create t1 (first in line) and t2 (second in line)
        _t1 = await QueueEngine.create_token(
            session=db_session,
            service_code="DOC",
            session_id="voice-test",
        )
        t2 = await QueueEngine.create_token(
            session=db_session,
            service_code="DOC",
            session_id="voice-test",
        )

        res = await VoiceAdapter.process_voice_query(
            session=db_session,
            query=f"میرا ٹوکن {t2.display_number} ہے، کتنی دیر لگے گی؟",
            session_id="voice-test",
        )

        assert res["token_resolved"] is True
        assert res["detected_language"] == "ur"
        assert "منٹ" in res["spoken_text"]  # Urdu word for minutes
        assert t2.display_number in res["spoken_text"]

    async def test_voice_query_general_guidance(self, db_session: AsyncSession):
        """Inquiry without token gives clear kiosk guidance."""
        res = await VoiceAdapter.process_voice_query(
            session=db_session,
            query="naya token kaise milega",
            session_id="voice-test",
        )
        assert res["token_resolved"] is False
        assert res["intent"] == "issue_token_guidance"
        assert "screen" in res["spoken_text"].lower() or "service" in res["spoken_text"].lower()


@pytest.mark.anyio
class TestVoiceAPIEndpoints:
    """Integration tests for /api/v1/voice endpoints."""

    async def test_voice_query_api_endpoint(self, async_client: AsyncClient):
        """POST /api/v1/voice/query processes spoken text."""
        resp = await async_client.post(
            "/api/v1/voice/query",
            json={
                "query": "When is my turn for token GEN-001?",
                "session_id": "default",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "spoken_text" in data
        assert "detected_language" in data
        assert data["detected_language"] == "en"
        assert "chime_hint" in data

    async def test_voice_announcements_endpoint(self, async_client: AsyncClient):
        """GET /api/v1/voice/announcements returns standard public broadcast templates."""
        resp = await async_client.get("/api/v1/voice/announcements")
        assert resp.status_code == 200
        data = resp.json()
        assert "announcements" in data
        assert "token_called" in data["announcements"]
        assert "turn_approaching" in data["announcements"]
        assert "en" in data["announcements"]["token_called"]
        assert "ur" in data["announcements"]["token_called"]
        assert "roman" in data["announcements"]["token_called"]
