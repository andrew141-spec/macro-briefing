"""
Macro Market Briefing — Core Convexity Terminal Theme
"""

import streamlit as st
import time
from datetime import datetime
import pytz

st.set_page_config(
    page_title="Macro Market Briefing",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.briefing_generator import generate_briefing, get_session
from utils.archive import save_briefing, load_archive, search_archive, format_archive_label
from utils.scheduler import (
    current_session_et, should_auto_generate, mark_generated,
    next_session_info, SESSION_LABELS, SESSION_ICONS
)

ET = pytz.timezone("America/New_York")

# ─── CORE CONVEXITY TERMINAL CSS ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&family=Space+Grotesk:wght@300;400;500;600;700&display=swap');

:root {
    --bg-void:      #060608;
    --bg-deep:      #0a0a0e;
    --bg-panel:     #0e0e14;
    --bg-card:      #12121a;
    --bg-hover:     #16161f;
    --border-dim:   #1c1c2a;
    --border-med:   #252535;
    --border-bright:#333350;
    --accent-gold:  #f5a623;
    --accent-amber: #e8930d;
    --text-primary: #e8e8f0;
    --text-secondary:#8888aa;
    --text-dim:     #444460;
    --green:        #00d4aa;
    --red:          #f05060;
    --blue:         #4488ff;
    --yellow:       #f5c842;
    --mono:         'JetBrains Mono', monospace;
    --sans:         'Space Grotesk', sans-serif;
}

html, body, [class*="css"] {
    font-family: var(--sans);
    background: var(--bg-void) !important;
    color: var(--text-primary);
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0 1.5rem 2rem 1.5rem !important; max-width: 100% !important; }

/* ── TOP HEADER BAR ── */
.cc-header {
    background: var(--bg-deep);
    border-bottom: 1px solid var(--border-dim);
    padding: 0.85rem 1.5rem;
    margin: -1rem -1.5rem 1.5rem -1.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.cc-header-left {
    display: flex;
    align-items: center;
    gap: 1.2rem;
}
.cc-logo {
    font-family: var(--mono);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--accent-gold);
    border: 1px solid var(--accent-gold);
    padding: 0.25rem 0.6rem;
    border-radius: 2px;
}
.cc-title {
    font-family: var(--mono);
    font-size: 0.82rem;
    font-weight: 500;
    color: var(--text-secondary);
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
.cc-divider-v {
    width: 1px;
    height: 18px;
    background: var(--border-dim);
}
.cc-header-right {
    display: flex;
    align-items: center;
    gap: 1.5rem;
}
.cc-time {
    font-family: var(--mono);
    font-size: 0.78rem;
    color: var(--text-secondary);
    text-align: right;
}
.cc-time .date { color: var(--text-dim); font-size: 0.68rem; }
.live-dot {
    display: inline-block;
    width: 6px; height: 6px;
    background: var(--green);
    border-radius: 50%;
    margin-right: 5px;
    animation: blink 2s infinite;
}
@keyframes blink { 0%,100%{opacity:1;} 50%{opacity:0.2;} }

/* ── SESSION BADGES ── */
.session-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.22rem 0.7rem;
    border-radius: 2px;
    font-family: var(--mono);
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
}
.badge-morning { background: rgba(68,136,255,0.08); color: var(--blue); border: 1px solid rgba(68,136,255,0.3); }
.badge-midday  { background: rgba(245,168,35,0.08);  color: var(--accent-gold); border: 1px solid rgba(245,168,35,0.3); }
.badge-closing { background: rgba(240,80,96,0.08);   color: var(--red); border: 1px solid rgba(240,80,96,0.3); }

/* ── SECTION HEADERS ── */
.cc-section {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin: 1.8rem 0 0.9rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border-dim);
}
.cc-section-label {
    font-family: var(--mono);
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--text-dim);
}
.cc-section-line {
    flex: 1;
    height: 1px;
    background: var(--border-dim);
}

