"""
Briefing Generator — Traderverse institutional quality.
Gemini 2.0 Flash (primary) + Yahoo Finance + RSS/GDELT news injection.
Upgraded: intraday ranges, prior-close context, strategist commentary section,
          session arc narrative, sector RSI, European rates.
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

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


def get_session(now_et=None):
    if now_et is None:
        now_et = datetime.now(ET)
    hour, minute = now_et.hour, now_et.minute
    if 8 <= hour <= 10 and not (hour == 8 and minute < 30):
        return "Morning"
    elif 11 <= hour <= 13:
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
        return round(float(rsi.dropna().iloc[-1]), 1)
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


# ─── FEW-SHOT REFERENCE EXAMPLES ─────────────────────────────────────────────

FEW_SHOT_EXAMPLES = """\
════════════════════════════════════════════════════
REFERENCE EXAMPLE A — Midday Briefing (risk-off, energy shock)
Study this for voice, sub-label style, and cross-asset integration.
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

Commodities — precious metals and industrials hit hard: Spot gold is down 4.4% to $4,606.28 \
(session low: $4,571), while silver is down 7% and copper is posting its biggest drop since \
2018. The magnitude of the silver and copper declines points to forced de-risking and growth \
sensitivity, even as oil strength would normally be supportive for inflation hedges.

Crypto — risk appetite cooling: Bitcoin is down 2.4% to $69,499.85 and Ether down 3% to \
$2,121.83, broadly consistent with the wider risk-off tape.

The divergence between crypto and equities is minimal today — both are selling off in tandem, \
consistent with a genuine risk-off impulse rather than an idiosyncratic equity shock. When \
both move together, it signals broad liquidation rather than sector rotation.

Strategist commentary and desk color

Thierry Wizman at Macquarie Group highlighted that central banks will recall how commodity \
inflation led the 2022 consumer inflation surge, raising the risk that policymakers stay \
restrictive even as growth slows. Ed Yardeni raised the probability of a "market meltdown" \
to 35% for the rest of the year (from 20%) and cut the odds of a "melt-up" to 5% (from 20%). \
JPMorgan's Andrew Tyler turned "tactically bearish," warning traders appear underprepared for \
a correction that could take the S&P 500 down as much as 10% from its peak.

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
• WTI above $97 — a close above $100 re-ignites the inflation-repricing that pushed \
front-end yields 18bps higher this morning; a reversal below $95 reduces the immediate \
policy tightening risk and likely lifts equities.
• Watch for a market shift from "inflation shock" to "growth shock": continued weakness in \
copper (now at its biggest drop since 2018) and cyclicals alongside stable long-end yields \
would reinforce that transition and begin to price Fed cuts rather than hikes.

════════════════════════════════════════════════════
REFERENCE EXAMPLE B — Closing Briefing (session arc, partial geopolitical resolution)
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

Spot gold fell 3.5% to $4,651.07/oz — a notable contradiction in a risk-off session, \
suggesting forced de-risking and profit-taking outweighed safe-haven demand. Crypto traded \
softer alongside broader risk assets: Bitcoin fell 1.3% to $70,278.74 and Ether declined \
2.0% to $2,142.87. The move in crypto was narrower than equities on a percentage basis, \
consistent with a geopolitical relief trade rather than a clean growth re-rating.

Corporate News
• FedEx — issued a bullish outlook, a constructive read-through for cyclicals and global \
activity expectations.
• Micron — heavy production spending guidance overshadowed an upbeat forecast.
• Alibaba — targeting $100 billion in cloud/AI revenue within five years.
• Eli Lilly — experimental medicine outperformed all current drugs on diabetic weight loss, \
reinforcing competitive momentum in next-generation GLP-1 therapies.
• Uber / Rivian — $1.25 billion robotaxi investment confirmed.

Looking to the next session, the key swing factor remains whether credible progress emerges \
on reopening the Strait of Hormuz and whether attacks on energy assets persist. Markets are \
also bracing for Friday's quarterly options expiration — about $5.7 trillion in notional \
options tied to US stocks, indexes, and ETFs — raising the probability of sharp, mechanically \
amplified moves around key levels. In rates, watch whether the UK gilt move extends: a \
sustained break above 4.90% on the 10-year would likely force further risk-off rotation \
globally and raise questions about whether the Bank of England needs to hike ahead of schedule.

