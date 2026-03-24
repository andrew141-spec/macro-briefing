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
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

:root{
    --bg:#020202;
    --bg-soft:#070707;
    --panel:#050505;
    --panel-2:#090909;
    --line:#141414;
    --line-2:#1d1d1d;
    --text:#d7d7d7;
    --text-soft:#8b8b8b;
    --text-dim:#5f5f5f;
    --accent:#ff7a1a;
    --accent-soft:rgba(255,122,26,.14);
    --green:#3ddc84;
    --red:#ff5a5f;
    --mono:'IBM Plex Mono', monospace;
    --display:'Rajdhani', sans-serif;
}

/* base */
html, body, [class*="css"]{
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: var(--display) !important;
}

.stApp{
    background:
        linear-gradient(rgba(255,122,26,.04), rgba(255,122,26,0)) top/100% 1px no-repeat,
        var(--bg) !important;
}

#MainMenu, footer, header {visibility:hidden;}
.block-container{
    max-width:100% !important;
    padding:0 .75rem 1rem .75rem !important;
}

/* remove streamlit rounded feel */
div[data-testid="stVerticalBlock"],
div[data-testid="stHorizontalBlock"]{
    gap:.55rem !important;
}

/* header */
.cc-header{
    background:#000 !important;
    border:1px solid var(--line-2);
    border-left:none;
    border-right:none;
    padding:.55rem .9rem;
    margin:-1rem -.75rem .75rem -.75rem;
    display:flex;
    align-items:center;
    justify-content:space-between;
    box-shadow: inset 0 -1px 0 rgba(255,122,26,.08);
}
.cc-header-left,
.cc-header-right{
    display:flex;
    align-items:center;
    gap:.8rem;
}
.cc-logo{
    font-family:var(--display);
    font-size:.95rem;
    font-weight:700;
    letter-spacing:.14em;
    text-transform:uppercase;
    color:var(--accent);
    padding:0;
    border:none;
    line-height:1;
}
.cc-title{
    font-family:var(--mono);
    font-size:.56rem;
    letter-spacing:.28em;
    text-transform:uppercase;
    color:var(--text-dim);
}
.cc-divider-v{
    width:1px;
    height:16px;
    background:var(--line-2);
}
.cc-time{
    font-family:var(--mono);
    font-size:.66rem;
    color:var(--text-soft);
    letter-spacing:.08em;
    text-transform:uppercase;
}
.cc-time .date{
    color:var(--text-dim);
    font-size:.58rem;
}
.live-dot{
    width:5px;
    height:5px;
    border-radius:50%;
    background:var(--green);
    box-shadow:0 0 8px rgba(61,220,132,.65);
    display:inline-block;
    margin-right:6px;
}

/* sections */
.cc-section{
    display:flex;
    align-items:center;
    gap:.55rem;
    margin:1rem 0 .5rem 0;
    padding:0;
    border:none;
}
.cc-section-label{
    font-family:var(--display);
    font-size:.82rem;
    font-weight:700;
    letter-spacing:.12em;
    text-transform:uppercase;
    color:var(--accent);
    line-height:1;
}
.cc-section-line{
    flex:1;
    height:1px;
    background:linear-gradient(to right, rgba(255,122,26,.32), transparent 72%);
}

/* cards / panels */
.stat-box,
.briefing-wrap,
.archive-row,
.countdown-wrap,
.sched-item,
.streamlit-expanderHeader,
[data-testid="stMetric"],
[data-testid="stMarkdownContainer"] > div:has(.news-item){
    background:linear-gradient(180deg, var(--panel-2), var(--panel)) !important;
    border:1px solid var(--line-2) !important;
    border-radius:0 !important;
    box-shadow:
        inset 0 1px 0 rgba(255,122,26,.04),
        0 0 0 1px rgba(0,0,0,.65);
}

