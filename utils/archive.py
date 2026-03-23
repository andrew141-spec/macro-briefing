import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

"""
Archive Manager
Stores and retrieves briefings from a local JSON file.
On Streamlit Cloud, use st.session_state as the runtime cache
and a local file for persistence within the session.
"""

import json
import os
from datetime import datetime
from pathlib import Path

ARCHIVE_FILE = Path("data/briefings_archive.json")


def _load_archive() -> list:
    """Load archive from disk. Returns empty list if not found."""
    try:
        ARCHIVE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if ARCHIVE_FILE.exists():
            with open(ARCHIVE_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _save_archive(archive: list):
    """Persist archive to disk."""
    try:
        ARCHIVE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ARCHIVE_FILE, "w") as f:
            json.dump(archive, f, indent=2)
    except Exception:
        pass


def save_briefing(briefing_result: dict) -> list:
    """
    Save a new briefing result to the archive.
    briefing_result must contain: session, date_str, briefing, generated_at
    Returns updated archive.
    """
    archive = _load_archive()

    entry = {
        "id":           f"{briefing_result['date_str']}_{briefing_result['session']}".replace(" ", "_").replace(",", ""),
        "session":      briefing_result.get("session", ""),
        "date_str":     briefing_result.get("date_str", ""),
        "generated_at": briefing_result.get("generated_at", ""),
        "briefing":     briefing_result.get("briefing", ""),
        "error":        briefing_result.get("error"),
    }

    # Deduplicate by id — replace if same session/date
    archive = [a for a in archive if a.get("id") != entry["id"]]
    archive.insert(0, entry)  # newest first

    # Keep last 90 briefings (30 days × 3 sessions)
    archive = archive[:90]
    _save_archive(archive)
    return archive


def load_archive() -> list:
    """Public: load full archive sorted newest-first."""
    return _load_archive()


def search_archive(query: str) -> list:
    """Simple text search across all briefings."""
    q = query.lower().strip()
    if not q:
        return load_archive()
    return [
        entry for entry in load_archive()
        if q in entry.get("briefing", "").lower()
        or q in entry.get("date_str", "").lower()
        or q in entry.get("session", "").lower()
    ]


def get_latest(n: int = 1) -> list:
    """Return the n most recent briefings."""
    return load_archive()[:n]


def format_archive_label(entry: dict) -> str:
    """Human-readable label for sidebar display."""
    return f"{entry.get('date_str', '')} — {entry.get('session', '')} ({entry.get('generated_at', '')})"
