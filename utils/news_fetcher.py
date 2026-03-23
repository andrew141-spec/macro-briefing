"""
News Fetcher — fixed for Streamlit Cloud import path issue.
Sources: RSS (Reuters/CNBC/FT/MarketWatch/Yahoo) + GDELT free API.
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
    {"name": "Reuters Business",  "url": "https://feeds.reuters.com/reuters/businessNews"},
    {"name": "Reuters Markets",   "url": "https://feeds.reuters.com/reuters/companyNews"},
    {"name": "CNBC Top News",     "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html"},
    {"name": "CNBC Economy",      "url": "https://www.cnbc.com/id/20910258/device/rss/rss.html"},
    {"name": "CNBC Finance",      "url": "https://www.cnbc.com/id/10000664/device/rss/rss.html"},
    {"name": "MarketWatch",       "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories"},
    {"name": "Yahoo Finance",     "url": "https://finance.yahoo.com/news/rssindex"},
    {"name": "FT Markets",        "url": "https://www.ft.com/rss/home/uk"},
    {"name": "Investing.com",     "url": "https://www.investing.com/rss/news.rss"},
    {"name": "The Economist",     "url": "https://www.economist.com/finance-and-economics/rss.xml"},
]

GDELT_URL = (
    "https://api.gdeltproject.org/api/v2/doc/doc"
    "?query=economy+OR+oil+OR+federal+reserve+OR+inflation+OR+china+OR+iran"
    "&mode=artlist&maxrecords=25&timespan=6h&format=json&sourcelang=english"
)

MACRO_KEYWORDS = [
    "fed", "federal reserve", "powell", "rate", "interest rate",
    "inflation", "cpi", "pce", "gdp", "jobs", "unemployment", "payroll", "recession",
    "oil", "crude", "brent", "wti", "opec", "energy",
    "china", "iran", "russia", "ukraine", "sanctions", "tariff", "trade",
    "dollar", "yen", "euro", "sterling", "dxy", "currency",
    "treasury", "yield", "bond", "yield curve",
    "bank", "jpmorgan", "goldman", "morgan stanley", "citi",
    "apple", "nvidia", "microsoft", "amazon", "google", "meta", "tesla",
    "earnings", "revenue", "profit", "guidance",
    "merger", "acquisition", "deal", "ipo",
    "ecb", "boe", "boj", "pboc", "central bank",
    "s&p", "nasdaq", "dow", "futures", "market", "rally", "selloff",
    "bitcoin", "crypto", "ethereum", "gold", "commodities",
    "geopolit", "war", "conflict", "military", "strait", "hormuz",
    "debt", "fiscal", "deficit",
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


def _priority(h):
    t = h.get("title", "").lower()
    if any(w in t for w in ["iran", "strait", "hormuz", "opec", "war", "military", "sanction"]):
        return 0
    if any(w in t for w in ["fed", "powell", "rate", "inflation", "cpi", "yield", "treasury"]):
        return 1
    if any(w in t for w in ["oil", "crude", "brent", "wti", "energy"]):
        return 2
    if any(w in t for w in ["china", "russia", "ukraine", "tariff", "trade"]):
        return 3
    if any(w in t for w in ["s&p", "nasdaq", "futures", "market", "rally", "selloff"]):
        return 4
    return 5


def _fetch_rss(max_per_feed=8):
    results, seen = [], set()
    headers = {"User-Agent": "Mozilla/5.0 (compatible; MacroBot/1.0)"}
    for feed in RSS_FEEDS:
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
                seen.add(title)
                results.append({"title": title, "source": feed["name"], "summary": summary, "pub_date": pubdate})
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
            if title and _relevant(title):
                results.append({"title": title, "source": "GDELT", "summary": "", "pub_date": ""})
    except Exception:
        pass
    return results


def fetch_headlines(max_per_feed=8, max_total=40):
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
    lines = ["=== LIVE NEWS HEADLINES (ground your briefing in these real events) ===", ""]
    for i, h in enumerate(headlines, 1):
        lines.append(f"{i:02d}. [{h['source']}] {h['title']}")
        s = h.get("summary", "")
        if s and s != h["title"] and len(s) > 40:
            lines.append(f"    -> {s[:180]}")
    lines += ["", "INSTRUCTION: Use above headlines to identify the dominant macro driver.", "Do NOT fabricate events not present in the headlines above."]
    return "\n".join(lines)
