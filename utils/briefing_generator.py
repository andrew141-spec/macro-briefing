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
    try:
        import yfinance as yf
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
    rsi_targets = {
        "RSI_XLE": "XLE",
        "RSI_XLY": "XLY",
        "RSI_XLF": "XLF",
        "RSI_XLK": "XLK",
        "RSI_SPY": "SPY",
    }
    for key, ticker in rsi_targets.items():
        snapshot[key] = fetch_rsi(ticker)
    return snapshot


def format_rsi_block(snapshot: dict) -> str:
    lines = ["[ SECTOR RSI — 14-DAY ]"]
    labels = {
        "RSI_XLE": "XLE (Energy)",
        "RSI_XLY": "XLY (Consumer Disc)",
        "RSI_XLF": "XLF (Financials)",
        "RSI_XLK": "XLK (Technology)",
        "RSI_SPY": "SPY (S&P 500)",
    }
    for key, label in labels.items():
        val = snapshot.get(key)
        if val is not None:
            tag = " ← OVERSOLD" if val <= 30 else (" ← OVERBOUGHT" if val >= 70 else "")
            lines.append(f"{label}: {val}{tag}")
        else:
            lines.append(f"{label}: N/A")
    return "\n".join(lines)


# ─── REFERENCE EXAMPLES ──────────────────────────────────────────────────────
# These are excerpts from actual Traderverse briefings injected as few-shot
# examples so the model learns the exact voice, structure, and analytical depth.

