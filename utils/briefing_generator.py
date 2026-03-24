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
REFERENCE EXAMPLE C — Morning Briefing (de-escalation relief rally)
════════════════════════════════════════════════════

Risk sentiment has improved sharply into the New York morning after President Trump said the \
United States and Iran had "very good" conversations and directed a five-day postponement of \
any military strikes. That shift in tone is driving a classic de-escalation trade: equities \
and bonds are higher, oil is materially lower, and the US dollar is softer.

US equity futures are signaling a strong rebound at the open, with S&P 500 futures up about \
1.6%–1.7%, Nasdaq 100 futures up about 1.6%, and Dow Jones Industrial Average futures up \
about 2.4%. Europe is participating but less dramatically, with the Stoxx Europe 600 up about \
0.9%, while the MSCI World Index is little changed — consistent with a US-led relief rally \
after weekend escalation rhetoric.

Rates are rallying as the market unwinds some of the "insurance" tightening that had been \
priced on the back of higher energy. The two-year US Treasury yield is down about 3 basis \
points to 3.86%, reflecting reduced near-term inflation anxiety. The 10-year US Treasury \
yield is around 4.35%, with the curve's reaction suggesting the dominant driver is lower \
inflation risk premia rather than a sudden deterioration in growth expectations. In Europe, \
Germany's 10-year yield is around 2.98% and Britain's 10-year yield around 3.92%.

Oil is the fulcrum. West Texas Intermediate crude is down about 7.6% to roughly $90.79, \
after settling at $97.94 on Friday. The magnitude matters because the prior spike had revived \
concerns that central banks could be forced to lean more hawkish to prevent energy-driven \
inflation from re-accelerating.

Gold is still lower on the day but off the worst levels, down about 2.5% to roughly $4,381 \
per ounce — a contradiction worth noting. Even with equities rallying and oil retreating, \
gold is not benefiting, suggesting liquidation and real-yield dynamics are the dominant force \
rather than position-building in hedges.

Crypto is participating in the risk rebound, with Bitcoin up about 3.6% to around $70,623 \
and Ether up about 5.1% to around $2,165. Both moving in the same direction as equities \
confirms this as a genuine risk-on impulse rather than idiosyncratic flows; the magnitude \
of Ether's outperformance relative to Bitcoin is consistent with a higher-beta risk-on bid.

Corporate News
• Fannie Mae and Freddie Mac began placing sizable orders to purchase mortgage-backed \
securities, stepping into a market unsettled by wider spreads and elevated volatility.
• UBS Chief Executive Sergio Ermotti said the Iran war could force him to pare back \
spending, a direct capital-allocation signal from a major global bank.

What to watch into the session
• WTI below $90 — sustained crude weakness below $90 validates the de-escalation trade \
and allows front-end yields to drift lower, supporting rate-sensitive equities; a reversal \
back above $95 re-introduces the inflation-tightening narrative and caps the equity rebound.
• Hormuz shipping confirmation — any verified increase in tanker transits is the clearest \
signal that the risk premium can compress durably; absence of confirmation keeps the rally \
fragile and headline-dependent.

════════════════════════════════════════════════════
END OF REFERENCE EXAMPLES — match this standard exactly.
════════════════════════════════════════════════════
"""

SYSTEM_PROMPT = """You are a senior global macro strategist writing a sell-side institutional market briefing for hedge funds and trading desks — Goldman Sachs Global Markets Daily / Bloomberg Markets Live caliber.

You have been given three reference examples of exactly the quality and style required. Study them carefully. Your output must be indistinguishable in voice, density, and analytical depth from those examples.

CORE OBJECTIVE: Produce a single, coherent macro narrative explaining ALL cross-asset price action through ONE dominant driver, CLEAR transmission mechanisms, and EXPLICIT market pricing implications. This is NOT a summary. This is a causal model of markets.

For every major move, state:
  First-order effect: what directly happened
  Second-order effect: how it impacts inflation, growth, or liquidity
  Third-order implication: how it changes policy expectations or positioning

You MUST use institutional pricing language throughout:
  "The market is pricing..." / "This implies..." / "This reflects..." /
  "Positioning suggests..." / "The constraint is..."

STYLE RULES:

