# Save as twilio_service.py
"""
Production-grade Twilio service for SMS and WhatsApp messaging (production usage).
- Strict validation (E.164)
- Template-first WhatsApp sending (Content API)
- Clear error handling and classification
- Separate messaging service SIDs for SMS and WhatsApp
- No accidental mixing of from_ and messaging_service_sid
- Returns actionable details for observability/alerts
"""

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Optional, Dict, Tuple, Any

from decouple import config
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

logger = logging.getLogger("twilio_service")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(ch)

# ---------- Helpers & constants ----------
E164_REGEX = re.compile(r'^\+[1-9]\d{1,14}$')

_PERMANENT_ERROR_CODES = {63016, 63007, 63014, 63024, 21211}
_TRANSIENT_ERROR_CODES = {21610, 21612, 21614, 21608, 20429, 63017}  # extend as required

def _is_valid_e164(number: str) -> bool:
    return bool(number and E164_REGEX.match(number))

def _normalize_raw_phone(phone: str) -> str:
    if not phone:
        return ""
    s = str(phone).strip()
    if s.lower().startswith("whatsapp:"):
        s = s[len("whatsapp:"):]
    s = re.sub(r'[()\-\s\.]', '', s)
    if not s.startswith('+'):
        s = '+' + s.lstrip('+')
    return s

def _whatsapp_prefix(number_e164: str) -> str:
    return f"whatsapp:{number_e164}"

def _classify_error_code(code: Optional[int]) -> str:
    if code is None:
        return "unknown"
    if code in _PERMANENT_ERROR_CODES:
        return "permanent"
    if code in _TRANSIENT_ERROR_CODES:
        return "transient"
    return "unknown"

# ---------- Config and Exceptions ----------
@dataclass
class TwilioConfig:
    account_sid: str
    auth_token: str
    verify_sid: Optional[str] = None
    verify_secret: Optional[str] = None
    messaging_service_sid_sms: Optional[str] = None  # SMS messaging service SID
    messaging_service_sid_whatsapp: Optional[str] = None  # WhatsApp messaging service SID
    phone_number: Optional[str] = None
    whatsapp_phone_number: Optional[str] = None
    whatsapp_content_sid: Optional[str] = None
    test_mode: bool = False
    allow_plaintext_when_session_open: bool = False

    @classmethod
    def from_env(cls) -> 'TwilioConfig':
        return cls(
            account_sid=config('TWILIO_ACCOUNT_SID', default=''),
            auth_token=config('TWILIO_AUTH_TOKEN', default=''),
            verify_sid=config('TWILIO_VERIFY_SID', default=None),
            verify_secret=config('TWILIO_VERIFY_SECRET', default=None),
            messaging_service_sid_sms=config('TWILIO_MESSAGING_SERVICE_SID_SMS', default=None),
            messaging_service_sid_whatsapp=config('TWILIO_MESSAGING_SERVICE_SID_WHATSAPP', default=None),
            phone_number=config('TWILIO_PHONE_NUMBER', default=None),
            whatsapp_phone_number=config('TWILIO_WHATSAPP_PHONE_NUMBER', default=None),
            whatsapp_content_sid=config('TWILIO_WHATSAPP_CONTENT_SID', default=None),
            test_mode=config('TWILIO_TEST_MODE', default='false', cast=bool),
            allow_plaintext_when_session_open=config('TWILIO_ALLOW_PLAIN_WHEN_SESSION', default='false', cast=bool),
        )

    def validate(self) -> Tuple[bool, Optional[str]]:
        if not self.account_sid:
            return False, "TWILIO_ACCOUNT_SID is required"
        if not self.auth_token:
            return False, "TWILIO_AUTH_TOKEN is required"
        if self.whatsapp_content_sid and not self.whatsapp_phone_number:
            return False, "TWILIO_WHATSAPP_PHONE_NUMBER must be set when TWILIO_WHATSAPP_CONTENT_SID is provided"
        if self.whatsapp_phone_number and not _is_valid_e164(self.whatsapp_phone_number):
            return False, "TWILIO_WHATSAPP_PHONE_NUMBER must be valid E.164 (e.g. +15558015045)"
        if self.phone_number and not _is_valid_e164(self.phone_number):
            logger.warning("TWILIO_PHONE_NUMBER provided but not valid E.164")
        return True, None


class TwilioServiceError(Exception):
    pass

class TwilioConfigurationError(TwilioServiceError):
    pass

