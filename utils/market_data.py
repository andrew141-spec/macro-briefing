import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

"""
Market Data Fetcher — upgraded with intraday ranges, prior-close context,
sector ETFs, silver/copper, and European rate proxies.
Primary: yfinance (Yahoo Finance) — no API key required
Fallback: Alpha Vantage — requires free API key
"""

import yfinance as yf
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
import time


# ─── TICKER MAP ───────────────────────────────────────────────────────────────
TICKERS = {
    # Equities
    "SP500":   "^GSPC",
    "NASDAQ":  "^IXIC",
    "DOW":     "^DJI",
    "Russell": "IWM",
    "VIX":     "^VIX",
    "SP500_F": "ES=F",
    "NQ_F":    "NQ=F",
    # Sector ETFs
    "XLE":     "XLE",
    "XLF":     "XLF",
    "XLK":     "XLK",
    "XLY":     "XLY",
    "XLP":     "XLP",
    # European
    "DAX":     "^GDAXI",
    "FTSE":    "^FTSE",
    "CAC":     "^FCHI",
    "STOXX":   "^STOXX50E",
    # US Rates
    "US10Y":   "^TNX",
    "US2Y":    "^IRX",
    "US30Y":   "^TYX",
    # European rates (these often fail on Yahoo — handled gracefully)
    "DE10Y":   "^DE10Y-EUR",
    "UK10Y":   "^TMBMKGB-10Y",
    # Commodities
    "BRENT":   "BZ=F",
    "WTI":     "CL=F",
    "GOLD":    "GC=F",
    "SILVER":  "SI=F",
    "COPPER":  "HG=F",
    "NATGAS":  "NG=F",
    # FX
    "DXY":     "DX-Y.NYB",
    "EURUSD":  "EURUSD=X",
    "GBPUSD":  "GBPUSD=X",
    "USDJPY":  "JPY=X",
    # Crypto
    "BTC":     "BTC-USD",
    "ETH":     "ETH-USD",
}

# Assets to enrich with intraday 5-min high/low
INTRADAY_TICKERS = {
    "WTI":    "CL=F",
    "BRENT":  "BZ=F",
    "GOLD":   "GC=F",
    "SILVER": "SI=F",
    "COPPER": "HG=F",
    "BTC":    "BTC-USD",
    "ETH":    "ETH-USD",
    "SP500":  "^GSPC",
    "NASDAQ": "^IXIC",
}


def _pct_change(current, prev):
    if prev and prev != 0:
        return round(((current - prev) / abs(prev)) * 100, 2)
    return 0.0


def fetch_intraday_range(ticker: str) -> dict | None:
    """Fetch today's intraday high/low/open via 5-min bars."""
    try:
        df = yf.download(ticker, period="1d", interval="5m",
                         auto_adjust=True, progress=False)
        if df.empty:
            return None
        return {
            "high":  round(float(df["High"].max()), 2),
            "low":   round(float(df["Low"].min()), 2),
            "open":  round(float(df["Open"].iloc[0]), 2),
        }
    except Exception:
        return None


def fetch_yahoo_data() -> dict:
    """Pull latest market data from Yahoo Finance."""
    data = {}
    tickers_str = " ".join(TICKERS.values())

    try:
        raw = yf.download(
            tickers_str,
            period="2d",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=True,
        )

        for name, ticker in TICKERS.items():
            try:
                if ticker in raw.columns.get_level_values(0):
                    df = raw[ticker].dropna()
                else:
                    t = yf.Ticker(ticker)
                    df = t.history(period="2d", interval="1d").dropna()

                if len(df) >= 2:
                    current = float(df["Close"].iloc[-1])
                    prev    = float(df["Close"].iloc[-2])
                    chg     = _pct_change(current, prev)
                    data[name] = {
                        "price":      round(current, 4),
                        "pct_chg":    chg,
                        "prev_close": round(prev, 4),
                    }
                elif len(df) == 1:
                    current = float(df["Close"].iloc[-1])
                    data[name] = {"price": round(current, 4), "pct_chg": 0.0, "prev_close": None}
            except Exception:
                data[name] = {"price": None, "pct_chg": None, "prev_close": None}

    except Exception as e:
        data["_error"] = str(e)

    # Derived: yield curve
    try:
        us10 = data.get("US10Y", {}).get("price")
        us2  = data.get("US2Y",  {}).get("price")
        if us10 and us2:
            data["YIELD_CURVE_2_10"] = round(us10 - us2, 3)
    except Exception:
        pass

    data["_source"]    = "Yahoo Finance"
    data["_timestamp"] = datetime.now(pytz.utc).isoformat()
    return data


def enrich_with_intraday(snapshot: dict) -> dict:
    """Add intraday high/low to key volatile tickers."""
    for label, ticker in INTRADAY_TICKERS.items():
        entry = snapshot.get(label, {})
        if not entry or entry.get("price") is None:
            continue
        pct = abs(entry.get("pct_chg") or 0)
        # Always fetch for energy and crypto; others only if moved >1.5%
        if pct >= 1.5 or label in ("WTI", "BRENT", "GOLD", "BTC", "ETH"):
            rng = fetch_intraday_range(ticker)
            if rng:
                snapshot[label]["intraday_high"] = rng["high"]
                snapshot[label]["intraday_low"]  = rng["low"]
                snapshot[label]["intraday_open"] = rng["open"]
    return snapshot


