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
ABSOLUTE RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RULE A — NO REPEATED FACTS.
Once a price, percentage, or event is stated, it is CLOSED. Never state it again anywhere \
later in the document. Each paragraph must contain information not present anywhere else.

RULE B — BANNED PHRASES. Do not use any of these, ever:
  - "reflects a shift in market expectations"
  - "the situation remains volatile" / "the situation remains fluid"
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
  - "have significant implications"
  - "investors will be closely watching"
  - "X said Y, which could lead to Z" — state the implication directly instead

RULE C — CAUSAL CHAIN STRUCTURE FOR SECTION 1.
The Section 1 causal chain must follow market logic, not narrative logic.
Correct chain: geopolitical signal → oil repricing → inflation expectations compress \
→ real rates fall → equity multiples expand → risk assets rally.
WRONG: "CEO X said Y therefore markets went up." CEO quotes do not move markets. \
Positioning, rates, and risk premium move markets. Find the real mechanism.

RULE D — INTRADAY CONTEXT FOR BIG MOVERS.
Any asset that moved more than 2%: state the intraday high or low AND the settlement. \
Format: "settled -9.7% to $88.74 after touching $84.20 intraday."

RULE E — EUROPEAN RATES ARE MANDATORY.
Section 3 must include Germany 10Y Bund and UK 10Y Gilt. Estimate if necessary, \
label estimates clearly. Silent omission is not acceptable.

RULE F — CORPORATE NEWS MATERIALITY THRESHOLD.
Section 7 only includes stories where at least one is true:
  • Capital allocation event >$500M (M&A, LBO, raise, buyback)
  • Named activist investor with disclosed position size
  • Earnings or guidance move with sector-level sentiment impact
  • Direct operational connection to the session's dominant macro theme
CEO quotes and strategy commentary do NOT clear this bar unless paired with a \
capital allocation decision. Apollo redemption stories only qualify if the \
redemption size and fund impact are material and specific.
Write each bullet as a direct statement of implication — never "X said Y which could lead to Z."

RULE G — SECTION 8 SPECIFICITY STANDARD.
Each bullet must contain all three:
  (a) exact variable or event to watch
  (b) transmission mechanism to markets
  (c) directional split with specific levels where possible
Example that passes: "Watch whether Iran confirms diplomatic contact — \
confirmation removes an estimated $8–10/bbl geopolitical premium from Brent, \
pulling energy breakevens ~15bps lower and supporting further multiple expansion in equities; \
denial reverses the session's entire move."
Example that fails: "Watch geopolitics."

RULE H — SECTION 6 CRYPTO ANALYTICAL STANDARD.
If BTC and ETH are flat while equities rally, that is a SIGNAL, not a non-event. \
Analyze it: crypto underperforming a strong risk-on session suggests the rally is being \
read as a geopolitical relief trade rather than a genuine growth re-rating — because \
growth re-ratings lift crypto alongside equities, while geopolitical relief trades do not. \
Never write two paragraphs that say the same thing. The second paragraph must add a \
different analytical point from the first.
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

{date_str.upper()} | {session.upper()} BRIEFING
{div}

SECTION 1 — MACRO NARRATIVE
[3 paragraphs. PARAGRAPH 1: Name the dominant geopolitical or macro event from the headlines \
in sentence one. Then build the MARKET MECHANISM chain — do not describe the event, \
explain how it transmitted into prices. The chain must be: \
event → which asset repriced first → why that caused the second asset to move → \
what that implies for valuations. No CEO quotes as market drivers. \
PARAGRAPH 2: What was the quality of the move? Was it driven by genuine positioning, \
short covering, or low-liquidity amplification? What is the bear case that the bulls \
are ignoring today? State it directly. \
PARAGRAPH 3: End with the single most important unresolved question for next session — \
phrased as a specific testable condition, not a vague theme. \
Then the close snapshot:]

At the close:
• [all major equity indices with direction, exact pct, exact level]

Rates: [US 2Y and 10Y exact yields in one sentence]
FX: [DXY + 2 key pairs with exact levels and direction]
Commodities: [oil settlement exact price and pct, gold exact price and pct]
Crypto: [BTC and ETH exact prices and pct moves]

