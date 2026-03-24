"""
News Fetcher — upgraded for institutional-quality corporate news.
Sources: RSS (Reuters/FT/Bloomberg/WSJ/CNBC) + GDELT free API.
All free, no API keys required.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import xml.etree.ElementTree as ET_XML
from datetime import datetime, timezone, timedelta
import re

RSS_FEEDS = [
    # Tier 1 — highest signal for macro/markets
    {"name": "Reuters Business",       "url": "https://feeds.reuters.com/reuters/businessNews",         "tier": 1},
    {"name": "Reuters Markets",        "url": "https://feeds.reuters.com/reuters/companyNews",           "tier": 1},
    {"name": "FT Markets",             "url": "https://www.ft.com/rss/home/uk",                          "tier": 1},
    {"name": "WSJ Markets",            "url": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",           "tier": 1},
    {"name": "WSJ Economy",            "url": "https://feeds.a.dj.com/rss/RSSWorldNews.xml",             "tier": 1},
    # Tier 2 — good breadth
    {"name": "CNBC Top News",          "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html",   "tier": 2},
    {"name": "CNBC Economy",           "url": "https://www.cnbc.com/id/20910258/device/rss/rss.html",    "tier": 2},
    {"name": "CNBC Finance",           "url": "https://www.cnbc.com/id/10000664/device/rss/rss.html",    "tier": 2},
    {"name": "MarketWatch Top",        "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories","tier": 2},
    {"name": "Yahoo Finance",          "url": "https://finance.yahoo.com/news/rssindex",                 "tier": 2},
    # Tier 3 — supplementary
    {"name": "The Economist Finance",  "url": "https://www.economist.com/finance-and-economics/rss.xml", "tier": 3},
    {"name": "Investing.com",          "url": "https://www.investing.com/rss/news.rss",                  "tier": 3},
]

GDELT_URL = (
    "https://api.gdeltproject.org/api/v2/doc/doc"
    "?query=economy+OR+oil+OR+federal+reserve+OR+inflation+OR+china+OR+iran"
    "&mode=artlist&maxrecords=25&timespan=6h&format=json&sourcelang=english"
)

MACRO_KEYWORDS = [
    "fed", "federal reserve", "powell", "rate", "interest rate",
    "inflation", "cpi", "pce", "gdp", "jobs", "unemployment", "payroll", "recession",
    "oil", "crude", "brent", "wti", "opec", "energy", "pipeline", "refinery",
    "china", "iran", "russia", "ukraine", "sanctions", "tariff", "trade", "hormuz", "strait",
    "dollar", "yen", "euro", "sterling", "dxy", "currency", "forex",
    "treasury", "yield", "bond", "yield curve", "spread",
    "bank", "jpmorgan", "goldman", "morgan stanley", "citi", "wells fargo", "bank of america",
    "earnings", "revenue", "profit", "guidance", "outlook", "forecast",
    "merger", "acquisition", "buyout", "lbo", "deal", "ipo", "spin-off", "stake",
    "buyback", "dividend", "capital", "raise", "offering", "bond sale",
    "activist", "elliott", "starboard", "icahn", "trian", "third point",
    "ecb", "boe", "boj", "pboc", "central bank", "lagarde", "bailey", "ueda",
    "s&p", "nasdaq", "dow", "futures", "market", "rally", "selloff", "correction",
    "bitcoin", "crypto", "ethereum", "gold", "silver", "copper", "commodities",
    "geopolit", "war", "conflict", "military", "nuclear", "strike",
    "debt", "fiscal", "deficit", "spending", "budget",
    "invest", "billion", "million", "fund", "portfolio",
]

# Stories that sound financial but carry no market signal — exclude them
NOISE_PATTERNS = [
    r"foldable (iphone|phone|device)",
    r"chuck norris",
    r"meme",
    r"celebrity",
    r"best days.*(halve|returns)",   # generic market timing advice
    r"market timing",
    r"sprouts farmers",
    r"stay invested",
    r"don.t panic",
    r"personal finance tips",
    r"how to invest",
    r"warren buffett says (invest|buy|hold)",  # generic advice without capital event
]

# Patterns that strongly signal material corporate news
MATERIAL_CORPORATE_PATTERNS = [
    r"\$[\d,]+\s*(billion|million|bn|mn)\b",   # dollar amount mentioned
    r"\b(acquire|acqui|merger|takeover|buyout|lbo|ipo|spin.?off)\b",
    r"\b(activist|elliott|starboard|icahn|trian|third point|pershing)\b",
    r"\b(earnings|quarterly results|guidance|raised? (outlook|forecast|guidance))\b",
    r"\b(invest(ing|ment|or))\s+(up to|as much as|\$[\d])",
    r"\b(capital raise|share buyback|dividend|bond sale|debt issuance)\b",
    r"\b(plant|factory|facility).{0,30}(shut|clos|open|expan)",
    r"\b(layoff|cut(ting)? jobs|restructur|headcount)\b",
    r"\bCEO.{0,30}(resign|step|replac|appoint)\b",
]


def _clean(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-z]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()[:300]


def _recent(pub_date_str, hours=18):
    if not pub_date_str:
        return True
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(pub_date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt >= datetime.now(timezone.utc) - timedelta(hours=hours)
    except Exception:
        return True


def _relevant(title, summary=""):
    combined = (title + " " + summary).lower()
    return any(kw in combined for kw in MACRO_KEYWORDS)


def _is_noise(title, summary=""):
    """Return True if the story matches known low-signal patterns."""
    combined = (title + " " + summary).lower()
    return any(re.search(p, combined) for p in NOISE_PATTERNS)


def _is_material_corporate(title, summary=""):
    """Return True if the story likely clears the materiality bar."""
    combined = (title + " " + summary).lower()
    return any(re.search(p, combined) for p in MATERIAL_CORPORATE_PATTERNS)


def _priority(h):
    t = (h.get("title", "") + " " + h.get("summary", "")).lower()
    # Geopolitical / energy supply risk — highest priority
    if any(w in t for w in ["iran", "strait", "hormuz", "opec", "war", "military", "sanction", "strike"]):
        return 0
    # Fed / rates / inflation
    if any(w in t for w in ["fed", "powell", "rate hike", "rate cut", "inflation", "cpi", "yield", "treasury", "fomc"]):
        return 1
    # Energy prices
    if any(w in t for w in ["oil", "crude", "brent", "wti", "energy", "pipeline", "refinery"]):
        return 2
    # Material corporate (M&A, earnings, capital events)
    if _is_material_corporate(t):
        return 3
    # Macro geopolitics (China, Russia, trade)
    if any(w in t for w in ["china", "russia", "ukraine", "tariff", "trade war", "export control"]):
        return 4
    # Broad market
    if any(w in t for w in ["s&p", "nasdaq", "futures", "market", "rally", "selloff"]):
        return 5
    return 6


def _fetch_rss(max_per_feed=10):
    results, seen = [], set()
    headers = {"User-Agent": "Mozilla/5.0 (compatible; MacroBot/1.0)"}

    # Sort feeds by tier so tier-1 sources fill the list first
    sorted_feeds = sorted(RSS_FEEDS, key=lambda f: f.get("tier", 9))

    for feed in sorted_feeds:
        try:
            resp = requests.get(feed["url"], headers=headers, timeout=8)
            if resp.status_code != 200:
                continue
            root = ET_XML.fromstring(resp.content)
            count = 0
            for item in root.findall(".//item"):
                if count >= max_per_feed:
                    break
                title   = _clean(item.findtext("title", ""))
                summary = _clean(item.findtext("description", ""))
                pubdate = item.findtext("pubDate", "")
                if not title or title in seen:
                    continue
                if not _recent(pubdate):
                    continue
                if not _relevant(title, summary):
                    continue
                if _is_noise(title, summary):
                    continue
                seen.add(title)
                results.append({
                    "title":    title,
                    "source":   feed["name"],
                    "summary":  summary,
                    "pub_date": pubdate,
                    "material": _is_material_corporate(title, summary),
                })
                count += 1
        except Exception:
            continue
    return results


def _fetch_gdelt():
    results = []
    try:
        resp = requests.get(GDELT_URL, timeout=10)
        if resp.status_code != 200:
            return []
        for art in resp.json().get("articles", [])[:20]:
            title = _clean(art.get("title", ""))
            if title and _relevant(title) and not _is_noise(title):
                results.append({
                    "title":    title,
                    "source":   "GDELT",
                    "summary":  "",
                    "pub_date": "",
                    "material": _is_material_corporate(title),
                })
    except Exception:
        pass
    return results


def fetch_headlines(max_per_feed=10, max_total=40):
    all_h, seen = [], set()
    for h in _fetch_rss(max_per_feed) + _fetch_gdelt():
        if h["title"] not in seen:
            seen.add(h["title"])
            all_h.append(h)
    all_h.sort(key=_priority)
    return all_h[:max_total]


def format_headlines_for_prompt(headlines):
    if not headlines:
        return "No live headlines available — rely on market data context."

    macro   = [h for h in headlines if not h.get("material")]
    corp    = [h for h in headlines if h.get("material")]

    lines = ["=== LIVE MACRO & GEOPOLITICAL HEADLINES ===", ""]
    for i, h in enumerate(macro, 1):
        lines.append(f"{i:02d}. [{h['source']}] {h['title']}")
        s = h.get("summary", "")
        if s and s != h["title"] and len(s) > 40:
            lines.append(f"    -> {s[:200]}")

    if corp:
        lines += ["", "=== MATERIAL CORPORATE NEWS (capital allocation / earnings / M&A) ===", ""]
        for i, h in enumerate(corp, 1):
            lines.append(f"{i:02d}. [{h['source']}] {h['title']}")
            s = h.get("summary", "")
            if s and s != h["title"] and len(s) > 40:
                lines.append(f"    -> {s[:200]}")

    lines += [
        "",
        "INSTRUCTION: Use macro headlines for the narrative driver and causal chain.",
        "Use material corporate headlines for Section 7 / Corporate News only.",
        "Do NOT use any corporate story that lacks a capital allocation decision, "
        "M&A event, earnings result, or activist involvement.",
        "Do NOT fabricate events not present above.",
    ]
    return "\n".join(lines)