STRUCTURE: The briefing is flowing, dense institutional prose. Sub-theme labels are inline narrative signposts describing what actually happened today. "Energy shock and inflation repricing:" is correct. "Equities:" is banned. Prices are woven into sentences, not listed.

OPENING: 1-2 sentences. Identify the single dominant driver and define the macro regime (risk-off, stagflation, growth scare, disinflation, liquidity tightening). State what the market believed before, what changed today, and what is now being repriced. Do NOT open with index percentage moves.

CROSS-ASSET FRAMEWORK: Before covering assets individually, explain how markets are functioning — which variable is leading (oil, rates, dollar) and whether signals are coherent or fragmented. Connect every asset back to the dominant driver via explicit transmission.

RATES — PRIMARY INFORMATION SIGNAL: Break down 2-year (policy expectations) vs 10-year (growth + term premium) separately. Explicitly state what the market is pricing for rate cuts/hikes/timing. Identify tensions: "growth weakening but yields rising = inflation shock regime."

EQUITIES — THROUGH THE MACRO LENS: State index performance briefly, then analyze WHICH factor is driving: rates? earnings? liquidity? positioning? Identify sector leadership and WHY, tied to the macro driver narratively — never as raw ETF tickers and percentages. Link equities explicitly to real yields, oil, and macro expectations. State whether repricing is fundamental or positioning/flow-driven.

COMMODITIES — OIL AS SYSTEMIC VARIABLE: Treat oil as the macro engine. State the supply/demand or geopolitical cause. Explain inflation pass-through and impact on consumers, margins, policy. Include second-order effects: "energy as a tax on growth." Gold must be explained via real yields + dollar dynamics — not "safe haven" alone.

FX — RATE DIFFERENTIALS AND LIQUIDITY: Explain dollar moves via rate differentials, risk sentiment, funding stress. Name the mechanism explicitly: "softer dollar + stronger yen suggests flows split between haven demand and relative rate repricing."

CROSS-ASSET CONSISTENCY CHECK: Are assets telling the same story? If not, name the divergence. Stocks up + yields up: growth optimism or inflation concern? Oil up + bonds down: stagflation signal?

POSITIONING AND FLOWS: Explain whether moves are driven by positioning, hedging, forced de-risking, or short covering. Include volatility and liquidity conditions where relevant.

CONTRADICTIONS MUST BE NAMED: Gold falls in risk-off? Say so explicitly. Crypto diverges from equities? Name the implication. Bonds sell off with equities? Flag it. Never skip contradictions.

SESSION ARC (CLOSING ONLY): Describe how the session evolved — early moves hold, fade, reverse? What specific headline changed the tape? Give intraday range for the dominant asset.

INTRADAY RANGE: For any asset that moved more than 2%, cite the intraday high or low.

PRIOR CLOSE CONTEXT (MORNING ONLY): For the first mention of any commodity or futures price, state it versus the prior session close.

EUROPEAN RATES — ALWAYS REQUIRED: Germany 10Y Bund and UK 10Y Gilt MUST appear. If exact levels are in the data, use them. If only US 10Y move is available, estimate:   Bund MOVE = day's US 10Y move in bps times 0.45 → label the estimated move "(est.)"   Gilt MOVE = day's US 10Y move in bps times 0.65 → label the estimated move "(est.)" NEVER multiply the yield level by these factors — only multiply the day's move in bps.

CRYPTO — TWO PARAGRAPHS REQUIRED: Para 1: Exact prices, pct moves, intraday range if >2%. Note any crypto-specific driver. Para 2: Compare direction to equities. Same direction = genuine risk impulse — say so. Diverging = state explicitly and name the implication. Never repeat Para 1 numbers.

POLICY IMPLICATIONS: Explain how today's moves affect Fed constraints. State clearly what the Fed can vs cannot do given the inflation/growth trade-off.

FORWARD-LOOKING SCENARIOS — MANDATORY: End with conditional logic for 2-4 key variables. For each: if X continues → Y outcome; if X reverses → Z outcome. Must feel like trading guidance. Every scenario must have a specific, checkable level.

CORPORATE NEWS: Company — one sentence, specific event, direct market read-through. No "could lead to." No CEO quote without a capital allocation decision. 3-5 bullets max.

