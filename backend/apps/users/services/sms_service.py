import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class SMSService:
    """Send OTP via Twilio in production; log to console in development."""

    @staticmethod
    def send_otp(phone_number: str, otp_code: str) -> bool:
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            return SMSService._send_via_twilio(phone_number, otp_code)
        logger.info("DEV OTP for %s: %s", phone_number, otp_code)
        print(f"\n{'='*40}\nOTP for {phone_number}: {otp_code}\n{'='*40}\n")
        return True

    @staticmethod
    def _send_via_twilio(phone_number: str, otp_code: str) -> bool:
        try:
            from twilio.rest import Client

            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            client.messages.create(
                body=f"Your ChatApp verification code is: {otp_code}. Valid for {settings.OTP_EXPIRY_MINUTES} minutes.",
                from_=settings.TWILIO_PHONE_NUMBER,
                to=phone_number,
            )
            return True
        except Exception as exc:
            logger.exception("Failed to send SMS: %s", exc)
            return False
