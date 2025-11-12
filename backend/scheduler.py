import json
import logging
from datetime import datetime, timedelta, time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Meeting log stays at project root
BASE_DIR = Path(__file__).resolve().parent.parent
# Centralized location for persistent JSON logs
MEETING_LOG_PATH = BASE_DIR / "db" / "data" / "meetings_log.json"


def load_meetings() -> List[Dict[str, Any]]:
    if not MEETING_LOG_PATH.exists():
        MEETING_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        return []
    try:
        with MEETING_LOG_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
            if isinstance(data, list):
                return data
    except (json.JSONDecodeError, OSError):
        logger.warning("Could not load meetings log; starting fresh.")
    return []


def write_meetings(entries: List[Dict[str, Any]]) -> None:
    try:
        MEETING_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with MEETING_LOG_PATH.open("w", encoding="utf-8") as handle:
            json.dump(entries, handle, indent=2, ensure_ascii=False)
    except OSError:
        logger.exception("Failed to persist meetings log")


def append_meeting(entry: Dict[str, Any]) -> None:
    entries = load_meetings()
    entries.append(entry)
    write_meetings(entries)


def generate_available_slots(booked: Optional[Dict[str, Any]] = None, days: int = 14) -> List[str]:
    booked_set = set(booked or [])
    now = datetime.now()
    slots: List[str] = []
    for offset in range(days):
        day = now + timedelta(days=offset)
        weekday = day.weekday()  # Monday=0, Sunday=6
        if weekday not in {6, 0, 1, 2, 3}:  # Sunday (6) through Thursday (3)
            continue
        for hour in range(8, 16):  # 08:00 through 15:00 start times
            slot_dt = datetime.combine(day.date(), time(hour, 0))
            if slot_dt <= now:
                continue
            slot_str = slot_dt.strftime("%Y-%m-%d %H:%M")
            if slot_str not in booked_set:
                slots.append(slot_str)
    return slots


def format_slot(slot_str: str) -> str:
    try:
        parsed = datetime.strptime(slot_str, "%Y-%m-%d %H:%M")
        return parsed.strftime("%A, %B %d at %I:%M %p")
    except ValueError:
        return slot_str


def ensure_proposed_slots(session: Dict[str, Any], batch: int = 2) -> List[str]:
    proposed = session.get("proposed_slots")
    if proposed:
        return proposed
    slots: List[str] = session.get("available_slots", [])
    index = session.get("slot_index", 0)
    if index >= len(slots):
        return []
    new_proposed = slots[index : index + batch]
    session["proposed_slots"] = new_proposed
    session["slot_index"] = index
    return new_proposed


def advance_slot_options(session: Dict[str, Any], step: Optional[int] = None) -> None:
    current = session.get("slot_index", 0)
    step = step or max(1, len(session.get("proposed_slots", [])) or 1)
    session["slot_index"] = current + step
    session["proposed_slots"] = []


def register_scheduled_slot(session: Dict[str, Any], slot: str) -> None:
    session["scheduled_slot"] = slot
    session["available_slots"] = [s for s in session.get("available_slots", []) if s != slot]
    session["proposed_slots"] = []


def log_meeting_if_needed(session: Dict[str, Any], call_sid: str) -> None:
    if session.get("meeting_logged"):
        return
    slot = session.get("scheduled_slot")
    if not slot:
        return
    entry = {
        "call_sid": call_sid,
        "slot": slot,
        "prospect_number": session.get("prospect_number"),
        "twilio_number": session.get("twilio_number"),
        "logged_at": datetime.utcnow().isoformat(),
    }
    append_meeting(entry)
    session["meeting_logged"] = True


def get_booked_slots() -> List[str]:
    """Return the list of slot strings currently booked in the meetings log."""
    entries = load_meetings()
    slots: List[str] = []
    for e in entries:
        s = e.get("slot")
        if isinstance(s, str):
            slots.append(s)
    return slots


def is_slot_available(slot_str: str, days: int = 14) -> bool:
    """Check whether a given slot string (YYYY-MM-DD HH:MM) is available within the next `days` days
    and falls inside the allowed window (Sunday-Thursday, 08:00-16:00).
    """
    try:
        # Validate format
        parsed = datetime.strptime(slot_str, "%Y-%m-%d %H:%M")
    except ValueError:
        return False

    # Exclude past
    if parsed <= datetime.now():
        return False

    # Check allowed weekdays: Sunday(6) through Thursday(3)
    if parsed.weekday() not in {6, 0, 1, 2, 3}:
        return False

    # Allowed start hours are 08:00-15:00 (last allowed start at 15:00)
    if not (8 <= parsed.hour <= 15):
        return False

    # Check within window days
    available = generate_available_slots(booked=get_booked_slots(), days=days)
    return slot_str in available


def book_slot(entry: Dict[str, Any]) -> bool:
    """Attempt to book a slot described by `entry`.

    Expected entry keys: 'slot' (YYYY-MM-DD HH:MM), plus any metadata (email, name, call_sid...).
    Returns True if booking succeeded (and was persisted), False if slot was already taken or invalid.
    """
    slot = entry.get("slot")
    if not isinstance(slot, str):
        return False

    if not is_slot_available(slot):
        return False

    # Persist meeting with metadata and server timestamp
    to_append = dict(entry)
    to_append["logged_at"] = datetime.utcnow().isoformat()
    append_meeting(to_append)
    return True


def update_meeting(slot: str, call_sid: Optional[str] = None, updates: Optional[Dict[str, Any]] = None) -> bool:
    """Update meeting entries matching slot (and optionally call_sid) with keys from updates.

    Returns True if at least one entry was updated and persisted.
    """
    if updates is None:
        return False
    entries = load_meetings()
    changed = False
    for e in entries:
        if e.get("slot") == slot and (call_sid is None or e.get("call_sid") == call_sid):
            e.update(updates)
            changed = True
    if changed:
        write_meetings(entries)
    return changed
