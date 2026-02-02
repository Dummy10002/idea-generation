# AI Daily Briefing System

A streamlined, budget-conscious automation system that delivers **Elite AI Intelligence** to your Notion database twice daily.

**Budget:** Capped strictly at $5.00/month.
**Schedule:** Morning (8:00 AM IST) & Evening (6:00 PM IST).

---

## 🚀 Features

- **2x Daily Updates:** Morning and evening briefings to keep you ahead.
- **Smart Discovery:** Uses strict 24-hour search filters for freshness.
- **"No Clutter" Policy:** Only delivers high-signal, summarized insights.
- **4 Key Categories:**
  1. 🤖 **Agentic News**: New frameworks, autonomous agents.
  2. 🛠️ **Building Tips**: Practical tutorials, code patterns.
  3. 💡 **Innovation**: Breakthrough research, new models.
  4. 🔥 **Trends**: Viral discussions and debates.

---

## 📋 Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   Edit `.env`:
   ```env
   # Notion (Required)
   NOTION_TOKEN=secret_...
   NOTION_DATABASE_ID=...

   # Research (Required)
   PERPLEXITY_API_KEY=pplx-...

   # Budget (Optional)
   MONTHLY_BUDGET=5.0
   ```

3. **Verify Budget**
   Check `data/budget_tracking.json` to see current spending.

---

## 🏃‍♂️ How to Run

**Manual Run:**
```bash
python scripts/daily_briefing.py
```

**Automated:**
GitHub Actions workflow `daily_ideas.yml` runs automatically at:
- 8:00 AM IST
- 6:00 PM IST

---

## 📁 Project Structure

```
idea-generation/
├── .github/workflows/
│   └── daily_ideas.yml      # 2x Daily Schedule
├── scripts/
│   ├── daily_briefing.py    # MAIN script (The only one you need)
│   └── setup_daily.py       # First-time setup helper
├── src/
│   ├── generator/           # Perplexity discovery logic
│   ├── interfaces/          # Notion delivery
│   └── utils/               # Budget & config
└── data/
    └── budget_tracking.json # Automatic cost tracking
```

---

## 💰 Cost Management

The system includes a **Safety Switch**:
- Each run costs approx **$0.01 - $0.03**.
- If monthly spend hits **$5.00**, the script automatically stops running.
- Resets automatically on the 1st of the month.
