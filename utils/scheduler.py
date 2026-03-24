import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

"""
Scheduler — updated schedule: 8:40 AM, 12:00 PM, 5:30 PM ET
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


def should_auto_generate(session, last_generated):
    if not session:
        return False
    now_et    = datetime.now(ET)
    today_str = now_et.strftime("%Y-%m-%d")
    return last_generated.get(session) != today_str


def mark_generated(session, last_generated):
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
        dt_today = now_et.replace(hour=start_time.hour, minute=start_time.minute, second=0, microsecond=0)
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
