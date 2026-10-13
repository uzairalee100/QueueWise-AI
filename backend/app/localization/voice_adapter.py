"""
QueueWise AI — Bilingual Voice & Speech Query Adapter

Specially designed for low-literacy citizens, multilingual public service environments,
and accessibility in hospitals, banks, and citizen service centers.

Features:
- Handles native Urdu (اردو), Roman Urdu (English alphabet), and English speech queries
- Intent extraction for token tracking, wait time, position ahead, and kiosk guidance
- Generates phonetically clear spoken announcements optimized for browser Text-to-Speech (TTS)
- Zero external speech dependencies required (graceful rule-based parsing with deterministic output)
"""
import re
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.models.token import Token, TokenStatus
from app.models.service_category import ServiceCategory
from app.services.queue_engine import QueueEngine
from app.services.wait_estimator import WaitEstimator


# Standard Low-Literacy Public Announcement Templates
STANDARD_ANNOUNCEMENTS: Dict[str, Dict[str, str]] = {
    "welcome": {
        "en": "Welcome to QueueWise public services. Touch the screen to get your token.",
        "ur": "کیو وائز پبلک سروسز میں خوش آمدید۔ ٹوکن حاصل کرنے کے لیے اسکرین کو چھوئیں۔",
        "roman": "QueueWise mein khush amdeed. Token hasil karne ke liye screen ko touch karein.",
    },
    "token_called": {
        "en": "Token {token_number}, please proceed to Counter {counter_name}.",
        "ur": "ٹوکن {token_number}، براہ کرم کاؤنٹر {counter_name} پر تشریف لائیں۔",
        "roman": "Token {token_number}, barah-e-karam Counter {counter_name} par tashreef layein.",
    },
    "turn_approaching": {
        "en": "Token {token_number}, your turn is approaching. You are next in line.",
        "ur": "ٹوکن {token_number}، آپ کی باری قریب ہے۔ آپ لائن میں اگلے ہیں۔",
        "roman": "Token {token_number}, aap ki baari qareeb hai. Aap line mein aglay hain.",
    },
    "delay_notice": {
        "en": "Notice: Counters are momentarily delayed. Thank you for your patience.",
        "ur": "اطلاع: کاؤنٹرز پر عارضی تاخیر ہے۔ آپ کے صبر کا شکریہ۔",
        "roman": "Ittela: Counters par aarzi takheer hai. Sabr ka shukriya.",
    },
    "cancelled": {
        "en": "Your token has been cancelled. Please request a new token if needed.",
        "ur": "آپ کا ٹوکن منسوخ کر دیا گیا ہے۔ ضرورت پڑنے پر نیا ٹوکن حاصل کریں۔",
        "roman": "Aap ka token mansookh kar diya gaya hai. Naya token hasil karein.",
    },
}


