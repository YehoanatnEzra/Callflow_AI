import os

# Twilio credentials (use environment variables if available)
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")  # add your Account_Sid
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")  # add you auth token

# Phone numbers
NUMBER_TWILIO = os.getenv("TWILIO_NUMBER", "") # add yout twilio number


__all__ = [
    "ACCOUNT_SID",
    "AUTH_TOKEN",
    "NUMBER_TWILIO",
    "YEHONATAN_NUMBER",
]


def using_env_vars():
    """Return True if both main Twilio creds are set in the environment."""
    return bool(os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_AUTH_TOKEN"))

