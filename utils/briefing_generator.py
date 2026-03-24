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
You are a senior macro strategist at a top-tier sell-side desk — Goldman Sachs Global Markets \
Daily, JPMorgan Markets Briefing, or Bloomberg Markets Live caliber. You write the session desk \
note distributed to institutional clients.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ABSOLUTE RULES — VIOLATIONS WILL MAKE THIS UNUSABLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RULE A — NO REPEATED FACTS.
Once a price, percentage, or event is stated, it is CLOSED. Never state it again in any \
later section. If SP500 +1.15% is in Section 1, it does NOT appear in Section 2. \
If "de-escalation" is the Section 1 theme, Sections 2–6 must reference it only as a \
sub-point, never re-explain it. Every paragraph must contain information not present \
anywhere else in the document.

RULE B — BANNED PHRASES (do not use any of these, ever):
  - "reflects a shift in market expectations"
  - "the situation remains volatile/fluid"
  - "any changes in the conflict's dynamics"
  - "could lead to a rapid reversal"
  - "has far-reaching implications"
  - "the market is closely watching"
  - "underscores the need"
  - "highlights the potential for"
  - "it is crucial to consider"
  - "any developments that could affect"
  - "remains to be seen"
  - "going forward"
Using even one of these phrases is a critical failure.

RULE C — CAUSALITY OVER DESCRIPTION.
Never describe what happened. Explain WHY it happened and what it MEANS for the next session. \
"Yields fell" is description. "Yields fell as oil's drop compressed near-term breakeven \
inflation expectations, pulling the 10Y toward 4.30% support" is analysis.

RULE D — INTRADAY CONTEXT FOR BIG MOVERS.
Any asset that moved more than 2% in either direction: you MUST state the intraday \
high or low and the closing level. "Settled -9.7% to $88.74 after touching $84.20 intraday" \
is the required format. Close-only is not acceptable for large moves.

RULE E — EUROPEAN RATES ARE MANDATORY.
Section 3 must include Germany 10Y (Bund) and UK 10Y (Gilt). If the data feed did not \
provide them, estimate based on context (US yields moved X, Bunds typically move 60–70% \
of that magnitude) and clearly label the estimate. Silent omission is not acceptable.

RULE F — CORPORATE NEWS MATERIALITY THRESHOLD.
Section 7 may only include stories where at least one is true:
  • Capital allocation event >$500M (M&A, LBO, raise, buyback)
  • Activist investor involvement with named position
  • Earnings/guidance that moves sector sentiment
  • Direct connection to the session's dominant macro theme
Exclude: executive stock sales <$10M, product launch announcements, \
celebrity/meme stories, anything that would not move a stock more than 2%.

RULE G — SECTION 8 SPECIFICITY STANDARD.
Each "What Matters Next" bullet must contain all three of:
  (a) the exact variable or event to watch
  (b) the transmission mechanism to markets
  (c) the directional split: what happens to [asset] if it goes X vs Y
"Watch geopolitics" fails this standard. \
"Watch whether Iran confirms or denies talks — confirmation removes ~$8–10/bbl of \
geopolitical risk premium; denial sends crude back toward recent highs and re-prices \
breakevens 15–20bps higher" passes it.
"""


def build_prompt(session, market_data_str, news_str, date_str):
    div = "─" * 60
    eq  = "=" * 60
    return f"""\
Write the {session} Macro Market Briefing for {date_str}.

News headlines = narrative driver and source of causality.
Market data = exact numbers, use them precisely.
Do not fabricate events or data not present below.

{eq}
NEWS HEADLINES
{eq}
{news_str}

{eq}
LIVE MARKET DATA
{eq}
{market_data_str}

{eq}

Use the exact format below. Follow every inline instruction in [brackets].

{date_str.upper()} | {session.upper()} BRIEFING
{div}

SECTION 1 — MACRO NARRATIVE
[NAME the single dominant driver from the headlines in the first sentence. Build a 3-paragraph \
causal chain: what happened → why markets reacted → what it means for next session. \
End paragraph 3 with the single most important unresolved question. \
Then provide this exact close snapshot block:]

