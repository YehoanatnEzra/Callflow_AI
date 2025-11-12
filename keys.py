import os

# Twilio credentials (use environment variables if available)
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "AC80205d6111f57aad69fd8c6bf831a81f")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "a94ae0bdc739d44fc27e05fa7fadb98b")

# Phone numbers
NUMBER_TWILIO = os.getenv("TWILIO_NUMBER", "+15187126855")
YEHONATAN_NUMBER = os.getenv("YEHONATAN_NUMBER", "+972546374390")

__all__ = [
    "ACCOUNT_SID",
    "AUTH_TOKEN",
    "NUMBER_TWILIO",
    "YEHONATAN_NUMBER",
]


def using_env_vars():
    """Return True if both main Twilio creds are set in the environment."""
    return bool(os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_AUTH_TOKEN"))