FOOTER: End every briefing with exactly: "Powered by Traderverse | DD/MM/YYYY"
Use format 23/03/2026 — NOT "March 23, 2026".

ABSOLUTE PROHIBITIONS:
NEVER open with index percentage moves.
NEVER list sector ETF tickers and raw percentages as data in the text.
NEVER write "stocks fell due to uncertainty" or "investors reacted to news."
NEVER use: "reflects a shift in market expectations" | "the situation remains volatile" |
  "could lead to a rapid reversal" | "has far-reaching implications" |
  "the market is closely watching" | "underscores the need" |
  "remains to be seen" | "going forward" | "investors will be closely watching"
NEVER restate a price already given earlier in the document.
NEVER fabricate Fed funds probability percentages not in the data.
NEVER include a corporate bullet that is only a CEO strategy comment.
NEVER use generic sub-labels like "Equities:" or "Rates:" — always name the story.
NEVER multiply yield levels by 0.45/0.65 — only multiply the day's move in bps.
NEVER skip the two-paragraph crypto requirement.
NEVER skip Germany Bund and UK Gilt in the rates section.
NEVER use "could" / "might" / "may" / "would" in the What to Watch section.
"""



def build_prompt(session, market_data_str, news_str, date_str, rsi_block: str = ""):
    eq  = "=" * 60
    div = "─" * 60
    rsi_section = (
        f"\n{eq}\nSECTOR RSI DATA (use exact numbers — never say 'approaching' without citing)\n{eq}\n{rsi_block}\n"
        if rsi_block else ""
    )

    # Footer date as DD/MM/YYYY
    try:
        from datetime import datetime as _dt
        footer_date = _dt.strptime(date_str, "%B %d, %Y").strftime("%d/%m/%Y")
    except Exception:
        footer_date = date_str

    session_framing = {
        "Morning": (
            "overnight and pre-market",
            "Write in present tense. Open with the macro regime and dominant driver — "
            "NOT with index percentage moves. "
            "For the FIRST mention of any commodity or futures price, contrast with prior session close. "
            "Frame what investors are walking into at the open and what has changed overnight."
        ),
        "Midday": (
            "intraday as of midday",
            "Use present tense and 'so far today' language. "
            "Open with the macro regime and dominant driver — NOT with index percentage moves. "
            "Flag if moves are accelerating or fading. "
            "For any asset that moved >2%, cite the intraday high or low. "
            "Integrate sector leadership narratively — never as raw ETF tickers and percentages."
        ),
        "Closing": (
            "full session",
            "Write in past tense for closes. "
            "Open with the session arc — what drove the day and how it evolved — NOT with index moves. "
            "Describe whether early moves held, faded, or reversed, and what headline changed the tape. "
            "Give intraday range for the dominant asset. "
            "Integrate sector leadership narratively — never as raw ETF tickers and percentages."
        ),
    }
    timeframe, session_instruction = session_framing.get(session, ("", ""))

    return f"""\
Write the {session} Macro Market Briefing for {date_str}.

{session_instruction}

CRITICAL: Match the voice and analytical depth of the reference examples exactly. \
Write like a Goldman Sachs or Bloomberg Markets Live desk note. \
Produce a causal model of markets — not a summary.

News headlines = narrative driver and source of causality.
Market data = exact numbers. Use intraday ranges where provided.
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

STEP 1 — DATA AUDIT (silent internal reasoning — do NOT output this section):

Complete ALL questions before writing a single word.

Q1. MACRO REGIME: What single macro theme do the top 5 headlines point to?
    Define the regime in 3 words (e.g., "energy inflation shock", "de-escalation relief rally",
    "stagflation repricing"). This becomes the anchor of the entire briefing.

Q2. EQUITIES: Are the major indices (S&P 500, Nasdaq, Dow) up or down by what exact %?
    What factor is driving them — rates? oil? earnings? flows?
    Is this fundamental repricing or positioning-driven?
    Do NOT open with these numbers — use them only to determine character.

Q3. OIL DIRECTION: Calculate (current WTI − prior close) / prior close × 100.
    State direction. Note intraday high/low if provided. Identify: supply/demand or geopolitical cause.
    What is the inflation pass-through? What is the second-order effect on growth and policy?