════════════════════════════════════════════════════
END OF REFERENCE EXAMPLES — match this standard exactly.
════════════════════════════════════════════════════
"""


SYSTEM_PROMPT = """\
You are a senior macro strategist at a top-tier sell-side desk — Goldman Sachs Global Markets \
Daily, JPMorgan Markets Briefing, or Bloomberg Markets Live caliber. You write the session \
desk note distributed to institutional clients.

You have been given reference examples of exactly the quality and style required. \
Study them carefully. Your output must be indistinguishable in voice, density, \
and analytical depth from those examples.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STYLE RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STRUCTURE:
The briefing is a unified narrative — not section headers filled in mechanically. \
Sub-theme labels must describe what actually happened today: \
"Energy shock and inflation repricing:" is correct. "Equities:" is not.

OPENING:
1–2 sentences. State the session's dominant character (risk-on / risk-off / mixed / \
headline-driven) and name the primary driver immediately. End after stating what is \
happening — no hedges, no "which could lead to."

CROSS-ASSET INTEGRATION:
Connect asset classes. Find the confirmation or contradiction and name it explicitly. \
"The softer dollar alongside a stronger yen suggests flows are split between haven \
demand and relative rate repricing — not a simple 'USD up' shock."

CONTRADICTIONS MUST BE NAMED:
If gold falls in a risk-off session, say so and label it a contradiction. \
Do NOT explain it away — state it and let the reader decide.

SESSION ARC (CLOSING ONLY):
Describe how the session evolved: did early weakness reverse? What headline flipped the \
tape? What was the intraday high/low for the dominant asset? Give a complete picture.

INTRADAY RANGE:
For any asset that moved more than 2%, cite the intraday high or low from the data. \
"WTI traded as high as $101 before settling at $96" is correct density.

PRIOR CLOSE CONTEXT (MORNING ONLY):
For the first mention of any commodity or futures price in a morning briefing, \
contrast it with the prior session close. "WTI is down 6% to $89, after settling \
at $95 Thursday" is correct.

CORPORATE NEWS:
Company — one sentence, specific event, direct market read-through. \
No "could lead to." No CEO quote without a capital allocation decision. \
3–5 bullets maximum.

WHAT TO WATCH:
2–4 bullets. Each: [Specific variable] — if [condition A + level], [mechanism] → \
[asset] moves [direction/level]; if [condition B], [opposite]. \
Every bullet needs a checkable level or condition. \
BANNED words in this section: "could" / "might" / "may" / "would" / "remains to be seen" / \
"will be closely watched" / "will be important" / "could impact markets" / "could signal" / \
"could lead to" / "it could"

STRATEGIST COMMENTARY (when present in headlines):
Format: "[Name] at [Firm] [warned/argued/said] [specific quantified view]." \
Only include if a named strategist or bank desk offered a specific call with a level \
or probability. Generic market commentary does not qualify.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ABSOLUTE PROHIBITIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NEVER use: "reflects a shift in market expectations" | "the situation remains volatile" |
"could lead to a rapid reversal" | "has far-reaching implications" |
"the market is closely watching" | "underscores the need" |
"remains to be seen" | "going forward" | "investors will be closely watching"

NEVER restate a price already given earlier in the document.
NEVER fabricate Fed funds probability percentages not in the data.
NEVER include a corporate bullet that is only a CEO strategy comment.
NEVER use generic sub-labels like "Equities:" or "Rates:" — always name the story.

ALWAYS include Germany 10Y Bund and UK 10Y Gilt in the rates section.
ALWAYS use the exact RSI numbers provided.
ALWAYS cite intraday high or low for any asset that moved more than 2%.
"""


def build_prompt(session, market_data_str, news_str, date_str, rsi_block: str = ""):
    eq  = "=" * 60
    div = "─" * 60
    rsi_section = (
        f"\n{eq}\nSECTOR RSI DATA (use exact numbers — never say 'approaching' without citing)\n{eq}\n{rsi_block}\n"
        if rsi_block else ""
    )

    session_framing = {
        "Morning": (
            "overnight and pre-market",
            "Write in present tense — futures are pointing, yields are moving. "
            "For the FIRST mention of any commodity or futures price, state it versus the prior session close. "
            "Frame what investors are walking into at the open."
        ),
        "Midday": (
            "intraday as of midday",
            "Use present tense and 'so far today' language. "
            "Note the time where it adds precision. "
            "Flag if a move is accelerating or fading. "
            "For any asset that moved >2%, cite the intraday high or low from the range data."
        ),
        "Closing": (
            "full session",
            "Write in past tense for closes. "
            "REQUIRED: describe the session arc — did early moves hold, fade, or reverse? "
            "What specific headline or data point changed the tape? "
            "What was the intraday range for the dominant asset? "
            "The closing note must give a complete picture of how the session evolved."
        ),
    }
    timeframe, session_instruction = session_framing.get(session, ("", ""))

    return f"""\
