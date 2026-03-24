import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

"""
Scheduler — session windows: 8:40 AM, 12:00 PM, 5:30 PM ET
Bug fix: should_auto_generate now checks the on-disk archive so page reloads
         never trigger a duplicate generation for an already-completed session.
"""

from datetime import datetime, time
import pytz

ET = pytz.timezone("America/New_York")

SESSION_WINDOWS = {
    "Morning": (time(8, 40),  time(10, 30)),
    "Midday":  (time(12, 0),  time(13, 30)),
    "Closing": (time(17, 30), time(19, 0)),
}

SESSION_LABELS = {
    "Morning": "Pre-Market Morning Briefing",
    "Midday":  "Midday Desk Update",
    "Closing": "After-Hours Closing Note",
}

SESSION_ICONS = {
    "Morning": "🌅",
    "Midday":  "🌞",
    "Closing": "🌆",
}


def current_session_et():
    now_et = datetime.now(ET)
    t = now_et.time().replace(second=0, microsecond=0)
    for session, (start, end) in SESSION_WINDOWS.items():
        if start <= t <= end:
            return session, now_et
    return None, now_et


def _archive_has_briefing_for(session: str, date_str: str) -> bool:
    """
    Check the on-disk archive to see if a briefing already exists
    for this session + date. This is the source of truth — not session_state.
    """
    try:
        from utils.archive import load_archive
        archive = load_archive()
        for entry in archive:
            if entry.get("session") == session and entry.get("date_str") == date_str:
                return True
    except Exception:
        pass
    return False


def should_auto_generate(session: str, last_generated: dict) -> bool:
    """
    Returns True only if BOTH conditions are met:
    1. session_state has no record of generating this session today, AND
    2. The on-disk archive has no briefing for this session + today's date.

    Condition 2 is the persistent check — it survives page reloads.
    Condition 1 is the fast in-memory check that avoids a disk read when possible.
    """
    if not session:
        return False

    now_et    = datetime.now(ET)
    today_str = now_et.strftime("%Y-%m-%d")

    # Fast path: session_state already recorded this session today
    if last_generated.get(session) == today_str:
        return False

    # Slow path: check the archive on disk (survives reloads)
    date_display = now_et.strftime("%B %d, %Y").replace(" 0", " ")
    if _archive_has_briefing_for(session, date_display):
        return False

    return True


def mark_generated(session: str, last_generated: dict) -> dict:
    now_et    = datetime.now(ET)
    today_str = now_et.strftime("%Y-%m-%d")
    last_generated[session] = today_str
    return last_generated


def next_session_info():
    now_et = datetime.now(ET)
    ordered = [
        ("Morning", SESSION_WINDOWS["Morning"][0]),
        ("Midday",  SESSION_WINDOWS["Midday"][0]),
        ("Closing", SESSION_WINDOWS["Closing"][0]),
    ]
    for session, start_time in ordered:
        dt_today = now_et.replace(
            hour=start_time.hour, minute=start_time.minute,
            second=0, microsecond=0
        )
        if dt_today > now_et:
            delta   = dt_today - now_et
            hours   = int(delta.seconds // 3600)
            minutes = int((delta.seconds % 3600) // 60)
            return {
                "session":    session,
                "label":      SESSION_LABELS[session],
                "icon":       SESSION_ICONS[session],
                "start_time": start_time.strftime("%I:%M %p ET"),
                "countdown":  f"{hours}h {minutes}m",
            }
    return {
        "session":    "Morning",
        "label":      SESSION_LABELS["Morning"],
        "icon":       SESSION_ICONS["Morning"],
        "start_time": "8:40 AM ET (tomorrow)",
        "countdown":  "Next trading day",
    }
