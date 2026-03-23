"""
Briefing Generator — fixed for Streamlit Cloud import path issue.
Groq (free) + Yahoo Finance + RSS/GDELT news injection.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from datetime import datetime
import pytz

from utils.market_data import get_market_snapshot, format_snapshot_for_prompt
from utils.news_fetcher import fetch_headlines, format_headlines_for_prompt

ET = pytz.timezone("America/New_York")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.3-70b-versatile"


def get_session(now_et=None):
    if now_et is None:
        now_et = datetime.now(ET)
    hour = now_et.hour
    if hour < 10:
        return "Morning"
    elif hour < 14:
        return "Midday"
    else:
        return "Closing"


SYSTEM_PROMPT = """You are a senior macro strategist at a top-tier sell-side institution — 
think Goldman Sachs Global Markets Daily, JPMorgan Markets Briefing, or Bloomberg Markets Live.

YOUR WRITING STYLE (non-negotiable):
- Every section must be grounded in the SPECIFIC news headlines and market data provided.
  Do NOT write generic macro commentary. Do NOT invent events. If the headlines say Iran, 
  write about Iran. If oil is down 7%, explain exactly why and what it means.
- Write in dense, flowing paragraphs. NO bullet points in Sections 1-6.
- Lead every section with the actual price level and move, then explain the WHY.
- Use cause-and-effect chain logic: "X happened which drove Y which means Z"
- Use phrases: "The key question is...", "The move reflects...", "The market is pricing...", 
  "Positioning appears...", "Risk remains...", "The fulcrum is...", "This is consistent with..."
- Never be vague. Never say "markets are mixed" without explaining WHY.
- Never repeat the same point across sections — each section adds new analytical value.
- Tone: zero fluff, zero emojis, zero casual language. Dry, precise, institutional.
- Length: 2-4 tight paragraphs per section of real analysis.
"""


def build_prompt(session, market_data_str, news_str, date_str):
    div = "─" * 57
    eq  = "=" * 60
    return f"""Write a full institutional {session} Macro Market Briefing for {date_str}.

USE BOTH data sources below. Headlines = narrative driver. Market data = exact numbers.

{eq}
{news_str}
{eq}
{market_data_str}
{eq}

CRITICAL:
1. Section 1 must open by naming the single dominant driver from the headlines. 3-4 paragraphs of dense causal analysis citing the actual event and exact market reaction.
2. Every section must reference ACTUAL price levels from the market data.
3. Section 4: if oil is moving significantly it must be the lead story.
4. Section 7: use ONLY the actual headlines provided — do not fabricate stories.
5. Section 8: name specific upcoming catalysts — real data releases, Fed speakers, geopolitical deadlines, technical levels.

{date_str.upper()} | {session.upper()} BRIEFING
{div}

SECTION 1 — MACRO NARRATIVE

SECTION 2 — EQUITIES

SECTION 3 — RATES

SECTION 4 — COMMODITIES (EMPHASIZE OIL)

SECTION 5 — FX

SECTION 6 — CRYPTO

SECTION 7 — CORPORATE NEWS & HEADLINES

SECTION 8 — WHAT MATTERS NEXT

{div}
Powered by Traderverse | {date_str}
"""


def generate_briefing(groq_api_key, alpha_vantage_key="", session=None, force_session=None):
    now_et   = datetime.now(ET)
    date_str = now_et.strftime("%B %d, %Y")
    session  = force_session or session or get_session(now_et)
    gen_at   = now_et.strftime("%Y-%m-%d %H:%M ET")

    result = {
        "session": session, "date_str": date_str, "briefing": "",
        "market_data_raw": {}, "market_data_str": "",
        "news_headlines": [], "generated_at": gen_at, "error": None,
    }

    # 1. Market data
    try:
        snapshot = get_market_snapshot(alpha_vantage_key)
        result["market_data_raw"] = snapshot
        mkt_str = format_snapshot_for_prompt(snapshot)
        result["market_data_str"] = mkt_str
    except Exception as e:
        result["error"] = f"Market data fetch failed: {e}"
        mkt_str = "Market data unavailable — use conservative approximations."

    # 2. News headlines
    try:
        headlines = fetch_headlines(max_per_feed=8, max_total=35)
        result["news_headlines"] = headlines
        news_str = format_headlines_for_prompt(headlines)
    except Exception as e:
        result["error"] = (result.get("error") or "") + f" | News fetch failed: {e}"
        news_str = "Live headlines unavailable — anchor analysis to market data moves."

    # 3. Call Groq
    try:
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": build_prompt(session, mkt_str, news_str, date_str)},
            ],
            "max_tokens": 4096,
            "temperature": 0.3,
            "top_p": 0.85,
        }
        resp = requests.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=90,
        )
        resp.raise_for_status()
        result["briefing"] = resp.json()["choices"][0]["message"]["content"]
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else "?"
        body   = e.response.text[:400] if e.response else ""
        result["error"] = (result.get("error") or "") + f" | Groq HTTP {status}: {body}"
    except Exception as e:
        result["error"] = (result.get("error") or "") + f" | Groq error: {e}"

    return result
