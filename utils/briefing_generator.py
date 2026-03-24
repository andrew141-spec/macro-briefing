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


def fetch_rsi(ticker_symbol: str, period: int = 14) -> float | None:
    """
    Calculate RSI for a given Yahoo Finance ticker using yfinance.
    Returns the most recent RSI value or None on failure.
    """
    try:
        import yfinance as yf
        import pandas as pd
        df = yf.download(ticker_symbol, period="60d", interval="1d",
                         auto_adjust=True, progress=False)
        if df.empty or len(df) < period + 1:
            return None
        close = df["Close"].squeeze()
        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(period).mean()
        loss  = (-delta.clip(upper=0)).rolling(period).mean()
        rs    = gain / loss
        rsi   = 100 - (100 / (1 + rs))
        val   = float(rsi.dropna().iloc[-1])
        return round(val, 1)
    except Exception:
        return None


def enrich_snapshot_with_rsi(snapshot: dict) -> dict:
    """
    Add RSI values for key sector ETFs to the snapshot dict.
    Runs after the main market data fetch.
    """
    rsi_targets = {
        "RSI_XLE":  "XLE",   # Energy
        "RSI_XLY":  "XLY",   # Consumer Discretionary
        "RSI_XLF":  "XLF",   # Financials
        "RSI_XLK":  "XLK",   # Technology
        "RSI_SPY":  "SPY",   # S&P 500 broad
        "RSI_VIX":  "^VIX",  # VIX
    }
    for key, ticker in rsi_targets.items():
        snapshot[key] = fetch_rsi(ticker)
    return snapshot


def format_rsi_block(snapshot: dict) -> str:
    """Format RSI values into a readable block for the prompt."""
    lines = ["[ RSI — 14-DAY ]"]
    labels = {
        "RSI_XLE": "XLE (Energy)",
        "RSI_XLY": "XLY (Consumer Disc)",
        "RSI_XLF": "XLF (Financials)",
        "RSI_XLK": "XLK (Technology)",
        "RSI_SPY": "SPY (S&P 500)",
        "RSI_VIX": "VIX",
    }
    for key, label in labels.items():
        val = snapshot.get(key)
        if val is not None:
            if val <= 30:
                tag = " ← OVERSOLD"
            elif val >= 70:
                tag = " ← OVERBOUGHT"
            else:
                tag = ""
            lines.append(f"{label}: {val}{tag}")
        else:
            lines.append(f"{label}: N/A")
    return "\n".join(lines)


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

RULE C — CAUSAL CHAIN FOR SECTION 1.
The correct transmission sequence is:
  geopolitical/macro event → which asset repriced first and why →
  how that forced a second asset to reprice → what that implies for valuations.
CEO quotes do NOT move markets. Positioning, rates, and risk premium do. \
Find the real mechanism. Never cite a CEO comment as a market driver.

RULE D — INTRADAY CONTEXT FOR BIG MOVERS.
Any asset that moved more than 2%: state the intraday high or low AND settlement. \
Format: "settled -9.7% to $88.74 after touching $84.20 intraday."

RULE E — EUROPEAN RATES ARE MANDATORY.
Section 3 must include Germany 10Y Bund and UK 10Y Gilt. \
Estimate from US move correlation if necessary — label estimates clearly. \
Silent omission is not acceptable.

RULE F — CORPORATE NEWS MATERIALITY THRESHOLD.
Section 7 only includes stories where at least one is true:
  • Capital allocation event >$500M (M&A, LBO, raise, buyback, large redemption)
  • Named activist with disclosed position size
  • Earnings/guidance with sector-level sentiment impact
  • Direct operational connection to the session's dominant macro theme
CEO quotes and strategy commentary WITHOUT a capital allocation decision do NOT qualify. \
BlackRock CEO market timing comments: does not qualify — exclude it. \
Write each bullet as a direct statement of market implication, never "X said Y which could lead to Z."
Correct format: "Chevron — physical crude is trading at a material premium to futures, \
a divergence that historically precedes a futures catch-up rally once the risk premium clears."

RULE G — SECTION 8 SPECIFICITY STANDARD.
Each bullet must contain all three:
  (a) exact variable or event to watch
  (b) transmission mechanism to markets
  (c) directional split with specific price levels where possible
"Watch geopolitics" fails. "Watch whether Iran confirms diplomatic contact — \
confirmation removes ~$8–10/bbl of geopolitical premium from Brent, pulling \
energy breakevens ~15bps lower; denial reverses the session's entire move" passes.

RULE H — SECTION 6 CRYPTO ANALYTICAL STANDARD.
If BTC/ETH are flat while equities rally: state explicitly that this is a geopolitical \
relief trade signal, not a growth re-rating, because genuine growth re-ratings lift \
crypto alongside equities while geopolitical relief trades do not. \
If crypto is outperforming equities, explain why with a specific driver. \
Never repeat paragraph 1's content in paragraph 2.

RULE I — NO FABRICATED PROBABILITIES OR DATA.
NEVER invent Fed funds futures probabilities, cut/hike odds, or any numerical estimate \
not present in the market data or headlines provided. If the data feed does not include \
Fed funds futures pricing, do NOT state a percentage probability of a cut or hike. \
Instead, characterize the shift qualitatively using only what is in the data: \
yield levels, curve shape, and any Fed speaker quotes from the headlines. \
A fabricated "25% chance of a cut" is worse than no estimate at all — \
it will be wrong and will destroy credibility.

