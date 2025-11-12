import logging
import os
from typing import Optional

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from backend.config import get_env, ACCOUNT_SID, AUTH_TOKEN, TWILIO_NUMBER


logger = logging.getLogger("call_service")


class CallService:
    """Lightweight wrapper around the Twilio Voice API for outbound calls."""

    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_number: Optional[str] = None,
    ) -> None:
        # Prefer explicit args, then environment, then placeholder fallbacks from config
        self.account_sid = account_sid or get_env("TWILIO_ACCOUNT_SID") or ACCOUNT_SID
        self.auth_token = auth_token or get_env("TWILIO_AUTH_TOKEN") or AUTH_TOKEN
        self.from_number = from_number or get_env("TWILIO_NUMBER") or TWILIO_NUMBER

        if not (self.account_sid and self.auth_token and self.from_number):
            raise RuntimeError("Twilio credentials and outbound number must be configured.")

        self.client = Client(self.account_sid, self.auth_token)

    def make_call(self, to_number: str, webhook_url: str) -> str:
        """Create an outbound call and return the Twilio Call SID."""
        if not webhook_url.startswith("http"):
            raise ValueError("webhook_url must be an absolute http(s) URL that Twilio can reach")

        logger.info("Dialing %s from %s via %s", to_number, self.from_number, webhook_url)

        try:
            call = self.client.calls.create(
                to=to_number,
                from_=self.from_number,
                url=webhook_url,
                method="POST",
                status_callback=os.getenv("TWILIO_STATUS_CALLBACK"),
                status_callback_event=("initiated", "ringing", "answered", "completed"),
                status_callback_method="POST",
            )
        except TwilioRestException as exc:
            logger.error("Twilio call failed: %s", exc)
            raise

        logger.info("Call created with sid=%s", call.sid)
        return call.sid
