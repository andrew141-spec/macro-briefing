# 📊 Macro Market Briefing App

Institutional-quality sell-side macro briefings, auto-generated 3× per trading day using Claude AI and live market data.

---

## What It Does

- **Auto-generates** Morning, Midday, and Closing briefings at 6 AM / 12 PM / 4 PM ET
- **Manual override**: generate any session on demand from the sidebar
- **Live market data** via Yahoo Finance (free, no key) + Alpha Vantage fallback
- **Archive**: stores the last 90 briefings, searchable by keyword
- **Downloadable**: each briefing exports as `.txt`
- **Dark Bloomberg-style UI** built for professional use

---

## Project Structure

```
macro_briefing/
├── app.py                          # Main Streamlit app
├── requirements.txt                # Python dependencies
├── .streamlit/
│   ├── config.toml                 # Dark theme + server config
│   └── secrets.toml.template       # API keys template
├── utils/
│   ├── market_data.py              # Yahoo Finance + AV fetcher
│   ├── briefing_generator.py       # Claude AI prompt + generation
│   ├── archive.py                  # JSON-based briefing storage
│   └── scheduler.py                # Session window logic
└── data/
    └── briefings_archive.json      # Auto-created on first run
```

---

## Deployment: Streamlit Cloud (Free)

### 1. Push to GitHub

```bash
git init
git add .
git commit -m "Initial macro briefing app"
git remote add origin https://github.com/YOUR_USERNAME/macro-briefing.git
git push -u origin main
```

### 2. Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click **New app** → connect your GitHub repo
3. Set **Main file path**: `app.py`
4. Click **Advanced settings** → **Secrets** and add:

```toml
GROQ_API_KEY = "gsk_your_key_here"
ALPHA_VANTAGE_KEY = ""   # optional
```

5. Click **Deploy** — live in ~2 minutes

---

## API Keys Required

| Key | Required | Cost | Where to get |
|-----|----------|------|--------------|
| `GROQ_API_KEY` | ✅ Yes | **Free** | [console.groq.com](https://console.groq.com) — no credit card |
| `ALPHA_VANTAGE_KEY` | ❌ Optional | Free | [alphavantage.co](https://www.alphavantage.co/support/#api-key) |

**Everything in this app is free.** Groq's free tier allows 14,400 requests/day — far more than the 3 briefings/day this app needs.

---

## Auto-Schedule Logic

The app checks for auto-generation **once per page load**:

| Session | Window (ET) | Triggers when... |
|---------|-------------|-----------------|
| Morning | 6:00–9:30 AM | Page loaded during window AND not yet generated today |
| Midday  | 12:00–1:30 PM | Same |
| Closing | 4:00–6:00 PM | Same |

> **Note**: Streamlit Cloud does not support true background cron jobs. The auto-generation fires on page load within the session window. For true scheduled delivery, consider pairing with a GitHub Action that pings the app URL at the right times.

---

## Adding Email Delivery (Future)

In `utils/briefing_generator.py`, a `send_email()` function can be wired in after generation. Add to secrets:

```toml
EMAIL_SENDER     = "you@gmail.com"
EMAIL_PASSWORD   = "your-gmail-app-password"
EMAIL_RECIPIENTS = "analyst1@firm.com,analyst2@firm.com"
```

---

## Local Development

```bash
pip install -r requirements.txt

# Create secrets file
mkdir -p .streamlit
cp .streamlit/secrets.toml.template .streamlit/secrets.toml
# Edit .streamlit/secrets.toml with your real keys

streamlit run app.py
```

---

## Briefing Structure

Each generated note covers:

1. **Macro Narrative** — dominant driver, cause-and-effect analysis
2. **Equities** — US futures/indices, Europe, move interpretation  
3. **Rates** — 2Y/10Y yields, curve shape, policy signals
4. **Commodities** — Brent + WTI (emphasized), gold
5. **FX** — DXY, EUR/USD, GBP/USD, USD/JPY
6. **Crypto** — BTC + ETH, liquidity context
7. **Corporate News** — 4–6 major headlines
8. **What Matters Next** — key risks, levels to watch

---

*Powered by Claude AI (Anthropic) · Yahoo Finance · Alpha Vantage*