RULE J — SECTION 2 RSI STANDARD.
The market data includes real RSI values for key sector ETFs. \
You MUST use the actual RSI numbers provided — do not say "approaching oversold" \
without citing the specific RSI level. State: "XLE RSI at 28.4, the lowest \
since [context if relevant], suggesting the sector is technically oversold." \
If an RSI is between 40–60, note it as neutral and focus on a different technical signal.
"""


def build_prompt(session, market_data_str, news_str, date_str, rsi_block: str = ""):
    div = "─" * 60
    eq  = "=" * 60
    rsi_section = f"\n{eq}\nSECTOR RSI DATA (14-day, use exact numbers in Section 2)\n{eq}\n{rsi_block}\n" if rsi_block else ""

    return f"""\
Write the {session} Macro Market Briefing for {date_str}.

News headlines = narrative driver and source of causality.
Market data = exact numbers, use them precisely.
Do not fabricate any probability estimates, data points, or events not present below.

{eq}
NEWS HEADLINES
{eq}
{news_str}

{eq}
LIVE MARKET DATA
{eq}
{market_data_str}
{rsi_section}
{eq}

{date_str.upper()} | {session.upper()} BRIEFING
{div}

SECTION 1 — MACRO NARRATIVE
[PARAGRAPH 1: Name the dominant event from the headlines in sentence one. Build the \
market mechanism chain: event → first asset to reprice and why → how that forced \
second asset to reprice → what that implies for valuations. No CEO quotes as drivers. \
PARAGRAPH 2: Quality of the move — was it short covering, genuine positioning, or \
low-liquidity amplification? State the bear case the bulls are ignoring today directly \
and without hedging. \
PARAGRAPH 3: The single most important unresolved question for next session, \
phrased as a specific testable condition. \
Then the close snapshot:]

At the close:
• [all major equity indices: direction, exact pct, exact level]

Rates: [US 2Y and 10Y exact yields]
FX: [DXY level + 2 key pairs with exact levels and pct]
Commodities: [oil settlement exact price and pct, gold exact price and pct]
Crypto: [BTC and ETH exact prices and pct moves]

SECTION 2 — EQUITIES
[PARAGRAPH 1: Do NOT restate any index level already in Section 1. Lead with SECTOR \
ROTATION — which sectors won and lost, name the specific ETFs (XLE, XLY, XLF, XLK etc), \
and explain the mechanism connecting them to today's macro driver. \
PARAGRAPH 2: Use the ACTUAL RSI numbers from the RSI data block provided. Cite exact \
levels — do not say "approaching oversold" without the number. Note any key technical \
level being tested (support, resistance, moving average). Add short interest or \
options flow context if available from headlines. Zero index-level restatement. \
Zero banned phrases from Rule B.]

SECTION 3 — RATES
[PARAGRAPH 1: Exact yields for US 2Y, 10Y, 30Y. State the 2s10s spread and interpret \
its direction. Germany 10Y Bund and UK 10Y Gilt are REQUIRED — estimate from US move \
correlation and label as estimate. \
PARAGRAPH 2: Characterize the shift in Fed expectations using ONLY what is in the data — \
yield levels, curve shape, and any Fed speaker quote from the headlines. \
DO NOT invent cut/hike probability percentages. If a Fed speaker appeared in the \
headlines, quote their specific concern precisely. State what the curve shape implies \
about terminal rate expectations without fabricating a number.]

SECTION 4 — COMMODITIES
[PARAGRAPH 1: Oil leads if it moved >2%. REQUIRED: intraday extreme AND settlement. \
Explain the specific mechanism — geopolitical premium unwind, physical vs futures \
divergence, positioning flush. Do NOT re-explain the geopolitical narrative from \
Section 1 — add commodity-market-specific detail. \
PARAGRAPH 2: Gold — is it confirming or contradicting the risk narrative? \
State which pattern: falling oil + flat/falling gold = clean risk-off unwind; \
falling oil + rising gold = stagflation hedge. Then name the specific CPI components \
affected and approximate magnitude.]

SECTION 5 — FX
[PARAGRAPH 1: DXY direction with specific driver. Exact levels for EUR, GBP, JPY \
with direction and pct. Do NOT re-explain the macro theme. \
PARAGRAPH 2: Name the single most informative currency cross, give the level, \
interpret what it signals about relative growth or monetary policy. \
State the specific level or condition that would change the FX thesis. \
Do NOT end with any uncertainty caveat. End forward-looking with a level.]

SECTION 6 — CRYPTO
[PARAGRAPH 1: BTC and ETH exact prices and pct moves. Pure equity beta or \
crypto-specific driver? Check headlines for ETF flows, regulation, stablecoin activity. \
PARAGRAPH 2: Compare crypto's move to equities' move. Apply Rule H — if flat while \
equities rally, state the geopolitical relief trade interpretation explicitly. \
Never repeat paragraph 1. Zero banned phrases.]

SECTION 7 — CORPORATE NEWS & HEADLINES
[Apply Rule F strictly. 3–5 bullets. Exclude any story that is only a CEO quote \
with no capital allocation decision — BlackRock market timing comments do not qualify. \
Direct implication only, never "could lead to." See Rule F for correct format.]

SECTION 8 — WHAT MATTERS NEXT
[3–4 bullets. Every bullet passes Rule G: exact variable + mechanism + \
directional split with specific levels. Order by market importance.]

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
        # Enrich with RSI data
        snapshot = enrich_snapshot_with_rsi(snapshot)
        result["market_data_raw"] = snapshot
        mkt_str  = format_snapshot_for_prompt(snapshot)
        rsi_str  = format_rsi_block(snapshot)
        result["market_data_str"] = mkt_str
    except Exception as e:
        result["error"] = f"Market data fetch failed: {e}"
        mkt_str = "Market data unavailable — use conservative approximations."
        rsi_str = ""

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
                {"role": "user",   "content": build_prompt(session, mkt_str, news_str, date_str, rsi_str)},
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