class VoiceAdapter:
    """Multilingual voice and conversational speech processing adapter."""

    @classmethod
    def detect_language(cls, text: str) -> str:
        """
        Detect language: 'ur' (Arabic/Persian script), 'roman_ur' (Roman Urdu), or 'en' (English).
        """
        # Check for Arabic / Urdu Unicode script range
        if re.search(r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]', text):
            return "ur"

        # Roman Urdu keywords
        roman_keywords = {
            "mera", "meri", "mere", "kab", "aayega", "aayegi", "kitne", "log", "agay",
            "hain", "kya", "haal", "kaun", "kaunsa", "kaunsi", "chahiye", "masla",
            "tashreef", "shukriya", "baari", "intezar", "intizar", "batao", "bataiye",
            "kaise", "kahan", "jana", "hai", "karo", "karein", "madad",
        }
        words = set(re.findall(r'\b\w+\b', text.lower()))
        if any(w in roman_keywords for w in words):
            return "roman_ur"

        return "en"

    @classmethod
    def extract_token_identifier(cls, query: str) -> Optional[str]:
        """
        Extract token display number or public ID from query (e.g. 'GEN-001', 'A-042', '001', 'token 2').
        """
        # Match standard display format like GEN-001, DOC-042, REG-101
        match_full = re.search(r'\b([A-Za-z]{2,5}-\d{2,4})\b', query, re.IGNORECASE)
        if match_full:
            return match_full.group(1).upper()

        # Match single letter dash number like A-042
        match_letter = re.search(r'\b([A-Za-z]-\d{2,4})\b', query, re.IGNORECASE)
        if match_letter:
            return match_letter.group(1).upper()

        # Match 'token 3' or 'token number 003'
        match_num = re.search(r'(?:token|number|no\.?)\s*#?\s*(\d{1,4})', query, re.IGNORECASE)
        if match_num:
            return match_num.group(1)

        return None

    @classmethod
    def classify_voice_intent(cls, query: str) -> str:
        """
        Classify intent from spoken utterance.
        """
        q = query.lower()

        if any(k in q for k in ["salam", "hello", "hi", "hey", "assalam"]):
            return "greeting"

        if any(k in q for k in ["kab aayega", "when", "turn", "baari", "wait", "intezar", "intizar", "kitni der", "how long"]):
            return "wait_time"

        if any(k in q for k in ["agay", "ahead", "kitne log", "people ahead", "line", "position"]):
            return "position_ahead"

        if any(k in q for k in ["status", "haal", "kya hai", "check", "maloom"]):
            return "token_status"

        if any(k in q for k in ["kahan jana", "where", "counter", "kahan", "location", "desk"]):
            return "counter_location"

        if any(k in q for k in ["naya token", "issue", "chahiye", "get token", "kiosk", "lena hai", "le lo"]):
            return "issue_token_guidance"

        if any(k in q for k in ["madad", "help", "guide", "tareeqa", "how"]):
            return "help"

        return "general_query"

    @classmethod
    async def process_voice_query(
        cls,
        session: AsyncSession,
        query: str,
        token_identifier: Optional[str] = None,
        session_id: str = "default",
    ) -> Dict[str, Any]:
        """
        Process a citizen or supervisor voice query and generate spoken TTS responses.
        """
        detected_lang = cls.detect_language(query)
        extracted_token = token_identifier or cls.extract_token_identifier(query)
        intent = cls.classify_voice_intent(query)

        token_obj: Optional[Token] = None
        if extracted_token:
            # Try to resolve token
            stmt = select(Token).where(
                and_(
                    Token.session_id == session_id,
                    (Token.display_number == extracted_token) | (Token.public_id == extracted_token),
                )
            )
            res = await session.execute(stmt)
            token_obj = res.scalar_one_or_none()

            # If not found with exact match, try matching just the digits at the end
            if not token_obj and extracted_token.isdigit():
                padded = f"{int(extracted_token):03d}"
                stmt_suffix = select(Token).where(
                    and_(
                        Token.session_id == session_id,
                        Token.display_number.endswith(f"-{padded}"),
                    )
                )
                res_suffix = await session.execute(stmt_suffix)
                token_obj = res_suffix.scalar_one_or_none()

        # Build response based on intent and resolved state
        spoken_en = ""
        spoken_ur = ""
        spoken_roman = ""
        chime_hint = "info"
        metadata: Dict[str, Any] = {
            "query": query,
            "detected_language": detected_lang,
            "intent": intent,
            "extracted_token": extracted_token,
            "token_found": token_obj is not None,
        }

        if token_obj:
            pos, ahead = await QueueEngine.get_queue_position_and_ahead(session, token_obj)
            estimate = await WaitEstimator.estimate_token_wait(session, token_obj)
            wait_mins = max(1, int(estimate.get("estimated_wait_minutes", 1)))
            metadata["position"] = pos
            metadata["people_ahead"] = ahead
            metadata["estimated_wait_minutes"] = wait_mins
            metadata["status"] = token_obj.status.value

            if token_obj.status == TokenStatus.WAITING:
                if ahead == 0:
                    spoken_en = f"Token {token_obj.display_number}: You are next! Please be ready near the counters."
                    spoken_ur = f"ٹوکن {token_obj.display_number}: آپ کی باری اگلی ہے! برائے مہربانی کاؤنٹرز کے قریب تیار رہیں۔"
                    spoken_roman = f"Token {token_obj.display_number}: Aap aglay hain! Meharbani farma kar counters ke qareeb tayyar rahein."
                    chime_hint = "approaching"
                else:
                    spoken_en = f"Token {token_obj.display_number} has {ahead} citizen{'s' if ahead > 1 else ''} ahead. Estimated wait is {wait_mins} minute{'s' if wait_mins > 1 else ''}."
                    spoken_ur = f"ٹوکن {token_obj.display_number} کے آگے {ahead} شہری ہیں۔ متوقع انتظار تقریباً {wait_mins} منٹ ہے۔"
                    spoken_roman = f"Token {token_obj.display_number} ke agay {ahead} afraad hain. Intezar takreeban {wait_mins} minute hai."
                    chime_hint = "info"

            elif token_obj.status == TokenStatus.CALLED:
                counter_name = token_obj.called_counter.name if token_obj.called_counter else "the assigned desk"
                spoken_en = f"Token {token_obj.display_number}: Your number is being called right now! Please proceed immediately to {counter_name}."
                spoken_ur = f"ٹوکن {token_obj.display_number}: آپ کا نمبر پکارا جا رہا ہے! براہ کرم فوری طور پر {counter_name} پر تشریف لائیں۔"
                spoken_roman = f"Token {token_obj.display_number}: Aap ka number pukara ja raha hai! Barah-e-karam fauran {counter_name} par tashreef layein."
                chime_hint = "turn_called"

            elif token_obj.status == TokenStatus.SERVING:
                spoken_en = f"Token {token_obj.display_number} is currently being served at the counter."
                spoken_ur = f"ٹوکن {token_obj.display_number} اس وقت کاؤنٹر پر سروس لے رہا ہے۔"
                spoken_roman = f"Token {token_obj.display_number} is waqt counter par maujood hai."

            elif token_obj.status == TokenStatus.COMPLETED:
                spoken_en = f"Token {token_obj.display_number} service has already been completed. Thank you!"
                spoken_ur = f"ٹوکن {token_obj.display_number} کی سروس مکمل ہو چکی ہے۔ شکریہ!"
                spoken_roman = f"Token {token_obj.display_number} ki service mukammal ho chuki hai. Shukriya!"

            elif token_obj.status == TokenStatus.SKIPPED:
                spoken_en = f"Token {token_obj.display_number} was marked as a no-show. Please speak to staff to recall your turn."
                spoken_ur = f"ٹوکن {token_obj.display_number} غیر حاضری کی وجہ سے آگے بڑھا دیا گیا ہے۔ عملے سے رابطہ کریں۔"
                spoken_roman = f"Token {token_obj.display_number} no-show ho gaya tha. Dobara baari ke liye staff se baat karein."
                chime_hint = "warning"

            else:
                spoken_en = f"Token {token_obj.display_number} is currently marked as {token_obj.status.value}."
                spoken_ur = f"ٹوکن {token_obj.display_number} کی حالت {token_obj.status.value} ہے۔"
                spoken_roman = f"Token {token_obj.display_number} ka status {token_obj.status.value} hai."

        else:
            # No specific token mentioned or found
            if intent == "issue_token_guidance":
                spoken_en = "To issue a new token, please select your desired service on the touch kiosk screen."
                spoken_ur = "نیا ٹوکن حاصل کرنے کے لیے ٹچ اسکرین پر مطلوبہ سروس کا انتخاب کریں۔"
                spoken_roman = "Naya token lene ke liye screen par apni service select karein."
            elif intent == "greeting":
                spoken_en = "Welcome to QueueWise. Tell me your token number or ask about queue wait times."
                spoken_ur = "خوش آمدید۔ اپنا ٹوکن نمبر بتائیں یا قطار کے انتظار کا وقت پوچھیں۔"
                spoken_roman = "Khush amdeed. Apna token number batayein ya intezar ka waqt poochein."
            elif extracted_token:
                spoken_en = f"I could not find token {extracted_token}. Please verify your ticket number or ask a staff member."
                spoken_ur = f"ٹوکن {extracted_token} کا ریکارڈ نہیں ملا۔ برائے مہربانی اپنے ٹوکن پر لکھا نمبر دوبارہ چیک کریں۔"
                spoken_roman = f"Token {extracted_token} nahi mila. Meharbani farma kar apna number dobara check karein."
                chime_hint = "warning"
            else:
                spoken_en = "Please state your token number like 'GEN 001' to check your turn and wait time."
                spoken_ur = "اپنی باری معلوم کرنے کے لیے اپنا ٹوکن نمبر بتائیں جیسے 'GEN 001'۔"
                spoken_roman = "Apni baari jan'ne ke liye apna token number batayein jaise 'GEN 001'."

        # Select primary spoken language according to detected input
        if detected_lang == "ur":
            primary_speech = spoken_ur
        elif detected_lang == "roman_ur":
            primary_speech = spoken_roman
        else:
            primary_speech = spoken_en

        return {
            "query": query,
            "detected_language": detected_lang,
            "intent": intent,
            "spoken_text": primary_speech,
            "spoken_text_en": spoken_en,
            "spoken_text_ur": spoken_ur,
            "spoken_text_roman": spoken_roman,
            "chime_hint": chime_hint,
            "token_resolved": token_obj is not None,
            "metadata": metadata,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @classmethod
    def get_standard_announcements(cls) -> Dict[str, Dict[str, str]]:
        """Return registered announcement templates for low-literacy kiosk and staff broadcast."""
        return STANDARD_ANNOUNCEMENTS