Q4. RATES DECOMPOSITION:
    2-year yield: up or down? What policy expectation does this reflect?
    10-year yield: up or down? Is this growth fear or inflation fear?
    Curve shape: flattening (inflation), steepening (growth concern), or mixed?
    What is the market pricing for rate cuts/hikes this year?

Q5. CONTRADICTIONS — check every one:
    - Gold falling in a risk-off session? (flag it — explain via real yields + dollar, not "profit-taking")
    - Gold falling in a risk-on session by >1%? (flag it)
    - Crypto rising while equities fall, or vice versa? (flag it with mechanism)
    - Bonds selling off alongside equities? (flag it — inflation shock, not growth fear)
    - Any sector diverging strongly from session theme? (name it narratively)
    Every contradiction flagged here MUST appear explicitly in the briefing.

Q6. EUROPEAN RATES:
    If DE10Y and UK10Y are in the data → use exact levels.
    If not → estimate using ONLY the day's move in bps:
      Bund MOVE = US 10Y move in bps × 0.45, label "(est.)"
      Gilt MOVE = US 10Y move in bps × 0.65, label "(est.)"
    NEVER multiply yield levels. Both MUST appear.

Q7. CROSS-ASSET COHERENCE: Are assets aligned or fragmented?
    Example checks: stocks up + yields up = growth or inflation? Oil up + bonds down = stagflation?
    Name the dominant interpretation and any internal contradiction.

Q8. STRATEGIST FILTER: Is there a named individual AND a specific quantified call?
    YES → include Strategist section with "[Name] at [Firm] [said/warned/argued] [specific level]."
    NO → omit the section entirely.

Q9. CORPORATE MATERIALITY: For each headline, confirm at least one of:
    (a) capital event >$500M, (b) M&A/activist, (c) earnings/guidance moving sector sentiment,
    (d) direct tie to today's macro driver. Omit anything that fails all four tests.

Q10. SECTOR INTEGRATION: Which 1-2 sectors meaningfully led or lagged and WHY?
    Embed this as narrative in the equities section — never as ETF tickers and raw percentages.

Only after completing this audit silently, write the briefing below.

{eq}

STEP 2 — WRITE THE BRIEFING:

{date_str.upper()} | {session.upper()} BRIEFING
{div}

[OPENING — 1-2 sentences. Name the dominant driver and macro regime. State what changed and
what is now being repriced. Do NOT open with index percentage moves.]

[CROSS-ASSET FRAMEWORK — before individual assets, explain which variable is leading and
whether market signals are coherent or fragmented. State the transmission mechanism.]

[CROSS-ASSET NARRATIVE — flowing prose with inline sub-theme labels that describe what happened.
REQUIRED: dominant macro driver with first/second/third-order effects; equities through macro lens
with sector narrative; rates decomposed into 2Y/10Y with explicit policy pricing; FX via rate
differentials; commodities with oil as systemic variable and gold via real yields+dollar; crypto
in two paragraphs. CONTRADICTIONS: every item from Q5 and Q7 must appear explicitly.]

Strategist commentary and desk color
[Only if Q8 confirmed named person + specific quantified call. OMIT ENTIRELY otherwise.]

Policy and geopolitics shaping pricing
[Only if Fed/ECB/BOE/BOJ speakers or major geopolitical policy decisions appeared.
State specific policy path implication. OMIT ENTIRELY if nothing material.]

Corporate News
[Only bullets passing Q9. 3-5 max. One sentence each. Direct market implication as fact.]

What to watch next session
[2-4 bullets. Exact format required:
"[Specific variable] — if [condition A + specific price level], [mechanism] pushes
[specific asset] to [specific level]; if [condition B], [opposite mechanism and outcome]."
BANNED: could / might / may / would / remains to be seen / will be closely watched /
will be important / could impact markets / could signal / could lead to / it could.
Every bullet must contain a specific, checkable price level.]