class TwilioMessageError(TwilioServiceError):
    def __init__(self, message: str, error_code: Optional[int] = None, original: Optional[Exception] = None):
        super().__init__(message)
        self.error_code = error_code
        self.original = original

# ---------- Service implementation ----------
class TwilioService:
    def __init__(self, config_obj: Optional[TwilioConfig] = None):
        self.config = config_obj or TwilioConfig.from_env()
        ok, msg = self.config.validate()
        if not ok:
            logger.error("Twilio configuration invalid: %s", msg)
            raise TwilioConfigurationError(msg)

        try:
            self.client = Client(self.config.account_sid, self.config.auth_token)
            logger.info("Twilio client initialized")
        except Exception as e:
            logger.exception("Failed to initialize Twilio client")
            raise TwilioConfigurationError("Failed to initialize Twilio client") from e

    # ---------- SMS OTP ----------
    def send_otp_sms(self, phone_number: str, otp_code: str) -> Tuple[bool, str, Dict[str, Any]]:
        try:
            if self.config.test_mode:
                logger.info("TEST MODE: OTP %s -> %s", otp_code, phone_number)
                return True, "TEST MODE simulated", {"to": phone_number, "otp": otp_code}

            normalized = _normalize_raw_phone(phone_number)
            if not _is_valid_e164(normalized):
                return False, "Invalid recipient phone number (E.164 required)", {"to": phone_number}

            body = f"Your Loopin verification code is: {otp_code}. This code expires in 10 minutes."

            params = {"body": body, "to": normalized}
            if self.config.messaging_service_sid_sms:
                params["messaging_service_sid"] = self.config.messaging_service_sid_sms
            else:
                from_num = self.config.phone_number or None
                if not from_num:
                    return False, "No SMS from number configured", {"to": normalized}
                params["from_"] = from_num

            message = self.client.messages.create(**params)
            logger.info("OTP SMS created SID=%s to=%s status=%s", getattr(message, "sid", None), normalized, getattr(message, "status", None))
            return True, "OTP queued/sent", {"sid": getattr(message, "sid", None), "status": getattr(message, "status", None)}
        except TwilioRestException as e:
            logger.exception("Twilio API error sending OTP SMS")
            return False, "Twilio API error sending SMS", {"error": str(e), "code": getattr(e, "code", None)}
        except Exception as e:
            logger.exception("Unexpected error sending OTP SMS")
            return False, "Unexpected error sending SMS", {"error": str(e)}

    # ---------- Verify OTP ----------
    def verify_otp(self, phone_number: str, otp_code: str) -> Tuple[bool, str, Dict[str, Any]]:
        try:
            if not self.config.verify_sid:
                return False, "Verify service not configured", {}
            normalized = _normalize_raw_phone(phone_number)
            if not _is_valid_e164(normalized):
                return False, "Invalid phone number format", {"to": phone_number}

            result = self.client.verify.v2.services(self.config.verify_sid).verification_checks.create(
                to=normalized,
                code=otp_code
            )
            status = getattr(result, "status", None)
            if status == "approved":
                logger.info("OTP verified for %s", normalized)
                return True, "OTP verified", {"status": status}
            logger.warning("OTP verification failed for %s status=%s", normalized, status)
            return False, "Invalid OTP", {"status": status}
        except TwilioRestException as e:
            logger.exception("Twilio Verify API error")
            return False, "Twilio Verify error", {"error": str(e), "code": getattr(e, "code", None)}
        except Exception as e:
            logger.exception("Unexpected error verifying OTP")
            return False, "Unexpected verify error", {"error": str(e)}

    # ---------- WhatsApp sending (template-first) ----------
    def send_whatsapp_message(
        self,
        phone_number: str,
        *,
        content_sid: Optional[str] = None,
        content_variables: Optional[Dict[str, Any]] = None,
        message_body: Optional[str] = None,
        from_number: Optional[str] = None,
        retry_on_transient: int = 1
    ) -> Tuple[bool, str, Dict[str, Any]]:
        try:
            if self.config.test_mode:
                logger.info("TEST MODE: simulate WhatsApp send to %s", phone_number)
                return True, "TEST MODE simulated", {"to": phone_number, "content_sid": content_sid, "content_variables": content_variables or {}}

            normalized = _normalize_raw_phone(phone_number)
            if not _is_valid_e164(normalized):
                return False, "Invalid recipient phone number (E.164 required)", {"to": phone_number}

            whatsapp_to = _whatsapp_prefix(normalized)
            final_content_sid = content_sid or self.config.whatsapp_content_sid

            if not final_content_sid:
                if not self.config.allow_plaintext_when_session_open:
                    return False, "Plain-text WhatsApp outbound to cold users is disallowed in production. Use content_sid (template) instead.", {"to": whatsapp_to}
                if not message_body or not message_body.strip():
                    return False, "Empty message body", {"to": whatsapp_to}

            params: Dict[str, Any] = {"to": whatsapp_to}
            if self.config.messaging_service_sid_whatsapp and not from_number:
                params["messaging_service_sid"] = self.config.messaging_service_sid_whatsapp
            else:
                from_val = from_number or self.config.whatsapp_phone_number
                if not from_val:
                    return False, "WhatsApp sender not configured", {"to": whatsapp_to}
                from_norm = _normalize_raw_phone(from_val)
                if not _is_valid_e164(from_norm):
                    return False, "Invalid whatsapp_from configuration (E.164 required)", {"from": from_val}
                params["from_"] = _whatsapp_prefix(from_norm)

            if final_content_sid:
                params["content_sid"] = final_content_sid
                if content_variables:
                    normalized_vars = {str(k): v for k, v in (content_variables or {}).items()}
                    params["content_variables"] = json.dumps(normalized_vars)
            else:
                params["body"] = message_body

            attempt = 0
            while True:
                attempt += 1
                try:
                    message = self.client.messages.create(**params)
                except TwilioRestException as e:
                    code = getattr(e, "code", None)
                    kind = _classify_error_code(code)
                    logger.warning("Twilio REST error sending WhatsApp to %s code=%s class=%s attempt=%d err=%s", whatsapp_to, code, kind, attempt, str(e))
                    if kind == "transient" and attempt <= retry_on_transient:
                        time.sleep(1)
                        continue
                    return False, "Twilio API error sending WhatsApp message", {"error": str(e), "code": code, "params": params}

                msg_status = getattr(message, "status", None)
                error_code = getattr(message, "error_code", None)
                details = {
                    "sid": getattr(message, "sid", None),
                    "status": msg_status,
                    "error_code": error_code,
                    "to": whatsapp_to,
                    "content_sid": final_content_sid,
                    "params": params,
                }

                if msg_status in ("failed", "undelivered"):
                    kind = _classify_error_code(error_code)
                    human = self._handle_whatsapp_error(error_code, msg_status)
                    logger.warning("WhatsApp undelivered to %s sid=%s status=%s code=%s kind=%s", whatsapp_to, details["sid"], msg_status, error_code, kind)
                    if kind == "transient" and attempt <= retry_on_transient:
                        time.sleep(1)
                        continue
                    return False, human, details

                if msg_status in ("queued", "sending", "sent", "delivered", "read", "accepted", None):
                    logger.info("WhatsApp message accepted to %s sid=%s status=%s", whatsapp_to, details["sid"], msg_status)
                    return True, "WhatsApp message accepted by Twilio", details

                logger.info("WhatsApp returned status %s for %s sid=%s", msg_status, whatsapp_to, details["sid"])
                return True, f"WhatsApp message created with status {msg_status}", details

        except Exception as exc:
            logger.exception("Unexpected error in send_whatsapp_message")
            return False, "Unexpected error sending WhatsApp message", {"error": str(exc)}

    def _handle_whatsapp_error(self, error_code: Optional[int], status: str) -> str:
        mapping = {
            63016: "Recipient has not opted in to receive WhatsApp messages (user must message your number to opt in)",
            63007: "Invalid WhatsApp number or not registered on WhatsApp",
            63014: "WhatsApp message template not approved or invalid",
            63024: "WhatsApp message blocked (likely not opted-in or template misuse)",
            21211: "Invalid phone number (wrong format or non-existent)",
            21656: "Invalid or empty message payload",
        }
        if error_code in mapping:
            base = mapping[error_code]
            if error_code == 63016:
                return f"{base}. User must send a message to your WhatsApp sender to create a session/opt-in."
            return base
        return f"Message delivery failed with status {status} (error_code={error_code})"

# Singleton accessor
_twilio_service_instance: Optional[TwilioService] = None

def get_twilio_service() -> TwilioService:
    global _twilio_service_instance
    if _twilio_service_instance is None:
        _twilio_service_instance = TwilioService()
    return _twilio_service_instance

# Module-level singleton instance for convenience
twilio_service = get_twilio_service()