SECTION 2 — EQUITIES
[PARAGRAPH 1: Do NOT restate any index level or pct already in Section 1. \
Lead with SECTOR ROTATION — which sectors won and lost today and the specific \
mechanism connecting them to the day's macro driver. Name ETFs or sector indices. \
PARAGRAPH 2: POSITIONING AND TECHNICALS only — short interest levels, \
oversold/overbought signals, options flow, key technical levels being tested or broken. \
Zero index-level restatement. Zero banned phrases.]

SECTION 3 — RATES
[PARAGRAPH 1: Exact yields for US 2Y, 10Y, 30Y. State the 2s10s spread and interpret \
its direction — steepening means the market expects growth to outpace near-term \
inflation; flattening is the opposite. Germany 10Y Bund and UK 10Y Gilt are REQUIRED — \
estimate from US move correlation if not in the data and label as estimate. \
PARAGRAPH 2: What specifically shifted in Fed pricing today? How many cuts is \
the market now pricing for the year, and did that change? Reference any Fed speaker \
from the headlines by name and quote the specific concern they raised. \
Do not use vague dovish/hawkish labels — give a specific rate level or shift.]

SECTION 4 — COMMODITIES
[PARAGRAPH 1: Oil leads if it moved >2%. REQUIRED: intraday low or high AND settlement \
price. Explain the SPECIFIC MECHANISM for the move — geopolitical risk premium unwind, \
physical vs futures divergence, positioning flush, or demand signal. Do NOT re-explain \
the geopolitical narrative from Section 1 — add the commodity-market-specific detail \
such as positioning, inventory, or physical vs paper divergence. \
PARAGRAPH 2: Gold — is it confirming or contradicting the risk narrative? \
A falling gold price alongside falling oil is a clean risk-off unwind; \
falling oil with rising gold is stagflation hedging. State which pattern this is. \
Then: which specific CPI components will be affected by today's commodity moves \
and by how much approximately?]

SECTION 5 — FX
[PARAGRAPH 1: DXY direction with the specific driver — rate differential compression, \
safe-haven unwind, or capital flow rotation? Exact levels for EUR, GBP, JPY \
with direction and pct move. Do NOT re-explain the macro theme. \
PARAGRAPH 2: Name the single most informative currency cross today and explain \
exactly what it is signaling about relative growth or monetary policy expectations. \
Give the level and the interpretation. Do NOT end with any caveat about uncertainty \
or the situation remaining fluid. End with a forward-looking statement about \
what level or event would change the FX thesis.]

SECTION 6 — CRYPTO
[PARAGRAPH 1: BTC and ETH exact prices and pct moves. Is this pure equity beta, \
or is there a crypto-specific driver in the headlines? Check for ETF flow news, \
regulatory developments, stablecoin activity, or on-chain signals. \
PARAGRAPH 2: REQUIRED ANALYSIS — compare crypto's move to equities' move today. \
If crypto is flat while equities are up, state explicitly: this rally is being read \
as a geopolitical relief trade, not a growth re-rating, because growth re-ratings \
lift crypto alongside equities while geopolitical relief trades do not. \
If crypto is outperforming equities, explain why. Never repeat paragraph 1's content. \
Zero banned phrases.]

SECTION 7 — CORPORATE NEWS & HEADLINES
[Apply Rule F materiality filter strictly. 3–5 bullets maximum. \
Each bullet: Company name. Specific event. Direct market implication stated as fact, \
not as "could lead to." If a story is a CEO quote with no capital allocation decision, \
it does not qualify — reframe it around the market implication or drop it. \
Example of correct format: "Chevron — CEO flagged physical crude is trading at a \
significant premium to futures, a divergence that historically precedes a futures \
catch-up rally once risk premium clears." \
Example of wrong format: "Chevron CEO said oil supply is tight, which could affect prices."]

SECTION 8 — WHAT MATTERS NEXT
[3–4 bullets. Every bullet must pass Rule G: exact variable + mechanism + \
directional split with specific levels. Order by market importance for next session. \
The first bullet should always be the most actionable near-term catalyst.]

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
