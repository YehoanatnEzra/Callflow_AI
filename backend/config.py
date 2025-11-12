"""Centralized configuration loading and validation.

This module reads environment variables, provides convenient accessors,
and offers friendly diagnostics for missing required settings.
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple


"""NOTE:
Hard‑coding real credentials is discouraged. If you previously stored live Twilio
values in keys.py, move them into environment variables instead of placing them here.
Below we provide placeholder fallbacks so development doesn't silently break, but
they are intentionally non-functional.
Replace with proper environment variables before production use.
"""

# Required for voice server to run calls and LLM
REQUIRED_VARS = ["OPENAI_API_KEY", "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"]

# Optional but useful
OPTIONAL_VARS = ["TWILIO_NUMBER", "PUBLIC_BASE_URL", "FLASK_SECRET_KEY", "YEHONATAN_NUMBER"]

# Fallback resolution order for Twilio-related values:
# 1) Environment variables
# 2) keys.py constants (backward compatible)
# 3) Safe placeholders (non-functional)

# Start with placeholders
ACCOUNT_SID = "AC_PLACEHOLDER_ACCOUNT_SID"
AUTH_TOKEN = "TWILIO_AUTH_TOKEN_PLACEHOLDER"
TWILIO_NUMBER = "+10000000000"
YEHONATAN_NUMBER = "+00000000000"

# Override via keys.py if present
try:
    import keys as _keys  # type: ignore
    ACCOUNT_SID = getattr(_keys, "ACCOUNT_SID", ACCOUNT_SID)
    AUTH_TOKEN = getattr(_keys, "AUTH_TOKEN", AUTH_TOKEN)
    TWILIO_NUMBER = getattr(_keys, "NUMBER_TWILIO", TWILIO_NUMBER)
    YEHONATAN_NUMBER = getattr(_keys, "YEHONATAN_NUMBER", YEHONATAN_NUMBER)
except Exception:
    pass

# Finally, env overrides all
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", ACCOUNT_SID)
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", AUTH_TOKEN)
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER", TWILIO_NUMBER)
YEHONATAN_NUMBER = os.getenv("YEHONATAN_NUMBER", YEHONATAN_NUMBER)


def get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    """Return environment variable or default if missing/empty."""
    val = os.getenv(name)
    if val is None or val == "":
        return default
    return val


def read_all() -> Dict[str, Optional[str]]:
    keys = REQUIRED_VARS + OPTIONAL_VARS
    return {k: get_env(k) for k in keys}


def missing(required: Optional[List[str]] = None) -> List[str]:
    req = required or REQUIRED_VARS
    return [k for k in req if not get_env(k)]


def diagnostics() -> str:
    """Return a human-friendly diagnostic string of important variables."""
    cfg = read_all()
    lines = ["Configuration summary:", "(placeholders do NOT represent working credentials)"]
    for k in REQUIRED_VARS:
        v = cfg.get(k)
        lines.append(f"  {k}: {'SET' if v else 'MISSING'}")
    for k in OPTIONAL_VARS:
        v = cfg.get(k)
        lines.append(f"  {k}: {'SET' if v else 'not set'}")
    # Show which fallbacks are currently in effect
    lines.append("Twilio resolved values (env > keys.py > placeholder):")
    lines.append(f"  ACCOUNT_SID: {'SET(env)' if os.getenv('TWILIO_ACCOUNT_SID') else ('SET(keys.py)' if 'keys' in globals() else 'PLACEHOLDER')}")
    lines.append(f"  AUTH_TOKEN: {'SET(env)' if os.getenv('TWILIO_AUTH_TOKEN') else ('SET(keys.py)' if 'keys' in globals() else 'PLACEHOLDER')}")
    lines.append(f"  TWILIO_NUMBER: {'SET(env)' if os.getenv('TWILIO_NUMBER') else ('SET(keys.py)' if 'keys' in globals() else 'PLACEHOLDER')}")
    return "\n".join(lines)


def require(required: Optional[List[str]] = None) -> Tuple[bool, List[str]]:
    """Check required envs are present. Returns (ok, missing_list)."""
    miss = missing(required)
    return (len(miss) == 0, miss)


__all__ = [
    "get_env",
    "read_all",
    "missing",
    "diagnostics",
    "require",
    "REQUIRED_VARS",
    "OPTIONAL_VARS",
    # Fallback constants
    "ACCOUNT_SID",
    "AUTH_TOKEN",
    "TWILIO_NUMBER",
    "YEHONATAN_NUMBER",
]


if __name__ == "__main__":
    # Simple CLI to print diagnostics and return non-zero if required vars are missing
    print(diagnostics())
    ok, miss = require()
    if not ok:
        print(f"Missing required variables: {', '.join(miss)}")
        raise SystemExit(1)
    print("All required environment variables are set.")
    raise SystemExit(0)
