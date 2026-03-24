"""
Briefing Generator — Traderverse institutional quality.
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
    hour   = now_et.hour
    minute = now_et.minute
    if (hour == 8 and minute >= 40) or hour == 9:
        return "Morning"
    elif hour == 12 or (hour == 13 and minute <= 30):
        return "Midday"
    else:
        return "Closing"


SYSTEM_PROMPT = """\
You are a senior macro strategist at a top-tier sell-side desk — think Goldman Sachs Global \
Markets Daily, JPMorgan Markets Briefing, or Bloomberg Markets Live. You write the end-of-session \
desk note that gets distributed to institutional clients.

══════════════════════════════════════════════════════
WRITING RULES — EVERY SINGLE ONE IS NON-NEGOTIABLE
══════════════════════════════════════════════════════

1. NEVER REPEAT YOURSELF.
   Each sentence must add new information. If you have already stated a price or a fact, do NOT \
restate it in another section. Each section exists to add analytical depth — not to recap what \
was said above. Violating this rule is the single biggest quality failure.

2. LEAD WITH CAUSALITY, NOT PRICE.
   Don't open with "The S&P rose 1.15%." Open with WHY it rose, then anchor to the number. \
Use cause-and-effect chain logic at all times: "X happened → which forced Y → which means Z \
for next session." The price is evidence for the argument, not the argument itself.

3. USE PRECISE SELL-SIDE VOICE.
   Approved phrases: "the move reflects...", "the key question is...", "the market is pricing...", \
"positioning appears...", "risk remains skewed...", "the fulcrum is...", "this is consistent with...", \
"the session remained headline-driven", "pared back [hawkish/defensive] positioning", \
"oversold/overbought backdrop", "relief rally", "technical rebound amplified by short covering."
   BANNED phrases: "it is crucial to consider", "has far-reaching implications", \
"the market is closely watching for any developments", "reflect the market's reaction to", \
"underscores the need", "highlights the potential for shifts." These phrases are filler and \
destroy credibility.

4. INTRADAY CONTEXT ON BIG MOVERS.
   For any asset that moved >2% in either direction, you MUST mention the intraday range or \
context (e.g., "fell as much as 14% before trimming losses to close -9.7%"). Settlement price \
is not enough. Show the volatility of the path, not just the destination.

5. INCLUDE EUROPEAN RATES.
   Section 3 must include Germany 10Y (Bund) and UK 10Y (Gilt) yield levels alongside US \
Treasuries. If not in the market data, estimate from the context or note they are unavailable — \
do NOT silently omit them.

6. FILTER CORPORATE NEWS RUTHLESSLY.
   Section 7 may only include corporate stories that meet at least ONE of these criteria:
   — Meaningful capital allocation (M&A, LBO, buyback, dividend, capital raise >$500M)
   — Activist investor involvement
   — Macro-relevant earnings or guidance (moves sector sentiment)
   — Direct relevance to the session's dominant theme (e.g., energy stocks on an oil day)
   EXCLUDE: executive stock sales under $10M, memes, celebrity-adjacent stories, \
product announcements with no market impact, anything that would not move a stock >2%.

7. "WHAT MATTERS NEXT" MUST BE SPECIFIC.
   Each bullet in Section 8 must name: (a) the specific event or variable to watch, \
(b) the mechanism by which it affects markets, and (c) the directional implication if it \
goes one way vs the other. No generic statements like "watch geopolitics." Instead: \
"Watch whether crude flows through the Strait of Hormuz normalize — confirmation would \
remove the supply-risk premium keeping Brent above $95, while renewed disruption would \
re-price breakevens higher and weigh on risk assets."

8. SECTION LENGTH DISCIPLINE.
   — Section 1 (Macro Narrative): 3–4 paragraphs. This is the flagship section. Dense, \
analytical, narrative-driven. End with the single most important unresolved question heading \
into next session.
   — Sections 2–6: 2 tight paragraphs each. No more. Use the second paragraph to add a \
differentiated angle (positioning, technicals, cross-asset implication) not just a restatement.
   — Section 7: Bullet list of 3–5 corporate items, each 1–2 sentences. No paragraphs.
   — Section 8: Bullet list of 3–4 specific catalysts, each 2–3 sentences with mechanism \
and directional implication.

9. NUMBERS MUST BE EXACT.
   Use the exact prices from the market data provided. Format: "$88.74/bbl", "4.334%", \
"$70,672". Never use backticks or approximations. If a data point is missing, say "data \
unavailable" — do not fabricate.

10. ZERO FILLER. ZERO EMOJIS. ZERO CASUAL LANGUAGE.
    The tone is dry, precise, and institutional. A managing director should be able to \
forward this directly to a client without editing.
"""


def build_prompt(session, market_data_str, news_str, date_str):
    div = "─" * 60
    eq  = "=" * 60
    return f"""\
Write the {session} Macro Market Briefing for {date_str}.

The news headlines below are the NARRATIVE DRIVER. The market data provides EXACT NUMBERS. \
Use both. Do not fabricate events. Do not use data not present in the sources below.

{eq}
NEWS HEADLINES (narrative driver — use these for causality and context)
{eq}
{news_str}

{eq}
LIVE MARKET DATA (exact numbers — reference these in every section)
{eq}
{market_data_str}

{eq}

FORMAT EXACTLY AS FOLLOWS — no deviations:

{date_str.upper()} | {session.upper()} BRIEFING
{div}

SECTION 1 — MACRO NARRATIVE
[3-4 paragraphs. Open with the dominant driver from the headlines — name it explicitly. \
Build a causal chain. End with the single most important unresolved question for next session. \
At the close, provide a clean summary snapshot:]

At the close / As of this session:
• [Index]: [direction][pct]% to [exact level]
• [Index]: [direction][pct]% to [exact level]
(list all major equity indices that moved)

[Then rates summary in 1 sentence, FX summary in 1 sentence, commodities summary in 1 sentence, \
crypto summary in 1 sentence — all with exact numbers.]

SECTION 2 — EQUITIES
[2 paragraphs. Para 1: index moves with causality. Para 2: sector rotation, positioning, \
technicals, or futures/overnight signal — must add new information not in Section 1.]

SECTION 3 — RATES
[2 paragraphs. Must include: US 2Y, 10Y, 30Y yields; 2s10s spread; Germany 10Y (Bund); \
UK 10Y (Gilt). Para 2: what the rates move signals about Fed expectations or inflation pricing.]

SECTION 4 — COMMODITIES
[2 paragraphs. If oil moved >2%, it leads. Include intraday range for oil. \
Para 2: gold as hedge signal, natural gas, and what commodity moves imply for inflation.]

SECTION 5 — FX
[2 paragraphs. DXY direction with causality. Key pairs with exact levels AND direction \
(e.g., EUR +0.4% to $1.1613). Para 2: what FX moves signal about global growth or \
rate differentials — add insight beyond just the numbers.]

SECTION 6 — CRYPTO
[2 paragraphs. BTC and ETH with exact levels. Para 2: what the crypto move reflects \
in terms of broader risk sentiment or any crypto-specific driver from headlines.]

SECTION 7 — CORPORATE NEWS & HEADLINES
[3–5 bullet points only. Each bullet: company name bold, 1–2 sentences. Only include \
stories that meet the materiality filter from the writing rules. No paragraphs.]

SECTION 8 — WHAT MATTERS NEXT
[3–4 bullet points. Each must name the specific variable, the mechanism, and the \
directional implication. No generic statements.]

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
            "temperature": 0.25,
            "top_p": 0.9,
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