Write the {session} Macro Market Briefing for {date_str}.

{session_instruction}

CRITICAL: Match the voice and analytical depth of the reference examples exactly. Your briefing must read like a Goldman Sachs or Bloomberg Markets Live desk note.

News headlines = narrative driver and source of causality.
Market data = exact numbers. Use intraday ranges where provided in the data.
Do not fabricate any data points, quotes, or probability percentages not present below.

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

STEP 1 — DATA AUDIT (silent internal reasoning — do NOT include in output):

Answer every question below using ONLY the numbers in the market data above.
Complete this audit before writing a single word of the briefing.

Q1. EQUITIES: Are the major indices (S&P 500, Nasdaq, Dow) up or down?
    By what exact percentage? If futures show 0.00% change, markets are FLAT — do NOT
    describe them as selling off or rallying. Opening narrative must reflect reality.

Q2. OIL DIRECTION: Calculate (current WTI price − prior close) / prior close x 100.
    If WTI is DOWN vs prior close, this is NOT an oil rally — correct the narrative.
    Brent: do the same. Note the intraday high and low if provided.

Q3. DOMINANT DRIVER: What single macro theme do the top 5 headlines point to?
    Name it in three words or fewer. This becomes the opening sentence driver.

Q4. CONTRADICTIONS — check every one of these:
    - Is gold falling in a risk-off session? (flag it)
    - Is crypto rising while equities fall, or vice versa? (flag it)
    - Are bonds selling off alongside equities? (flag it — bonds usually rally in risk-off)
    - Is any sector ETF moving strongly against the session theme? (flag it)
    Every contradiction flagged here MUST appear explicitly in the cross-asset narrative.

Q5. EUROPEAN RATES: Are DE10Y and UK10Y in the data?
    If N/A → estimate Bund = US 10Y move × 0.45, label "(est.)".
    Estimate Gilt = US 10Y move × 0.65, label "(est.)".
    Both MUST appear in the rates section — skipping them is not permitted.

Q6. STRATEGIST FILTER: Does the STRATEGIST COMMENTARY section contain a named individual
    AND a specific number (probability %, price target, index level)?
    YES → include the Strategist section.
    NO named person with a specific number → OMIT the section entirely.

Q7. CORPORATE MATERIALITY: For each corporate headline, confirm at least one of:
    (a) capital event >$500M, (b) M&A/LBO/activist stake, (c) earnings or guidance
    that moves sector sentiment, (d) direct operational tie to today's macro driver.
    OpenAI risk disclosures = NO. Redemption rates without capital decision = NO.
    CEO strategy quotes without capital allocation = NO.

Only after completing this audit silently, write the briefing below.

{eq}

STEP 2 — WRITE THE BRIEFING:

{date_str.upper()} | {session.upper()} BRIEFING
{div}

[OPENING — 1-2 sentences. Session character must match Q1-Q3 audit results, not assumptions.
If equities are flat, say mixed/subdued — not risk-off. Name the primary driver. No hedges.]

[CROSS-ASSET NARRATIVE
Sub-theme labels must describe what actually happened — never generic labels.
REQUIRED: dominant macro driver, equities/sector rotation,
rates (Bund + Gilt REQUIRED — estimate and label if N/A), FX, commodities, crypto.

CRYPTO — two paragraphs required:
  Para 1: exact prices, pct moves, intraday range if >2%. Note any crypto-specific driver.
  Para 2: compare crypto move to equities. Same direction = genuine risk-on/off.
  Diverging = state explicitly and name the implication. Never repeat Para 1 numbers.

COMMODITIES: Morning briefing — first oil mention must include current vs. prior close.
  Any move >2%: cite the intraday high or low from the range data.

CONTRADICTIONS: Every item flagged in Q4 must appear in the narrative.
  Do not explain contradictions away — name them and let the reader decide.]

Strategist commentary and desk color
[Include ONLY if Q6 audit confirmed a named person with a specific quantified call.
"[Name] at [Firm] [warned/argued/noted] [specific level or probability]."
OMIT ENTIRELY if no qualifying entry exists.]