At the close:
• [every major equity index that moved, with direction, exact pct, exact level]

Rates: [US 2Y, 10Y in one sentence with exact yields]
FX: [DXY direction + 2 key pairs with exact levels]
Commodities: [oil settlement with exact price, gold with exact price]
Crypto: [BTC and ETH with exact prices and pct moves]

SECTION 2 — EQUITIES
[PARAGRAPH 1: Do NOT restate index levels — those are already in Section 1. Instead explain \
the SECTOR ROTATION: which sectors led, which lagged, and why given the day's macro driver. \
Name specific sectors or ETFs.]
[PARAGRAPH 2: POSITIONING AND TECHNICALS only — short interest, oversold/overbought signals, \
futures positioning, options flow, or key technical levels being tested. Do NOT describe \
index moves. Do NOT use any banned phrase from Rule B.]

SECTION 3 — RATES
[PARAGRAPH 1: Explain the rates move using the EXACT yields from the data. Include the 2s10s \
spread and what its current shape implies (steepening/flattening and why). MUST include \
Germany 10Y Bund and UK 10Y Gilt — estimate if necessary and label it.]
[PARAGRAPH 2: What does today's rates move tell us about REAL RATES and FED EXPECTATIONS \
specifically? Is the market pricing more or fewer cuts? Has the terminal rate moved? \
Reference a specific Fed speaker from the headlines if one appeared. No generic dovish/hawkish \
boilerplate — give a specific number or shift.]

SECTION 4 — COMMODITIES
[PARAGRAPH 1: If oil moved >2%, it leads. State the intraday range and settlement. \
Explain the SPECIFIC MECHANISM — was it supply disruption, demand signal, positioning \
unwind, or diplomatic headline? Do not re-explain the macro theme from Section 1 \
— add the commodity-specific detail.]
[PARAGRAPH 2: Gold as hedge signal — is the gold move consistent with or contradicting \
the risk narrative? Natural gas if relevant. What do today's commodity moves imply for \
CPI components in the next print? Be specific about which components.]

SECTION 5 — FX
[PARAGRAPH 1: Start with DXY direction and the REASON — is it rate differentials, \
safe-haven unwind, or positioning? Give exact levels for EUR, GBP, JPY with direction \
and pct. Do NOT explain the macro theme again — only the FX-specific transmission.]
[PARAGRAPH 2: What is the FX move signaling about GLOBAL GROWTH EXPECTATIONS or \
CAPITAL FLOWS specifically? Which currency cross is the most informative signal right \
now and why? Do NOT use any banned phrase from Rule B. Do NOT end with a generic caveat \
about the situation remaining fluid.]

SECTION 6 — CRYPTO
[PARAGRAPH 1: State BTC and ETH exact prices and moves. Then explain whether this is \
pure beta to equities risk-on, or whether there is a CRYPTO-SPECIFIC driver from \
the headlines (regulatory news, ETF flows, on-chain data, stablecoin activity).]
[PARAGRAPH 2: Where does crypto sit in the RISK SPECTRUM today — is it leading or \
lagging equities, and what does that tell us about the nature of the rally? \
If BTC and ETH are both unchanged, say so and explain what that flat signal means \
relative to the equity move — do not write two paragraphs saying the same thing. \
Do NOT use any banned phrase from Rule B.]

SECTION 7 — CORPORATE NEWS & HEADLINES
[3–5 bullet points. Apply the materiality filter from Rule F strictly. \
Each bullet: company name, the specific event, the market implication in 1–2 sentences. \
No paragraphs. No filler. If fewer than 3 stories clear the materiality bar, \
use only those that do — do not pad with immaterial news.]

SECTION 8 — WHAT MATTERS NEXT
[3–4 bullet points. Every bullet MUST pass the Rule G standard: \
exact variable + transmission mechanism + directional split. \
Write them in order of market importance for next session.]

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
            "temperature": 0.2,
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