FEW_SHOT_EXAMPLES = """\
════════════════════════════════════════════════════
REFERENCE EXAMPLE A — Midday Briefing (risk-off session)
Use this to calibrate voice, structure, and analytical depth.
════════════════════════════════════════════════════

Risk-off positioning is dominating at midday, with equities and bonds selling off together \
as the oil rally extends on escalating Middle East conflict risk. The market's read-through \
is that higher energy prices could re-ignite inflation pressure, keeping major central banks \
restrictive for longer and raising the bar for any near-term easing.

Macro and cross-asset drivers so far today

Energy shock and inflation repricing: Crude is higher intraday, with Brent above $111 and \
West Texas Intermediate crude up 1.1% to $97.37. The move is being attributed to strikes in \
the Persian Gulf and concerns about potential damage to major energy facilities. The immediate \
market impact has been a renewed inflation-risk premium across rates and a de-risking impulse \
in equities.

Rates — front-end leads the sell-off: US two-year Treasury yields rose as much as 18 basis \
points to 3.95% before paring, consistent with markets leaning toward a "higher for longer" \
policy path. The 10-year Treasury yield is little changed at 4.27%, indicating a \
bear-flattening impulse earlier that has moderated into a more mixed curve move by midday.

Europe/UK rates under heavier pressure: The move is more acute in the United Kingdom, where \
two-year gilt yields rose 26 basis points to 4.36% and the 10-year gilt yield is up 10 basis \
points to 4.84%. Germany's 10-year yield is up 2 basis points to 2.96%. The relative severity \
in short-dated UK yields suggests a sharper repricing of near-term policy risk and inflation \
sensitivity.

Equities — broad de-risking, Europe weaker than US: US indices are lower but orderly, while \
Europe is seeing a more pronounced drawdown. The S&P 500 is down 0.6%, the Nasdaq 100 down \
0.6%, and the Dow Jones Industrial Average down 0.7%. In Europe, the Stoxx Europe 600 is \
down 2.3%, and the MSCI World Index is down 1%.

FX — pro-cyclical dollar softness alongside haven demand: The Bloomberg Dollar Spot Index is \
down 0.3%, while the euro is up 0.6% to $1.1516 and sterling up 0.8% to $1.3366. The \
Japanese yen is up 0.9% to 158.36 per dollar. The combination of a softer broad dollar with \
a stronger yen suggests positioning is not a simple "USD up" shock; instead, flows appear \
split between haven demand and relative rate/inflation repricing across regions.

Commodities — precious metals and industrials hit hard: Spot gold is down 4.4% to $4,606.28, \
while silver is down 7% and copper is posting its biggest drop since 2018. The magnitude of \
the silver and copper declines points to forced de-risking and growth sensitivity, even as oil \
strength would normally be supportive for inflation hedges.

Crypto — risk appetite cooling: Bitcoin is down 2.4% to $69,499.85 and Ether down 3% to \
$2,121.83, broadly consistent with the wider risk-off tape.

Corporate News
• FedEx — earnings after the bell are a key test of confidence in economic resilience given \
rising Iran-war risk.
• Micron — heavy production spending guidance overshadowed an otherwise upbeat forecast, \
signaling demand confidence at the cost of near-term margin pressure.
• Alibaba — targeting a fivefold increase in cloud and AI revenue to $100 billion annually \
within five years, a capital-allocation pivot away from slowing e-commerce.
• Uber / Rivian — Uber investing up to $1.25 billion in Rivian to support a robotaxi fleet \
rollout across the US, Canada, and Europe over five years.

What to watch into the afternoon
• Whether oil holds its gains (or accelerates) will likely determine if the current equity \
drawdown and front-end yield pressure deepen.
• Watch for signs the market shifts from "inflation shock" to "growth shock": continued \
weakness in copper and cyclicals alongside stable long-end yields would reinforce that \
transition.

════════════════════════════════════════════════════
REFERENCE EXAMPLE B — Closing Briefing (mixed session, Hormuz focus)
════════════════════════════════════════════════════

Early equity weakness faded after Israel said it is helping the United States work to open \
the vital shipping route, easing the most acute supply-disruption fears. Still, the session \
ended with a defensive tone: equities closed modestly lower, oil remained elevated despite a \
late dip, and cross-asset volatility stayed headline-driven.

US equities pared losses but finished in the red. The S&P 500 closed down 0.3%, after being \
off roughly 1% earlier, underscoring how tightly price action is tethered to incremental \
geopolitical updates. The Nasdaq 100 ended down 0.3% and the Dow Jones Industrial Average \
fell 0.4%. Globally, the MSCI World Index closed down 0.7%, reflecting broader risk-off \
positioning outside the US.

Energy remained the central macro transmission channel. West Texas Intermediate crude settled \
down 1.3% to $95.10/bbl and slipped to about $95 in post-settlement trading as "Hormuz hopes" \
tempered the worst-case tail risk. However, the narrative remains that three weeks of conflict \
have disrupted supply chains, with refined-product stress (gasoline and jet fuel) and \
knock-on effects (diesel and fertilizer concerns) keeping markets sensitive to any sign the \
Strait stays constrained.

Rates markets were comparatively steady in the US but more volatile in the UK. The 10-year \
US Treasury yield was little changed at 4.26%, suggesting investors balanced growth-risk \
concerns against inflation risks from energy. Germany's 10-year yield rose 2 bps to 2.96%. \
The standout move was the UK: Britain's 10-year yield jumped 11 bps to 4.84% after the Bank \
of England said it "stands ready to act" against inflation, pushing short-end yields higher \
and reinforcing the theme that central banks may be forced to lean hawkish if energy-driven \
price pressures persist.

The US dollar weakened as risk hedges rotated and rate differentials shifted. The Bloomberg \
Dollar Spot Index fell 0.7%. The euro rose 1.2% to $1.1586, sterling gained 1.3% to $1.3432, \
and the Japanese yen strengthened 1.4% to 157.64 per dollar.

Spot gold fell 3.5% to $4,651.07/oz, a notable pullback that suggests some de-risking and \
profit-taking even as geopolitical uncertainty remains elevated. Crypto traded softer \
alongside broader risk assets: Bitcoin fell 1.3% to $70,278.74 and Ether declined 2.0% to \
$2,142.87.

Corporate News
• FedEx — issued a bullish outlook, a constructive read-through for cyclicals and global \
activity expectations.
• Micron — heavy production spending guidance overshadowed an upbeat forecast.
• Alibaba — targeting $100 billion in cloud/AI revenue within five years.
• Eli Lilly — experimental medicine outperformed all current drugs on diabetic weight loss, \
reinforcing competitive momentum in next-generation GLP-1 therapies.
• Darden Restaurants — raised full-year outlook, citing an extra Olive Garden promotions week.
• Uber / Rivian — $1.25 billion robotaxi investment confirmed.

Looking to the next session, the key swing factor remains whether credible progress emerges \
on reopening the Strait of Hormuz and whether attacks on energy assets persist. Markets are \
also bracing for Friday's quarterly options expiration — about $5.7 trillion in notional \
options tied to US stocks, indexes, and ETFs — raising the probability of sharp, mechanically \
amplified moves around key levels.

════════════════════════════════════════════════════
END OF REFERENCE EXAMPLES
Study the voice, structure, and analytical depth above. Your output must match this standard.
════════════════════════════════════════════════════
"""