Policy and geopolitics shaping pricing
[Include ONLY if Fed/ECB/BOE/BOJ speakers or major geopolitical policy decisions appeared.
Quote exact language. State the specific policy path implication — not generic framing.
OMIT ENTIRELY if nothing material appeared.]

Corporate News
[Only bullets that passed Q7. 3-5 maximum. One sentence each.
Direct market implication stated as fact. No "could lead to." No CEO strategy quotes.]

What to watch next session
[2-4 bullets. Each bullet MUST follow this exact format:
"[Specific variable] — if [condition A including a specific price/level],
[named mechanism] pushes [specific asset] to [specific level];
if [condition B], [opposite mechanism and outcome]."

BANNED anywhere in this section:
"could" / "might" / "may" / "would" / "remains to be seen" /
"will be closely watched" / "will be important" / "could impact markets" /
"could signal" / "could lead to" / "it could"

Every bullet must contain at least one specific price level checkable tomorrow morning.]

{div}
Powered by Traderverse | {date_str}
"""


def generate_briefing(gemini_api_key="", groq_api_key="", alpha_vantage_key="", session=None, force_session=None):
    now_et   = datetime.now(ET)
    date_str = now_et.strftime("%B %d, %Y").replace(" 0", " ")
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
        headlines = fetch_headlines(max_per_feed=10, max_total=45)
        result["news_headlines"] = headlines
        news_str = format_headlines_for_prompt(headlines)
    except Exception as e:
        result["error"] = (result.get("error") or "") + f" | News fetch failed: {e}"
        news_str = "Live headlines unavailable — anchor analysis to market data moves."

    # 3. Build full prompt
    full_prompt = (
        SYSTEM_PROMPT + "\n\n"
        + FEW_SHOT_EXAMPLES + "\n\n"
        + build_prompt(session, mkt_str, news_str, date_str, rsi_str)
    )
    prompt_chars = len(full_prompt)
    result["prompt_chars"] = prompt_chars

    # 4. Call Gemini
    if gemini_api_key:
        try:
            payload = {
                "contents": [
                    {"parts": [{"text": full_prompt}]}
                ],
                "generationConfig": {
                    "temperature": 0.2,
                    "topP": 0.85,
                    "maxOutputTokens": 4096,
                },
            }
            resp = requests.post(
                f"{GEMINI_API_URL}?key={gemini_api_key}",
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=180,
            )
            resp.raise_for_status()
            data = resp.json()
            # Check for blocked content
            if "candidates" not in data:
                block_reason = data.get("promptFeedback", {}).get("blockReason", "unknown")
                result["error"] = (result.get("error") or "") + f" | Gemini blocked: {block_reason} | full response: {str(data)[:300]}"
            else:
                candidate = data["candidates"][0]
                finish_reason = candidate.get("finishReason", "")
                if finish_reason == "SAFETY":
                    result["error"] = (result.get("error") or "") + f" | Gemini safety block"
                else:
                    result["briefing"] = candidate["content"]["parts"][0]["text"]
                    return result
        except requests.exceptions.Timeout:
            result["error"] = (result.get("error") or "") + f" | Gemini timeout after 180s (prompt was {prompt_chars} chars)"
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else "?"
            body   = e.response.text[:600] if e.response else "no response body"
            result["error"] = (result.get("error") or "") + f" | Gemini HTTP {status}: {body}"
        except KeyError as e:
            result["error"] = (result.get("error") or "") + f" | Gemini parse error (missing key {e}): {str(data)[:300]}"
        except Exception as e:
            result["error"] = (result.get("error") or "") + f" | Gemini error ({type(e).__name__}): {e}"

    # 5. Fallback to Groq if Gemini fails or no key provided
    if groq_api_key:
        GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
        GROQ_MODEL   = "llama-3.3-70b-versatile"
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
                timeout=180,
            )
            resp.raise_for_status()
            result["briefing"] = resp.json()["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            result["error"] = (result.get("error") or "") + f" | Groq timeout after 180s"
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else "?"
            body   = e.response.text[:600] if e.response else "no response body"
            result["error"] = (result.get("error") or "") + f" | Groq HTTP {status}: {body}"
        except Exception as e:
            result["error"] = (result.get("error") or "") + f" | Groq error ({type(e).__name__}): {e}"

    return result
