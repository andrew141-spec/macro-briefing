import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

"""
Market Data Fetcher
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
    "SP500_F": "ES=F",      # S&P 500 futures
    "NQ_F":    "NQ=F",      # Nasdaq futures
    # European
    "DAX":     "^GDAXI",
    "FTSE":    "^FTSE",
    "CAC":     "^FCHI",
    # Rates (proxy ETFs + direct)
    "US10Y":   "^TNX",
    "US2Y":    "^IRX",
    "US30Y":   "^TYX",
    # Commodities
    "BRENT":   "BZ=F",
    "WTI":     "CL=F",
    "GOLD":    "GC=F",
    "NATGAS":  "NG=F",
    # FX
    "DXY":     "DX-Y.NYB",
    "EURUSD":  "EURUSD=X",
    "GBPUSD":  "GBPUSD=X",
    "USDJPY":  "JPY=X",
    "USDCNY":  "CNY=X",
    # Crypto
    "BTC":     "BTC-USD",
    "ETH":     "ETH-USD",
}


def _pct_change(current, prev):
    """Safe percent change calculation."""
    if prev and prev != 0:
        return round(((current - prev) / abs(prev)) * 100, 2)
    return 0.0


def fetch_yahoo_data() -> dict:
    """
    Pull latest market data from Yahoo Finance.
    Returns a clean dict ready for the briefing prompt.
    """
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
                    # Single ticker fallback
                    t = yf.Ticker(ticker)
                    df = t.history(period="2d", interval="1d")
                    df = df.dropna()

                if len(df) >= 2:
                    current = float(df["Close"].iloc[-1])
                    prev    = float(df["Close"].iloc[-2])
                    chg     = _pct_change(current, prev)
                    data[name] = {"price": round(current, 4), "pct_chg": chg}
                elif len(df) == 1:
                    current = float(df["Close"].iloc[-1])
                    data[name] = {"price": round(current, 4), "pct_chg": 0.0}
            except Exception:
                data[name] = {"price": None, "pct_chg": None}

    except Exception as e:
        data["_error"] = str(e)

    # Yield curves (derived)
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


def fetch_alpha_vantage_fallback(api_key: str, symbols: list) -> dict:
    """
    Alpha Vantage fallback for specific symbols when Yahoo fails.
    Only fetches what's requested to stay within rate limits.
    """
    if not api_key:
        return {}

    BASE = "https://www.alphavantage.co/query"
    results = {}

    for sym in symbols[:5]:  # AV free tier: 25 req/day, pace calls
        try:
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": sym,
                "apikey": api_key,
            }
            resp = requests.get(BASE, params=params, timeout=10)
            resp.raise_for_status()
            quote = resp.json().get("Global Quote", {})
            if quote:
                results[sym] = {
                    "price":   round(float(quote.get("05. price", 0)), 4),
                    "pct_chg": round(float(quote.get("10. change percent", "0%").replace("%", "")), 2),
                }
            time.sleep(12)  # Respect AV rate limit (5 req/min free)
        except Exception:
            pass

    return results


def get_market_snapshot(alpha_vantage_key: str = "") -> dict:
    """
    Master function: try Yahoo Finance first, patch missing values
    with Alpha Vantage if a key is provided.
    """
    snapshot = fetch_yahoo_data()

    # Identify failed tickers
    failed = [k for k, v in snapshot.items()
              if not k.startswith("_") and isinstance(v, dict) and v.get("price") is None]

    if failed and alpha_vantage_key:
        # Map our label → AV symbol
        label_to_av = {
            "SP500":  "SPY",
            "NASDAQ": "QQQ",
            "DOW":    "DIA",
            "BTC":    "BTC/USD",  # AV crypto endpoint differs
            "ETH":    "ETH/USD",
            "WTI":    "WTI",
            "GOLD":   "XAUUSD",
        }
        av_symbols = [label_to_av[k] for k in failed if k in label_to_av]
        if av_symbols:
            av_data = fetch_alpha_vantage_fallback(alpha_vantage_key, av_symbols)
            # Patch back
            for label in failed:
                av_sym = label_to_av.get(label)
                if av_sym and av_sym in av_data:
                    snapshot[label] = av_data[av_sym]
                    snapshot["_source"] = "Yahoo Finance + Alpha Vantage"

    return snapshot


def format_snapshot_for_prompt(snapshot: dict) -> str:
    """
    Convert the raw snapshot dict into a structured string
    that feeds cleanly into the Claude prompt.
    """
    def fmt(label):
        d = snapshot.get(label, {})
        if not d or d.get("price") is None:
            return f"{label}: N/A"
        p   = d["price"]
        chg = d.get("pct_chg", 0) or 0
        sign = "+" if chg >= 0 else ""
        return f"{label}: {p:,.4g} ({sign}{chg:.2f}%)"

    ts  = snapshot.get("_timestamp", "")
    src = snapshot.get("_source", "Yahoo Finance")
    yc  = snapshot.get("YIELD_CURVE_2_10")
    yc_str = f"\n2s10s Yield Curve Spread: {yc:+.3f}%" if yc else ""

    lines = [
        f"=== LIVE MARKET DATA | {ts} | Source: {src} ===",
        "",
        "[ EQUITIES ]",
        fmt("SP500"), fmt("NASDAQ"), fmt("DOW"),
        fmt("SP500_F") + " (futures)", fmt("NQ_F") + " (futures)",
        fmt("VIX") + " (volatility)",
        fmt("DAX"), fmt("FTSE"), fmt("CAC"),
        "",
        "[ RATES ]",
        fmt("US10Y") + " (10Y yield)", fmt("US2Y") + " (2Y yield)", fmt("US30Y") + " (30Y yield)",
        yc_str,
        "",
        "[ COMMODITIES ]",
        fmt("BRENT") + " (Brent crude)", fmt("WTI") + " (WTI crude)",
        fmt("GOLD"), fmt("NATGAS"),
        "",
        "[ FX ]",
        fmt("DXY") + " (Dollar Index)",
        fmt("EURUSD"), fmt("GBPUSD"), fmt("USDJPY"),
        "",
        "[ CRYPTO ]",
        fmt("BTC"), fmt("ETH"),
    ]

    return "\n".join(filter(None, lines))