/* ── STAT BOXES ── */
.stat-grid { display: grid; gap: 0.5rem; }
.stat-box {
    background: var(--bg-panel);
    border: 1px solid var(--border-dim);
    padding: 0.65rem 0.8rem;
    text-align: center;
    transition: border-color 0.15s;
}
.stat-box:hover { border-color: var(--border-med); }
.stat-label {
    font-family: var(--mono);
    font-size: 0.58rem;
    font-weight: 600;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--text-dim);
    margin-bottom: 0.3rem;
}
.stat-value {
    font-family: var(--mono);
    font-size: 0.95rem;
    font-weight: 500;
    color: var(--text-primary);
}
.stat-chg {
    font-family: var(--mono);
    font-size: 0.68rem;
    margin-top: 0.15rem;
}
.pos { color: var(--green); }
.neg { color: var(--red); }
.neu { color: var(--text-dim); }

/* ── BRIEFING BODY ── */
.briefing-wrap {
    background: var(--bg-panel);
    border: 1px solid var(--border-dim);
    border-left: 2px solid var(--accent-gold);
    padding: 2rem 2.5rem;
    font-size: 0.9rem;
    line-height: 1.85;
    color: #d0d0e0;
    white-space: pre-wrap;
    font-family: var(--sans);
    letter-spacing: 0.01em;
}

/* ── ARCHIVE ITEMS ── */
.archive-row {
    background: var(--bg-panel);
    border: 1px solid var(--border-dim);
    border-left: 2px solid var(--border-med);
    padding: 0.75rem 1rem;
    margin-bottom: 0.4rem;
    cursor: pointer;
    transition: all 0.15s;
}
.archive-row:hover {
    border-color: var(--border-bright);
    border-left-color: var(--accent-gold);
    background: var(--bg-hover);
}
.archive-meta {
    font-family: var(--mono);
    font-size: 0.64rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.3rem;
}
.archive-preview {
    font-size: 0.78rem;
    color: var(--text-secondary);
    line-height: 1.5;
}

/* ── COUNTDOWN BOX ── */
.countdown-wrap {
    background: var(--bg-panel);
    border: 1px solid var(--border-dim);
    padding: 0.9rem 1rem;
    text-align: center;
}
.countdown-label {
    font-family: var(--mono);
    font-size: 0.58rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--text-dim);
}
.countdown-session {
    font-size: 0.78rem;
    color: var(--text-secondary);
    margin: 0.3rem 0;
}
.countdown-time {
    font-family: var(--mono);
    font-size: 1.3rem;
    font-weight: 600;
    color: var(--accent-gold);
    letter-spacing: 0.05em;
}
.countdown-at {
    font-family: var(--mono);
    font-size: 0.62rem;
    color: var(--text-dim);
    margin-top: 0.2rem;
}

/* ── SCHEDULE STRIP ── */
.schedule-strip {
    display: flex;
    gap: 0.4rem;
    margin-top: 0.7rem;
}
.sched-item {
    flex: 1;
    background: var(--bg-card);
    border: 1px solid var(--border-dim);
    padding: 0.45rem 0.5rem;
    text-align: center;
}
.sched-time {
    font-family: var(--mono);
    font-size: 0.68rem;
    font-weight: 600;
    color: var(--accent-gold);
}
.sched-name {
    font-family: var(--mono);
    font-size: 0.56rem;
    color: var(--text-dim);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-top: 0.15rem;
}

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
    background: var(--bg-deep) !important;
    border-right: 1px solid var(--border-dim) !important;
}
[data-testid="stSidebar"] * { color: var(--text-primary) !important; }
[data-testid="stSidebar"] .stTextInput input {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-med) !important;
    color: var(--text-primary) !important;
    font-family: var(--mono) !important;
    font-size: 0.78rem !important;
    border-radius: 2px !important;
}
[data-testid="stSidebar"] .stSelectbox > div > div {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-med) !important;
    border-radius: 2px !important;
}

/* ── BUTTONS ── */
.stButton > button {
    background: transparent !important;
    color: var(--accent-gold) !important;
    border: 1px solid var(--accent-gold) !important;
    border-radius: 2px !important;
    font-family: var(--mono) !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    transition: all 0.15s !important;
    width: 100% !important;
}
.stButton > button:hover {
    background: rgba(245,166,35,0.08) !important;
}

/* ── EXPANDER ── */
.streamlit-expanderHeader {
    background: var(--bg-panel) !important;
    border: 1px solid var(--border-dim) !important;
    border-radius: 2px !important;
    font-family: var(--mono) !important;
    font-size: 0.72rem !important;
    color: var(--text-secondary) !important;
}