{div}
Powered by Traderverse | {footer_date}
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
    print(f"[BRIEFING] prompt_chars={prompt_chars}", flush=True)

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
            print(f"[GEMINI] Sending request...", flush=True)
            resp = requests.post(
                f"{GEMINI_API_URL}?key={gemini_api_key}",
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=180,
            )
            print(f"[GEMINI] status={resp.status_code}", flush=True)
            if not resp.ok:
                err = f"Gemini HTTP {resp.status_code}: {resp.text[:600]}"
                print(f"[GEMINI] {err}", flush=True)
                result["error"] = (result.get("error") or "") + f" | {err}"
            else:
                data = resp.json()
            print(f"[GEMINI] response keys={list(data.keys())}", flush=True)
            if "candidates" not in data:
                block_reason = data.get("promptFeedback", {}).get("blockReason", "unknown")
                err = f"Gemini blocked: {block_reason} | full response: {str(data)[:500]}"
                print(f"[GEMINI] BLOCKED: {err}", flush=True)
                result["error"] = (result.get("error") or "") + f" | {err}"
            else:
                candidate = data["candidates"][0]
                finish_reason = candidate.get("finishReason", "")
                print(f"[GEMINI] finishReason={finish_reason}", flush=True)
                if finish_reason == "SAFETY":
                    result["error"] = (result.get("error") or "") + f" | Gemini safety block | candidate={str(candidate)[:300]}"
                    print(f"[GEMINI] safety block: {candidate}", flush=True)
                else:
                    try:
                        result["briefing"] = candidate["content"]["parts"][0]["text"]
                        print(f"[GEMINI] SUCCESS, briefing_len={len(result['briefing'])}", flush=True)
                        return result
                    except (KeyError, IndexError) as ke:
                        err = f"Gemini parse error: {ke} | candidate={str(candidate)[:400]}"
                        print(f"[GEMINI] {err}", flush=True)
                        result["error"] = (result.get("error") or "") + f" | {err}"
        except requests.exceptions.Timeout:
            err = f"Gemini timeout after 180s (prompt was {prompt_chars} chars)"
            print(f"[GEMINI] {err}", flush=True)
            result["error"] = (result.get("error") or "") + f" | {err}"
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else "?"
            body   = e.response.text[:600] if e.response else "no response body"
            err = f"Gemini HTTP {status}: {body}"
            print(f"[GEMINI] {err}", flush=True)
            result["error"] = (result.get("error") or "") + f" | {err}"
        except KeyError as e:
            err = f"Gemini parse error (missing key {e}): {str(data)[:300]}"
            print(f"[GEMINI] {err}", flush=True)
            result["error"] = (result.get("error") or "") + f" | {err}"
        except Exception as e:
            err = f"Gemini error ({type(e).__name__}): {e}"
            print(f"[GEMINI] {err}", flush=True)
            result["error"] = (result.get("error") or "") + f" | {err}"

    # 5. Fallback to Groq if Gemini fails or no key provided
    if groq_api_key:
        GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
        GROQ_MODEL   = "llama-3.3-70b-versatile"
        try:
            print(f"[GROQ] Sending request...", flush=True)
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
            print(f"[GROQ] status={resp.status_code}", flush=True)
            if not resp.ok:
                err = f"Groq HTTP {resp.status_code}: {resp.text[:600]}"
                print(f"[GROQ] {err}", flush=True)
                result["error"] = (result.get("error") or "") + f" | {err}"
            else:
                result["briefing"] = resp.json()["choices"][0]["message"]["content"]
                print(f"[GROQ] SUCCESS, briefing_len={len(result['briefing'])}", flush=True)
            print(f"[GROQ] SUCCESS, briefing_len={len(result['briefing'])}", flush=True)
        except requests.exceptions.Timeout:
            err = f"Groq timeout after 180s"
            print(f"[GROQ] {err}", flush=True)
            result["error"] = (result.get("error") or "") + f" | {err}"
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else "?"
            body   = e.response.text[:600] if e.response else "no response body"
            err = f"Groq HTTP {status}: {body}"
            print(f"[GROQ] {err}", flush=True)
            result["error"] = (result.get("error") or "") + f" | {err}"
        except Exception as e:
            err = f"Groq error ({type(e).__name__}): {e}"
            print(f"[GROQ] {err}", flush=True)
            result["error"] = (result.get("error") or "") + f" | {err}"

    print(f"[BRIEFING] DONE — error={result.get('error')}, briefing={'set' if result.get('briefing') else 'empty'}", flush=True)
    return result
