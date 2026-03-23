"""
Macro Market Briefing — Institutional-Quality Sell-Side Desk Notes
Powered by Claude AI + Yahoo Finance (+ Alpha Vantage fallback)
"""

import streamlit as st
import time
from datetime import datetime
import pytz

# ─── PAGE CONFIG (must be first Streamlit call) ───────────────────────────────
st.set_page_config(
    page_title="Macro Market Briefing",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── LOCAL IMPORTS ────────────────────────────────────────────────────────────
from utils.briefing_generator import generate_briefing, get_session
from utils.archive import save_briefing, load_archive, search_archive, format_archive_label
from utils.scheduler import (
    current_session_et, should_auto_generate, mark_generated,
    next_session_info, SESSION_LABELS, SESSION_ICONS
)

ET = pytz.timezone("America/New_York")

# ─── CUSTOM CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Global typography ── */
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
}

/* ── Header bar ── */
.macro-header {
    background: linear-gradient(135deg, #0a0f1e 0%, #0d1a2e 60%, #0f2040 100%);
    border-bottom: 2px solid #1a3a5c;
    padding: 1.5rem 2rem 1.2rem;
    margin: -1rem -1rem 1.5rem -1rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.macro-header h1 {
    color: #e8f0fe;
    font-size: 1.5rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    margin: 0;
}
.macro-header .subtitle {
    color: #6b9ed2;
    font-size: 0.78rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-top: 0.2rem;
}
.live-dot {
    display: inline-block;
    width: 8px; height: 8px;
    background: #00d4aa;
    border-radius: 50%;
    margin-right: 6px;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}

/* ── Session badge ── */
.session-badge {
    display: inline-block;
    padding: 0.3rem 0.85rem;
    border-radius: 3px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}
.badge-morning { background: #1a3a5c; color: #74b9ff; border: 1px solid #2d5a8c; }
.badge-midday  { background: #2d3a1a; color: #a8e063; border: 1px solid #4a6a2a; }
.badge-closing { background: #3a1a2d; color: #f38ba8; border: 1px solid #6a2a4a; }

/* ── Section headers ── */
.section-header {
    background: #0d1a2e;
    border-left: 3px solid #1e6bb0;
    padding: 0.5rem 0.8rem;
    margin: 1.5rem 0 0.8rem 0;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #6b9ed2;
}

/* ── Briefing text container ── */
.briefing-body {
    background: #080e1a;
    border: 1px solid #1a2a3a;
    border-radius: 4px;
    padding: 2rem 2.5rem;
    font-size: 0.94rem;
    line-height: 1.75;
    color: #ccd6f6;
    white-space: pre-wrap;
    font-family: 'IBM Plex Sans', sans-serif;
}

/* ── Market ticker strip ── */
.ticker-strip {
    background: #080e1a;
    border: 1px solid #1a2a3a;
    border-radius: 4px;
    padding: 0.8rem 1rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.8rem;
}
.ticker-pos { color: #00d4aa; }
.ticker-neg { color: #f38ba8; }
.ticker-neu { color: #8899aa; }

/* ── Stat boxes ── */
.stat-box {
    background: #0d1a2e;
    border: 1px solid #1a3a5c;
    border-radius: 4px;
    padding: 0.9rem 1rem;
    text-align: center;
}
.stat-label { font-size: 0.68rem; color: #6b9ed2; text-transform: uppercase; letter-spacing: 0.1em; }
.stat-value { font-size: 1.1rem; font-weight: 600; color: #e8f0fe; font-family: 'IBM Plex Mono', monospace; }
.stat-chg-pos { font-size: 0.78rem; color: #00d4aa; }
.stat-chg-neg { font-size: 0.78rem; color: #f38ba8; }

/* ── Archive item ── */
.archive-item {
    background: #0d1a2e;
    border: 1px solid #1a3a5c;
    border-radius: 4px;
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.5rem;
    cursor: pointer;
    transition: border-color 0.2s;
}
.archive-item:hover { border-color: #1e6bb0; }

/* ── Next session countdown ── */
.countdown-box {
    background: #080e1a;
    border: 1px solid #1a3a5c;
    border-radius: 4px;
    padding: 0.8rem 1rem;
    text-align: center;
    font-size: 0.78rem;
    color: #6b9ed2;
}
.countdown-time {
    font-size: 1.2rem;
    font-weight: 600;
    color: #74b9ff;
    font-family: 'IBM Plex Mono', monospace;
}

/* ── Sidebar styling ── */
[data-testid="stSidebar"] {
    background: #060c16 !important;
    border-right: 1px solid #1a2a3a;
}
[data-testid="stSidebar"] * { color: #ccd6f6 !important; }

/* ── Buttons ── */
.stButton > button {
    background: #0d2a4a;
    color: #74b9ff;
    border: 1px solid #1e6bb0;
    border-radius: 3px;
    font-weight: 600;
    font-size: 0.82rem;
    letter-spacing: 0.05em;
    transition: all 0.2s;
    width: 100%;
}
.stButton > button:hover {
    background: #1a3a5c;
    border-color: #74b9ff;
}

/* ── Spinner ── */
.stSpinner > div { border-top-color: #1e6bb0 !important; }

/* ── Divider ── */
hr { border-color: #1a2a3a; }

/* ── Error / warning ── */
.error-box {
    background: #2d0a0f;
    border: 1px solid #6a1a2a;
    border-radius: 4px;
    padding: 0.8rem 1rem;
    color: #f38ba8;
    font-size: 0.82rem;
}
</style>
""", unsafe_allow_html=True)


# ─── SESSION STATE INIT ───────────────────────────────────────────────────────
def init_state():
    defaults = {
        "briefings":       [],       # list of result dicts (current session)
        "current_briefing": None,    # currently displayed briefing
        "last_generated":  {},       # {session: date_str} to avoid duplicates
        "api_key_set":     False,
        "auto_check_done": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ─── HELPERS ─────────────────────────────────────────────────────────────────
def get_session_badge(session: str) -> str:
    cls = {"Morning": "badge-morning", "Midday": "badge-midday", "Closing": "badge-closing"}.get(session, "badge-morning")
    icon = SESSION_ICONS.get(session, "📋")
    return f'<span class="session-badge {cls}">{icon} {session}</span>'


def render_ticker_strip(market_data_raw: dict):
    """Render a compact market data strip from raw snapshot."""
    if not market_data_raw:
        return

    items = [
        ("S&P",   market_data_raw.get("SP500",  {})),
        ("NDX",   market_data_raw.get("NASDAQ", {})),
        ("DOW",   market_data_raw.get("DOW",    {})),
        ("VIX",   market_data_raw.get("VIX",    {})),
        ("WTI",   market_data_raw.get("WTI",    {})),
        ("BRENT", market_data_raw.get("BRENT",  {})),
        ("GOLD",  market_data_raw.get("GOLD",   {})),
        ("DXY",   market_data_raw.get("DXY",    {})),
        ("BTC",   market_data_raw.get("BTC",    {})),
        ("10Y",   market_data_raw.get("US10Y",  {})),
        ("2Y",    market_data_raw.get("US2Y",   {})),
    ]

    cols = st.columns(len(items))
    for col, (label, d) in zip(cols, items):
        if d and d.get("price") is not None:
            price = d["price"]
            chg   = d.get("pct_chg", 0) or 0
            sign  = "+" if chg >= 0 else ""
            color = "#00d4aa" if chg >= 0 else "#f38ba8"
            col.markdown(
                f"""<div class="stat-box">
                    <div class="stat-label">{label}</div>
                    <div class="stat-value">{price:,.2f}</div>
                    <div style="color:{color};font-size:0.75rem;font-weight:600;">{sign}{chg:.2f}%</div>
                </div>""",
                unsafe_allow_html=True
            )


def run_generation(session_override: str = None):
    """Core generation pipeline — called from both auto and manual triggers."""
    groq_key = st.secrets.get("GROQ_API_KEY", "")
    av_key   = st.secrets.get("ALPHA_VANTAGE_KEY", "")

    if not groq_key:
        st.error("GROQ_API_KEY not found in Streamlit secrets. Add it in App Settings → Secrets. Get a free key at console.groq.com")
        return

    with st.spinner("Fetching live market data and generating briefing..."):
        result = generate_briefing(
            groq_api_key=groq_key,
            alpha_vantage_key=av_key,
            force_session=session_override,
        )

    if result.get("briefing"):
        save_briefing(result)
        st.session_state["current_briefing"] = result
        st.session_state["last_generated"] = mark_generated(
            result["session"], st.session_state["last_generated"]
        )
        st.success(f"Briefing generated — {result['session']} | {result['generated_at']}")
    else:
        st.error(f"Generation failed: {result.get('error', 'Unknown error')}")


# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📊 Macro Desk")
    st.markdown("---")

    # Next session countdown
    nxt = next_session_info()
    st.markdown(
        f"""<div class="countdown-box">
            <div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.1em;">Next Session</div>
            <div style="margin:0.3rem 0;">{nxt['icon']} {nxt['label']}</div>
            <div class="countdown-time">{nxt['countdown']}</div>
            <div style="font-size:0.68rem;margin-top:0.2rem;">{nxt['start_time']}</div>
        </div>""",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # Manual generation
    st.markdown("**Generate Briefing**")
    session_choice = st.selectbox(
        "Session",
        options=["Auto-detect", "Morning", "Midday", "Closing"],
        label_visibility="collapsed"
    )

    if st.button("Generate Now", use_container_width=True):
        override = None if session_choice == "Auto-detect" else session_choice
        run_generation(session_override=override)
        st.rerun()

    st.markdown("---")

    # Archive search
    st.markdown("**Briefing Archive**")
    search_q = st.text_input("Search briefings", placeholder="e.g. Fed, inflation, oil...", label_visibility="collapsed")

    archive = search_archive(search_q) if search_q else load_archive()

    if archive:
        labels = [format_archive_label(e) for e in archive]
        selected_label = st.selectbox(
            "Past briefings",
            options=labels,
            label_visibility="collapsed"
        )
        if selected_label:
            idx = labels.index(selected_label)
            if st.button("Load Selected", use_container_width=True):
                entry = archive[idx]
                st.session_state["current_briefing"] = {
                    "session":         entry.get("session", ""),
                    "date_str":        entry.get("date_str", ""),
                    "generated_at":    entry.get("generated_at", ""),
                    "briefing":        entry.get("briefing", ""),
                    "market_data_raw": {},
                }
                st.rerun()
    else:
        st.caption("No briefings in archive yet.")

    st.markdown("---")
    st.caption("Auto-generates at 6 AM / 12 PM / 4 PM ET")
    st.caption(f"ET: {datetime.now(ET).strftime('%I:%M %p')}")


# ─── AUTO-GENERATION CHECK ────────────────────────────────────────────────────
# Runs once per app load — checks if we're in a session window and haven't generated yet
if not st.session_state["auto_check_done"]:
    session_now, now_et = current_session_et()
    if session_now and should_auto_generate(session_now, st.session_state["last_generated"]):
        st.info(f"Auto-generating {session_now} briefing for {now_et.strftime('%B %d, %Y')}...")
        run_generation(session_override=session_now)
    st.session_state["auto_check_done"] = True


# ─── MAIN CONTENT ─────────────────────────────────────────────────────────────

# Header
now_et   = datetime.now(ET)
date_disp = now_et.strftime("%A, %B %d, %Y")
time_disp = now_et.strftime("%I:%M %p ET")

st.markdown(
    f"""<div class="macro-header">
        <div>
            <h1><span class="live-dot"></span>Macro Market Briefing</h1>
            <div class="subtitle">Institutional Sell-Side Desk | Powered by Groq + Live News</div>
        </div>
        <div style="text-align:right;">
            <div style="color:#6b9ed2;font-size:0.8rem;">{date_disp}</div>
            <div style="color:#8899aa;font-size:0.72rem;">{time_disp}</div>
        </div>
    </div>""",
    unsafe_allow_html=True
)

briefing = st.session_state.get("current_briefing")

if briefing and briefing.get("briefing"):
    session  = briefing.get("session", "")
    date_str = briefing.get("date_str", "")
    gen_at   = briefing.get("generated_at", "")
    mkt_raw  = briefing.get("market_data_raw", {})

    # Meta row
    col1, col2, col3 = st.columns([2, 2, 3])
    with col1:
        st.markdown(get_session_badge(session), unsafe_allow_html=True)
    with col2:
        st.markdown(f'<span style="color:#8899aa;font-size:0.8rem;">{date_str}</span>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<span style="color:#4a6a8a;font-size:0.75rem;">Generated: {gen_at}</span>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Ticker strip
    if mkt_raw:
        st.markdown('<div class="section-header">Live Market Snapshot</div>', unsafe_allow_html=True)
        render_ticker_strip(mkt_raw)
        st.markdown("<br>", unsafe_allow_html=True)

    # News headlines expander
    news_headlines = briefing.get("news_headlines", [])
    if news_headlines:
        with st.expander(f"📰 Live News Input ({len(news_headlines)} headlines used to generate this briefing)", expanded=False):
            st.markdown('<div style="font-size:0.75rem;color:#6b9ed2;margin-bottom:0.5rem;">These are the real headlines injected into the AI prompt. The briefing is grounded in these events.</div>', unsafe_allow_html=True)
            for i, h in enumerate(news_headlines, 1):
                src   = h.get("source", "")
                title = h.get("title", "")
                summ  = h.get("summary", "")
                st.markdown(
                    f'<div style="padding:0.4rem 0;border-bottom:1px solid #1a2a3a;font-size:0.8rem;">'
                    f'<span style="color:#4a6a8a;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.08em;">{i:02d}. {src}</span><br>'
                    f'<span style="color:#ccd6f6;">{title}</span>'
                    + (f'<br><span style="color:#8899aa;font-size:0.75rem;">{summ[:180]}</span>' if summ and summ != title else "")
                    + '</div>',
                    unsafe_allow_html=True
                )
        st.markdown("<br>", unsafe_allow_html=True)

    # Briefing body
    st.markdown('<div class="section-header">Desk Note</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="briefing-body">{briefing["briefing"]}</div>',
        unsafe_allow_html=True
    )

    # Download
    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button(
        label="Download Briefing (.txt)",
        data=briefing["briefing"],
        file_name=f"macro_briefing_{date_str.replace(', ','_').replace(' ','_')}_{session}.txt",
        mime="text/plain",
    )

else:
    # Empty state
    st.markdown(
        """<div style="text-align:center;padding:4rem 2rem;color:#4a6a8a;">
            <div style="font-size:2.5rem;margin-bottom:1rem;">📋</div>
            <div style="font-size:1rem;font-weight:500;color:#6b9ed2;margin-bottom:0.5rem;">No briefing loaded</div>
            <div style="font-size:0.82rem;">Use the sidebar to generate a briefing or load one from the archive.</div>
            <div style="font-size:0.78rem;margin-top:0.5rem;color:#3a5a7a;">
                Auto-generation triggers at 6:00 AM, 12:00 PM, and 4:00 PM ET.
            </div>
        </div>""",
        unsafe_allow_html=True
    )

    # Show archive preview if briefings exist
    archive = load_archive()
    if archive:
        st.markdown('<div class="section-header">Recent Briefings</div>', unsafe_allow_html=True)
        for entry in archive[:3]:
            badge = get_session_badge(entry.get("session",""))
            preview = entry.get("briefing","")[:280].replace("<","&lt;")
            st.markdown(
                f"""<div class="archive-item">
                    {badge}
                    <span style="font-size:0.75rem;color:#6b9ed2;margin-left:0.5rem;">{entry.get('date_str','')} — {entry.get('generated_at','')}</span>
                    <div style="font-size:0.8rem;color:#8899aa;margin-top:0.5rem;line-height:1.5;">{preview}...</div>
                </div>""",
                unsafe_allow_html=True
            )