SYSTEM_PROMPT = """\
You are a senior macro strategist at a top-tier sell-side desk — Goldman Sachs Global Markets \
Daily, JPMorgan Markets Briefing, or Bloomberg Markets Live caliber. You write the session \
desk note distributed to institutional clients.

You have been given reference examples of exactly the quality and style required. \
Study them carefully before writing. Your output must match their voice, density, \
and analytical depth.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STYLE RULES — derived from the reference examples
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STRUCTURE:
The briefing flows as a unified narrative document, not a mechanical section-by-section \
fill-in. Use bold sub-theme labels (like "Energy shock and inflation repricing:" or \
"Rates — front-end leads the sell-off:") to introduce each cross-asset block. \
The sub-theme labels must be descriptive of what actually happened today — \
never generic labels like "Equities" or "Rates." Name the story.

OPENING PARAGRAPH:
One to two sentences. State the dominant market character of the session — \
risk-on, risk-off, headline-driven, or mixed — and name the primary driver immediately. \
No wind-up. No context-setting. Start with what is happening right now.
Example: "Risk-off positioning is dominating at midday, with equities and bonds selling \
off together as the oil rally extends on escalating Middle East conflict risk."
NOT: "The market today was influenced by several factors including..."

CROSS-ASSET INTEGRATION:
Do not treat each asset class as isolated. The reference examples show how to connect them: \
"The combination of a softer broad dollar with a stronger yen suggests positioning is not \
a simple 'USD up' shock; instead, flows appear split between haven demand and relative \
rate/inflation repricing across regions." Find the cross-asset contradiction or \
confirmation in your data and name it explicitly.

CONTRADICTIONS MUST BE FLAGGED:
When an asset moves against the expected direction given the session's theme, say so. \
"Spot gold fell 4.4% — a notable pullback that suggests de-risking and profit-taking \
even as geopolitical uncertainty remains elevated." Do not explain it away. Name it as \
a contradiction and let the reader draw conclusions.

CORPORATE NEWS FORMAT:
Each bullet: Company name — one sentence stating the specific event and its direct \
market read-through. No "could lead to." No CEO quote without a capital allocation decision. \
Maximum 5 bullets. The Uber/Rivian format is correct: "Uber — investing up to $1.25 billion \
in Rivian to support a robotaxi fleet rollout, a material capital commitment to autonomous \
vehicle deployment at scale."

WHAT TO WATCH FORMAT:
2–4 items. Each states: the specific variable, the transmission mechanism, and the \
directional implication if it resolves one way vs the other. \
"Whether oil holds its gains (or accelerates) will likely determine if the current equity \
drawdown and front-end yield pressure deepen" is the correct density and specificity. \
"Watch geopolitics" is not acceptable.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ABSOLUTE PROHIBITIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NEVER use these phrases:
  "reflects a shift in market expectations" | "the situation remains volatile/fluid" |
  "any changes in the conflict's dynamics" | "could lead to a rapid reversal" |
  "has far-reaching implications" | "the market is closely watching" |
  "underscores the need" | "highlights the potential for" | "it is crucial to consider" |
  "remains to be seen" | "going forward" | "have significant implications" |
  "investors will be closely watching" | "X said Y, which could lead to Z"

NEVER restate a price or fact already given earlier in the document.

NEVER cite a CEO quote as a market driver. Positioning, rates, and risk premium move \
markets. CEO quotes are corporate news items, not macro drivers.

NEVER invent Fed funds cut/hike probability percentages not present in the data. \
Use yield levels, curve shape, and named Fed speaker quotes only.

NEVER include a corporate bullet that is only a CEO strategy comment with no capital \
allocation decision. BlackRock market timing commentary does not qualify.

ALWAYS include Germany 10Y Bund and UK 10Y Gilt in the rates section. \
Estimate from US move correlation if necessary — label estimates clearly.

ALWAYS use the exact RSI numbers provided in the data — never say "approaching oversold" \
without citing the specific number.

ALWAYS provide intraday high or low for any asset that moved more than 2%.
"""