/* ── DOWNLOAD BUTTON ── */
.stDownloadButton > button {
    background: transparent !important;
    color: var(--text-dim) !important;
    border: 1px solid var(--border-dim) !important;
    border-radius: 2px !important;
    font-family: var(--mono) !important;
    font-size: 0.68rem !important;
    letter-spacing: 0.08em !important;
}

/* ── SUCCESS/ERROR/INFO ── */
.stSuccess, .stInfo { border-radius: 2px !important; }

/* ── HR ── */
hr { border-color: var(--border-dim) !important; }

/* ── EMPTY STATE ── */
.empty-state {
    text-align: center;
    padding: 5rem 2rem;
    color: var(--text-dim);
}
.empty-icon {
    font-size: 2rem;
    margin-bottom: 1rem;
    opacity: 0.4;
}
.empty-title {
    font-family: var(--mono);
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--text-secondary);
    margin-bottom: 0.5rem;
}
.empty-sub {
    font-size: 0.78rem;
    color: var(--text-dim);
    line-height: 1.6;
}

/* ── NEWS ITEM ── */
.news-item {
    padding: 0.55rem 0;
    border-bottom: 1px solid var(--border-dim);
}
.news-src {
    font-family: var(--mono);
    font-size: 0.6rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--text-dim);
}
.news-title { font-size: 0.82rem; color: var(--text-primary); margin: 0.15rem 0; }
.news-summ { font-size: 0.74rem; color: var(--text-secondary); line-height: 1.5; }

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: var(--bg-void); }
::-webkit-scrollbar-thumb { background: var(--border-bright); border-radius: 2px; }
</style>
""", unsafe_allow_html=True)


# ─── SESSION STATE ────────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "briefings":        [],
        "current_briefing": None,
        "last_generated":   {},
        "api_key_set":      False,
        "auto_check_done":  False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ─── HELPERS ─────────────────────────────────────────────────────────────────
def get_session_badge(session: str) -> str:
    cls  = {"Morning": "badge-morning", "Midday": "badge-midday", "Closing": "badge-closing"}.get(session, "badge-morning")
    icon = SESSION_ICONS.get(session, "📋")
    return f'<span class="session-badge {cls}">{icon} {session}</span>'


def render_ticker_strip(market_data_raw: dict):
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
            color = "#00d4aa" if chg >= 0 else "#f05060"
            col.markdown(
                f"""<div class="stat-box">
                    <div class="stat-label">{label}</div>
                    <div class="stat-value">{price:,.2f}</div>
                    <div class="stat-chg" style="color:{color};">{sign}{chg:.2f}%</div>
                </div>""",
                unsafe_allow_html=True
            )


def run_generation(session_override: str = None):
    groq_key = st.secrets.get("GROQ_API_KEY", "")
    av_key   = st.secrets.get("ALPHA_VANTAGE_KEY", "")

    if not groq_key:
        st.error("GROQ_API_KEY not found in Streamlit secrets. Add it in App Settings → Secrets.")
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
    st.markdown("""
    <div style="padding:0.6rem 0 0.4rem 0;">
        <div style="font-family:'JetBrains Mono',monospace;font-size:0.62rem;font-weight:700;
                    letter-spacing:0.2em;text-transform:uppercase;color:#f5a623;
                    border-bottom:1px solid #1c1c2a;padding-bottom:0.6rem;margin-bottom:0.8rem;">
            ◈ Macro Desk
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Next session countdown
    nxt = next_session_info()
    st.markdown(
        f"""<div class="countdown-wrap">
            <div class="countdown-label">Next Session</div>
            <div class="countdown-session">{nxt['icon']} {nxt['label']}</div>
            <div class="countdown-time">{nxt['countdown']}</div>
            <div class="countdown-at">{nxt['start_time']}</div>
        </div>
        <div class="schedule-strip">
            <div class="sched-item"><div class="sched-time">8:40 AM</div><div class="sched-name">Morning</div></div>
            <div class="sched-item"><div class="sched-time">12:00 PM</div><div class="sched-name">Midday</div></div>
            <div class="sched-item"><div class="sched-time">5:30 PM</div><div class="sched-name">Closing</div></div>
        </div>""",
        unsafe_allow_html=True
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # Manual generation
    st.markdown("""<div style="font-family:'JetBrains Mono',monospace;font-size:0.62rem;
                    letter-spacing:0.15em;text-transform:uppercase;color:#444460;
                    margin-bottom:0.5rem;">Generate Briefing</div>""", unsafe_allow_html=True)
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

    # ── Archive with scrollable full list ──
    st.markdown("""<div style="font-family:'JetBrains Mono',monospace;font-size:0.62rem;
                    letter-spacing:0.15em;text-transform:uppercase;color:#444460;
                    margin-bottom:0.5rem;">Briefing Archive</div>""", unsafe_allow_html=True)

    search_q = st.text_input(
        "Search briefings",
        placeholder="Search by keyword, date, session...",
        label_visibility="collapsed"
    )

    archive = search_archive(search_q) if search_q else load_archive()

    if archive:
        st.markdown(f"""<div style="font-family:'JetBrains Mono',monospace;font-size:0.6rem;
                        color:#444460;margin-bottom:0.4rem;">{len(archive)} briefing(s) found</div>""",
                    unsafe_allow_html=True)

        # Show ALL briefings in a scrollable container via selectbox
        labels = [format_archive_label(e) for e in archive]

        # Scrollable list — use selectbox showing all entries (Streamlit handles scroll)
        selected_label = st.selectbox(
            "Select briefing",
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
                    "news_headlines":  entry.get("news_headlines", []),
                }
                st.rerun()

        # Also render a visual scrollable list below for quick scan
        st.markdown("""<div style="max-height:320px;overflow-y:auto;margin-top:0.6rem;
                        border:1px solid #1c1c2a;padding:0.4rem;">""", unsafe_allow_html=True)
        for i, entry in enumerate(archive):
            badge_cls = {"Morning":"badge-morning","Midday":"badge-midday","Closing":"badge-closing"}.get(entry.get("session",""),"badge-morning")
            preview = entry.get("briefing","")[:120].replace("<","&lt;")
            active_style = "border-left-color:#f5a623;" if labels[i] == selected_label else ""
            st.markdown(
                f"""<div class="archive-row" style="{active_style}">
                    <div class="archive-meta">
                        <span class="session-badge {badge_cls}" style="font-size:0.56rem;padding:0.1rem 0.4rem;">
                            {SESSION_ICONS.get(entry.get('session',''),'📋')} {entry.get('session','')}
                        </span>
                        &nbsp; {entry.get('date_str','')}
                    </div>
                    <div class="archive-preview">{preview}…</div>
                </div>""",
                unsafe_allow_html=True
            )
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("""<div style="font-family:'JetBrains Mono',monospace;font-size:0.7rem;
                        color:#444460;padding:1rem 0;text-align:center;">
                        No briefings in archive yet.</div>""", unsafe_allow_html=True)

    st.markdown("---")
    now_et = datetime.now(ET)
    st.markdown(
        f"""<div style="font-family:'JetBrains Mono',monospace;font-size:0.6rem;color:#333350;text-align:center;">
            ET {now_et.strftime('%I:%M %p')} · Auto-generates 8:40 AM / 12 PM / 5:30 PM
        </div>""",
        unsafe_allow_html=True
    )


# ─── AUTO-GENERATION CHECK ────────────────────────────────────────────────────
if not st.session_state["auto_check_done"]:
    session_now, now_et = current_session_et()
    if session_now and should_auto_generate(session_now, st.session_state["last_generated"]):
        st.info(f"Auto-generating {session_now} briefing for {now_et.strftime('%B %d, %Y')}...")
        run_generation(session_override=session_now)
    st.session_state["auto_check_done"] = True


# ─── MAIN HEADER ──────────────────────────────────────────────────────────────
now_et    = datetime.now(ET)
date_disp = now_et.strftime("%A, %B %d, %Y")
time_disp = now_et.strftime("%H:%M ET")

st.markdown(
    f"""<div class="cc-header">
        <div class="cc-header-left">
            <span class="cc-logo">News</span>
            <div class="cc-divider-v"></div>
            <span class="cc-title"><span class="live-dot"></span>Macro Market Briefing</span>
        </div>
        <div class="cc-header-right">
            <div class="cc-time">
                <div>{time_disp}</div>
                <div class="date">{date_disp}</div>
            </div>
        </div>
    </div>""",
    unsafe_allow_html=True
)


# ─── MAIN CONTENT ─────────────────────────────────────────────────────────────
briefing = st.session_state.get("current_briefing")

if briefing and briefing.get("briefing"):
    session  = briefing.get("session", "")
    date_str = briefing.get("date_str", "")
    gen_at   = briefing.get("generated_at", "")
    mkt_raw  = briefing.get("market_data_raw", {})

    # Meta row
    col1, col2, col3 = st.columns([2, 2, 4])
    with col1:
        st.markdown(get_session_badge(session), unsafe_allow_html=True)
    with col2:
        st.markdown(f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:0.72rem;color:#555570;">{date_str}</span>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:0.65rem;color:#333350;">Generated {gen_at}</span>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Ticker strip
    if mkt_raw:
        st.markdown("""<div class="cc-section">
            <span class="cc-section-label">Live Market Snapshot</span>
            <div class="cc-section-line"></div>
        </div>""", unsafe_allow_html=True)
        render_ticker_strip(mkt_raw)
        st.markdown("<br>", unsafe_allow_html=True)

    # News expander
    news_headlines = briefing.get("news_headlines", [])
    if news_headlines:
        with st.expander(f"📡  News Feed — {len(news_headlines)} headlines", expanded=False):
            st.markdown(f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.6rem;color:#444460;margin-bottom:0.6rem;letter-spacing:0.1em;text-transform:uppercase;">Live headlines used to generate this briefing</div>', unsafe_allow_html=True)
            for i, h in enumerate(news_headlines, 1):
                src   = h.get("source", "")
                title = h.get("title", "")
                summ  = h.get("summary", "")
                st.markdown(
                    f'<div class="news-item">'
                    f'<div class="news-src">{i:02d} · {src}</div>'
                    f'<div class="news-title">{title}</div>'
                    + (f'<div class="news-summ">{summ[:200]}</div>' if summ and summ != title else "")
                    + '</div>',
                    unsafe_allow_html=True
                )
        st.markdown("<br>", unsafe_allow_html=True)

    # Briefing body
    st.markdown("""<div class="cc-section">
        <span class="cc-section-label">Desk Note</span>
        <div class="cc-section-line"></div>
    </div>""", unsafe_allow_html=True)

    st.markdown(
        f'<div class="briefing-wrap">{briefing["briefing"]}</div>',
        unsafe_allow_html=True
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button(
        label="↓  Download Briefing (.txt)",
        data=briefing["briefing"],
        file_name=f"macro_briefing_{date_str.replace(', ','_').replace(' ','_')}_{session}.txt",
        mime="text/plain",
    )

else:
    # Empty state
    archive = load_archive()
    st.markdown(
        f"""<div class="empty-state">
            <div class="empty-icon">◈</div>
            <div class="empty-title">No Briefing Loaded</div>
            <div class="empty-sub">
                Use the sidebar to generate a briefing or load one from the archive.<br>
                Auto-generation runs at <strong style="color:#f5a623;">8:40 AM</strong>,
                <strong style="color:#f5a623;">12:00 PM</strong>, and
                <strong style="color:#f5a623;">5:30 PM</strong> ET every day.
            </div>
        </div>""",
        unsafe_allow_html=True
    )

    if archive:
        st.markdown("""<div class="cc-section">
            <span class="cc-section-label">Recent Briefings</span>
            <div class="cc-section-line"></div>
        </div>""", unsafe_allow_html=True)
        for entry in archive[:5]:
            badge   = get_session_badge(entry.get("session",""))
            preview = entry.get("briefing","")[:300].replace("<","&lt;")
            st.markdown(
                f"""<div class="archive-row">
                    {badge}
                    <span style="font-family:'JetBrains Mono',monospace;font-size:0.62rem;color:#444460;margin-left:0.5rem;">
                        {entry.get('date_str','')} · {entry.get('generated_at','')}
                    </span>
                    <div class="archive-preview" style="margin-top:0.4rem;">{preview}…</div>
                </div>""",
                unsafe_allow_html=True
            )