/* stat boxes */
.stat-grid{display:grid;gap:.45rem;}
.stat-box{
    padding:.55rem .65rem;
    text-align:left;
    min-height:74px;
}
.stat-box:hover{
    border-color:rgba(255,122,26,.45) !important;
    background:linear-gradient(180deg, #0d0d0d, #060606) !important;
}
.stat-label{
    font-family:var(--mono);
    font-size:.54rem;
    font-weight:600;
    letter-spacing:.2em;
    text-transform:uppercase;
    color:var(--text-dim);
    margin-bottom:.35rem;
}
.stat-value{
    font-family:var(--display);
    font-size:1.15rem;
    font-weight:700;
    letter-spacing:.02em;
    color:#f1f1f1;
    line-height:1;
}
.stat-chg{
    font-family:var(--mono);
    font-size:.6rem;
    margin-top:.3rem;
    letter-spacing:.06em;
}
.pos{color:var(--green);}
.neg{color:var(--red);}
.neu{color:var(--text-dim);}

/* briefing panel */
.briefing-wrap{
    padding:1.15rem 1.25rem;
    border-left:1px solid var(--accent) !important;
    font-size:.92rem;
    line-height:1.75;
    color:#d0d0d0;
    white-space:pre-wrap;
    font-family:var(--display);
}

/* archive */
.archive-row{
    padding:.7rem .8rem;
    margin-bottom:.35rem;
    transition:.15s ease;
}
.archive-row:hover{
    border-color:rgba(255,122,26,.45) !important;
    background:#0a0a0a !important;
}
.archive-meta{
    font-family:var(--mono);
    font-size:.56rem;
    letter-spacing:.16em;
    text-transform:uppercase;
    color:var(--text-dim);
    margin-bottom:.25rem;
}
.archive-preview{
    font-size:.78rem;
    color:var(--text-soft);
    line-height:1.4;
}

/* countdown / schedule */
.countdown-wrap{
    padding:.75rem .8rem;
    text-align:left;
}
.countdown-label,
.sched-name{
    font-family:var(--mono);
    font-size:.55rem;
    letter-spacing:.18em;
    text-transform:uppercase;
    color:var(--text-dim);
}
.countdown-session{
    font-size:.74rem;
    color:var(--text-soft);
    margin:.2rem 0;
}
.countdown-time{
    font-family:var(--display);
    font-size:1.2rem;
    font-weight:700;
    color:var(--accent);
    letter-spacing:.04em;
    line-height:1;
}
.countdown-at{
    font-family:var(--mono);
    font-size:.56rem;
    color:var(--text-dim);
    margin-top:.2rem;
}
.schedule-strip{display:flex;gap:.35rem;margin-top:.55rem;}
.sched-item{padding:.4rem .45rem;text-align:left;}
.sched-time{
    font-family:var(--display);
    font-size:.82rem;
    font-weight:700;
    color:var(--accent);
    line-height:1;
}

/* badges */
.session-badge{
    display:inline-flex;
    align-items:center;
    gap:.35rem;
    padding:.16rem .48rem;
    border-radius:0;
    font-family:var(--mono);
    font-size:.54rem;
    font-weight:600;
    letter-spacing:.18em;
    text-transform:uppercase;
    border:1px solid var(--line-2);
    background:#090909;
}
.badge-morning,
.badge-midday,
.badge-closing{
    color:var(--accent);
    border-color:rgba(255,122,26,.35);
    background:rgba(255,122,26,.08);
}

/* sidebar */
[data-testid="stSidebar"]{
    background:#000 !important;
    border-right:1px solid var(--line-2) !important;
}
[data-testid="stSidebar"] *{
    color:var(--text) !important;
}
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stSelectbox > div > div,
[data-testid="stSidebar"] textarea{
    background:#080808 !important;
    border:1px solid var(--line-2) !important;
    border-radius:0 !important;
    color:var(--text) !important;
    font-family:var(--mono) !important;
    font-size:.72rem !important;
}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown{
    font-family:var(--mono) !important;
}

/* buttons */
.stButton > button,
.stDownloadButton > button{
    width:100% !important;
    background:#090909 !important;
    color:var(--accent) !important;
    border:1px solid rgba(255,122,26,.45) !important;
    border-radius:0 !important;
    box-shadow:none !important;
    font-family:var(--mono) !important;
    font-size:.66rem !important;
    font-weight:600 !important;
    letter-spacing:.18em !important;
    text-transform:uppercase !important;
    min-height:2.25rem !important;
}
.stButton > button:hover,
.stDownloadButton > button:hover{
    background:var(--accent-soft) !important;
    border-color:var(--accent) !important;
}

/* expander */
.streamlit-expanderHeader{
    font-family:var(--mono) !important;
    font-size:.66rem !important;
    color:var(--text-soft) !important;
    padding:.65rem .8rem !important;
}

/* inputs */
.stTextInput input,
.stTextArea textarea,
.stSelectbox > div > div{
    border-radius:0 !important;
}

/* empty state */
.empty-state{
    text-align:center;
    padding:4rem 1rem;
    color:var(--text-dim);
    border:1px dashed var(--line-2);
    background:#050505;
}
.empty-icon{
    font-size:1.6rem;
    margin-bottom:.75rem;
    opacity:.35;
}
.empty-title{
    font-family:var(--mono);
    font-size:.72rem;
    font-weight:600;
    letter-spacing:.18em;
    text-transform:uppercase;
    color:var(--text-soft);
    margin-bottom:.4rem;
}
.empty-sub{
    font-size:.75rem;
    color:var(--text-dim);
    line-height:1.5;
}

/* news */
.news-item{
    padding:.5rem 0;
    border-bottom:1px solid var(--line);
}
.news-src{
    font-family:var(--mono);
    font-size:.54rem;
    letter-spacing:.18em;
    text-transform:uppercase;
    color:var(--text-dim);
}
.news-title{
    font-size:.8rem;
    color:#efefef;
    margin:.14rem 0;
}
.news-summ{
    font-size:.72rem;
    color:var(--text-soft);
    line-height:1.45;
}

/* tables / markdown */
table{
    border-collapse:collapse !important;
}
th, td{
    border-color:var(--line-2) !important;
}

/* scrollbar */
::-webkit-scrollbar{width:6px;height:6px;}
::-webkit-scrollbar-track{background:#030303;}
::-webkit-scrollbar-thumb{
    background:#202020;
    border-radius:0;
}
::-webkit-scrollbar-thumb:hover{
    background:#2b2b2b;
}
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
    gemini_key = st.secrets.get("GEMINI_API_KEY", "")
    groq_key   = st.secrets.get("GROQ_API_KEY", "")
    av_key     = st.secrets.get("ALPHA_VANTAGE_KEY", "")

    if not gemini_key and not groq_key:
        st.error("No API key found. Add GEMINI_API_KEY (or GROQ_API_KEY as fallback) to Streamlit secrets.")
        return

    model_label = "Gemini 2.0 Flash" if gemini_key else "Groq (fallback)"
    with st.spinner(f"Fetching live market data and generating briefing via {model_label}..."):
        result = generate_briefing(
            gemini_api_key=gemini_key,
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
        st.success(f"Briefing generated via {model_label} — {result['session']} | {result['generated_at']}")
    else:
        st.error("Generation failed")
        st.write(f"**Prompt size:** {result.get('prompt_chars', 'unknown')} chars")
        error_detail = result.get('error') or 'No error detail captured'
        st.code(error_detail, language=None)
        st.write("**Debug info:**")
        for k, v in result.items():
            if k not in ('briefing', 'market_data_raw', 'market_data_str', 'news_headlines'):
                st.write(f"- `{k}`: {str(v)[:300]}")


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

    if st.button("Test Connectivity", use_container_width=True):
        import requests as _req
        gemini_key = st.secrets.get("GEMINI_API_KEY", "")
        groq_key   = st.secrets.get("GROQ_API_KEY", "")

        st.write("**Keys found:**")
        st.write(f"- Gemini: {'✅ set' if gemini_key else '❌ missing'}")
        st.write(f"- Groq: {'✅ set' if groq_key else '❌ missing'}")

        st.write("**Network test:**")
        try:
            r = _req.get("https://httpbin.org/get", timeout=5)
            st.write(f"- Basic internet: ✅ {r.status_code}")
        except Exception as e:
            st.write(f"- Basic internet: ❌ {e}")

        try:
            r = _req.get("https://generativelanguage.googleapis.com", timeout=5)
            st.write(f"- Gemini endpoint: ✅ reachable")
        except Exception as e:
            st.write(f"- Gemini endpoint: ❌ {e}")

        try:
            r = _req.get("https://api.groq.com", timeout=5)
            st.write(f"- Groq endpoint: ✅ reachable")
        except Exception as e:
            st.write(f"- Groq endpoint: ❌ {e}")

    if st.button("Generate Now", use_container_width=True):
        override = None if session_choice == "Auto-detect" else session_choice
        run_generation(session_override=override)
        st.rerun()

    st.markdown("---")

    # ── Archive ──
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

        labels = [format_archive_label(e) for e in archive]

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