def fetch_alpha_vantage_fallback(api_key: str, symbols: list) -> dict:
    if not api_key:
        return {}
    BASE = "https://www.alphavantage.co/query"
    results = {}
    for sym in symbols[:5]:
        try:
            params = {"function": "GLOBAL_QUOTE", "symbol": sym, "apikey": api_key}
            resp = requests.get(BASE, params=params, timeout=10)
            resp.raise_for_status()
            quote = resp.json().get("Global Quote", {})
            if quote:
                results[sym] = {
                    "price":      round(float(quote.get("05. price", 0)), 4),
                    "pct_chg":    round(float(quote.get("10. change percent", "0%").replace("%", "")), 2),
                    "prev_close": None,
                }
            time.sleep(12)
        except Exception:
            pass
    return results


def get_market_snapshot(alpha_vantage_key: str = "") -> dict:
    """Master: Yahoo first, patch with Alpha Vantage, enrich with intraday."""
    snapshot = fetch_yahoo_data()

    failed = [k for k, v in snapshot.items()
              if not k.startswith("_") and isinstance(v, dict) and v.get("price") is None]

    if failed and alpha_vantage_key:
        label_to_av = {
            "SP500": "SPY", "NASDAQ": "QQQ", "DOW": "DIA",
            "BTC": "BTC/USD", "ETH": "ETH/USD", "WTI": "WTI", "GOLD": "XAUUSD",
        }
        av_symbols = [label_to_av[k] for k in failed if k in label_to_av]
        if av_symbols:
            av_data = fetch_alpha_vantage_fallback(alpha_vantage_key, av_symbols)
            for label in failed:
                av_sym = label_to_av.get(label)
                if av_sym and av_sym in av_data:
                    snapshot[label] = av_data[av_sym]
                    snapshot["_source"] = "Yahoo Finance + Alpha Vantage"

    snapshot = enrich_with_intraday(snapshot)
    return snapshot


def _fmt_price(p: float) -> str:
    if p >= 10000:
        return f"{p:,.0f}"
    elif p >= 100:
        return f"{p:,.2f}"
    elif p >= 1:
        return f"{p:,.4f}"
    return f"{p:.6f}"


def format_snapshot_for_prompt(snapshot: dict) -> str:
    """
    Build the market data block injected into the briefing prompt.
    Includes intraday range for assets that moved significantly, and prior close
    for morning-session context.
    """
    def fmt(label, show_range=True, show_prev=True):
        d = snapshot.get(label, {})
        if not d or d.get("price") is None:
            return f"{label}: N/A"
        p    = d["price"]
        chg  = d.get("pct_chg", 0) or 0
        sign = "+" if chg >= 0 else ""
        base = f"{label}: {_fmt_price(p)} ({sign}{chg:.2f}%)"

        if show_range:
            hi = d.get("intraday_high")
            lo = d.get("intraday_low")
            if hi and lo:
                base += f"  [intraday range: {_fmt_price(lo)} – {_fmt_price(hi)}]"

        if show_prev:
            prev = d.get("prev_close")
            if prev:
                base += f"  (prev close: {_fmt_price(prev)})"

        return base

    ts  = snapshot.get("_timestamp", "")
    src = snapshot.get("_source", "Yahoo Finance")
    yc  = snapshot.get("YIELD_CURVE_2_10")
    yc_str = f"2s10s Spread: {yc:+.3f}%" if yc else ""

    lines = [
        f"=== LIVE MARKET DATA | {ts} | Source: {src} ===",
        "",
        "[ EQUITIES — cash & futures ]",
        fmt("SP500"), fmt("NASDAQ"), fmt("DOW"),
        fmt("SP500_F") + " (S&P 500 futures)",
        fmt("NQ_F")    + " (Nasdaq futures)",
        fmt("VIX")     + " (volatility index — use for risk sentiment)",
        fmt("DAX"), fmt("FTSE"), fmt("CAC"), fmt("STOXX"),
        "",
        "[ SECTOR ROTATION — use to identify leadership/laggards ]",
        fmt("XLE") + " (Energy sector ETF)",
        fmt("XLF") + " (Financials sector ETF)",
        fmt("XLK") + " (Technology sector ETF)",
        fmt("XLY") + " (Consumer Discretionary ETF)",
        fmt("XLP") + " (Consumer Staples ETF)",
        "",
        "[ RATES — ALWAYS include DE10Y and UK10Y in rates section ]",
        fmt("US10Y", show_range=False) + " (US 10Y Treasury yield)",
        fmt("US2Y",  show_range=False) + " (US 2Y Treasury yield)",
        fmt("US30Y", show_range=False) + " (US 30Y Treasury yield)",
        fmt("DE10Y", show_range=False) + " (Germany 10Y Bund — REQUIRED in rates section)",
        fmt("UK10Y", show_range=False) + " (UK 10Y Gilt — REQUIRED in rates section)",
        yc_str,
        "",
        "[ COMMODITIES — include intraday range if move >2% ]",
        fmt("BRENT")  + " (Brent crude oil)",
        fmt("WTI")    + " (WTI crude oil)",
        fmt("GOLD"),
        fmt("SILVER") + " (silver — flag if diverging from gold)",
        fmt("COPPER") + " (copper — growth/demand proxy)",
        fmt("NATGAS"),
        "",
        "[ FX ]",
        fmt("DXY")    + " (Dollar Index)",
        fmt("EURUSD") + " (EUR/USD)",
        fmt("GBPUSD") + " (GBP/USD — sterling)",
        fmt("USDJPY") + " (USD/JPY — yen)",
        "",
        "[ CRYPTO — note if diverging from equities ]",
        fmt("BTC") + " (Bitcoin)",
        fmt("ETH") + " (Ether)",
    ]

    return "\n".join(filter(None, lines))
