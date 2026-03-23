import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

"""
Scheduler
Determines whether a new briefing should be auto-generated
based on ET session windows. Uses Streamlit session state
to avoid duplicate generation within a session window.
"""

from datetime import datetime, time
import pytz

ET = pytz.timezone("America/New_York")

# Session windows (ET) — outside these windows no auto-generation
SESSION_WINDOWS = {
    "Morning": (time(6, 0),  time(9, 30)),   # 6:00–9:30 AM ET
    "Midday":  (time(12, 0), time(13, 30)),  # 12:00–1:30 PM ET
    "Closing": (time(16, 0), time(18, 0)),   # 4:00–6:00 PM ET
}

SESSION_LABELS = {
    "Morning": "Pre-Market Morning Briefing",
    "Midday":  "Midday Lunch Update",
    "Closing": "Post-Market Closing Briefing",
}

SESSION_ICONS = {
    "Morning": "🌅",
    "Midday":  "🌞",
    "Closing": "🌆",
}


def current_session_et() -> tuple[str | None, datetime]:
    """
    Returns (session_name, now_et).
    session_name is None if we're between sessions.
    """
    now_et = datetime.now(ET)
    t = now_et.time().replace(second=0, microsecond=0)

    for session, (start, end) in SESSION_WINDOWS.items():
        if start <= t <= end:
            return session, now_et

    return None, now_et


def should_auto_generate(session: str, last_generated: dict) -> bool:
    """
    Returns True if the current session hasn't been generated yet today.
    last_generated: dict mapping session → date string (YYYY-MM-DD)
    """
    if not session:
        return False
    now_et    = datetime.now(ET)
    today_str = now_et.strftime("%Y-%m-%d")
    last_date = last_generated.get(session)
    return last_date != today_str


def mark_generated(session: str, last_generated: dict) -> dict:
    """Record that a session was generated today."""
    now_et    = datetime.now(ET)
    today_str = now_et.strftime("%Y-%m-%d")
    last_generated[session] = today_str
    return last_generated


def next_session_info() -> dict:
    """
    Returns info about the next upcoming session for countdown display.
    """
    now_et = datetime.now(ET)
    t = now_et.time()

    ordered = [
        ("Morning", SESSION_WINDOWS["Morning"][0]),
        ("Midday",  SESSION_WINDOWS["Midday"][0]),
        ("Closing", SESSION_WINDOWS["Closing"][0]),
    ]

    for session, start_time in ordered:
        dt_today = now_et.replace(
            hour=start_time.hour,
            minute=start_time.minute,
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

    # All sessions passed today — show tomorrow's morning
    return {
        "session":    "Morning",
        "label":      SESSION_LABELS["Morning"],
        "icon":       SESSION_ICONS["Morning"],
        "start_time": "6:00 AM ET (tomorrow)",
        "countdown":  "Next trading day",
    }