def build_prompt(session, market_data_str, news_str, date_str, rsi_block: str = ""):
    eq  = "=" * 60
    div = "─" * 60
    rsi_section = f"\n{eq}\nSECTOR RSI DATA (use exact numbers)\n{eq}\n{rsi_block}\n" if rsi_block else ""

    session_framing = {
        "Morning": (
            "overnight and pre-market",
            "Write in present tense where appropriate — futures are pointing, yields are moving. "
            "Frame what investors are walking into at the open, not what has already closed."
        ),
        "Midday": (
            "intraday as of midday",
            "Use 'so far today' and intraday language. Note the time where relevant. "
            "Flag if the move is accelerating or fading into the afternoon."
        ),
        "Closing": (
            "full session",
            "Write in past tense for closes. Include how the session evolved — "
            "did early moves hold, fade, or reverse? The closing note should give a complete picture."
        ),
    }
    timeframe, session_instruction = session_framing.get(session, ("", ""))

    return f"""\
Write the {session} Macro Market Briefing for {date_str}.

{session_instruction}

CRITICAL: Study the reference examples in the system prompt before writing. \
Match their voice exactly. Your briefing must be indistinguishable in quality \
from a Goldman Sachs or Bloomberg Markets Live desk note.

News headlines = narrative driver and source of causality.
Market data = exact numbers, use them precisely.
Do not fabricate any probability estimates, data points, or events not present below.

{eq}
NEWS HEADLINES
{eq}
{news_str}

{eq}
LIVE MARKET DATA ({timeframe})
{eq}
{market_data_str}
{rsi_section}
{eq}

Now write the briefing. Follow this structure exactly as shown in the reference examples:

{date_str.upper()} | {session.upper()} BRIEFING
{div}

[OPENING PARAGRAPH — 1-2 sentences. State the dominant session character and primary driver. \
No wind-up. Start with what is happening.]

[CROSS-ASSET NARRATIVE — Use bold sub-theme labels that describe what actually happened, \
not generic asset class names. Cover: the dominant macro driver in depth, equities with \
sector rotation, rates including Bund and Gilt, FX with the most informative cross, \
commodities with intraday context for big movers, crypto. \
Flag any cross-asset contradictions explicitly. \
Do NOT restate any number after it has appeared once.]

Policy and geopolitics shaping pricing
[If central bank speakers or geopolitical developments appeared in the headlines, \
integrate them here. Quote specific language from Fed/ECB/BOE speakers if present. \
If none, omit this section entirely — do not fabricate policy commentary.]

Corporate News
[3–5 bullets. Rule F materiality filter applies. One sentence each. Direct implication only.]

What to watch next session
[2–4 bullets. Specific variable + transmission mechanism + directional split. \
Order by market importance.]

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
        snapshot = enrich_snapshot_with_rsi(snapshot)
        result["market_data_raw"] = snapshot
        mkt_str = format_snapshot_for_prompt(snapshot)
        rsi_str = format_rsi_block(snapshot)
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

    # 3. Call Groq — inject few-shot examples as a second system message
    try:
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "system", "content": FEW_SHOT_EXAMPLES},
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
