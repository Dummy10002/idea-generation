# Notion Setup Guide for AI Ideas

This guide shows you how to set up **Notion** as your idea delivery system. **Notion API is completely FREE!**

---

## 📋 What You'll Get

A Notion database that automatically receives:
- Daily AI news ideas (8-10 per day)
- Deep research reports (for top 3 ideas)  
- Approval checkbox
- All metadata (source, score, links)

---

## 🚀 Setup Steps (5 minutes)

### Step 1: Create a Notion Integration

1. Go to: **https://www.notion.so/my-integrations**
2. Click **"+ New Integration"**
3. Fill in:
   - **Name:** `AI Ideas Bot`
   - **Logo:** Optional
   - **Associated workspace:** Your workspace
4. Click **"Submit"**
5. **Copy the "Internal Integration Token"** (starts with `secret_`)

### Step 2: Create Your Ideas Database

1. Open Notion
2. Create a new page called "AI Ideas"
3. Add a **Database - Full page**
4. Add these properties (columns):

| Property Name | Type | Purpose |
|--------------|------|---------|
| Title | Title (default) | News headline |
| Source | Select | Where it came from |
| Category | Select | "🤖 AI" or "🔥 Trending" |
| Link | URL | Original article |
| Score | Number | Relevance score (0-100) |
| Approved | Checkbox | ✅ You approve this |
| Status | Select | "New", "Reviewed", "Used" |
| Date Added | Date | When it was added |

### Step 3: Connect Integration to Database

1. Open your "AI Ideas" database
2. Click the **⋯** (three dots) menu in the top right
3. Go to **"Connections"**
4. Click **"+ Add connection"**
5. Select **"AI Ideas Bot"** (your integration)
6. Click **"Confirm"**

### Step 4: Get Your Database ID

1. Open your database in a browser
2. The URL looks like:
   ```
   https://notion.so/your-workspace/DATABASE_ID?v=...
   ```
3. Copy the **DATABASE_ID** part (32 characters, may have hyphens)

### Step 5: Update Your .env File

```env
NOTION_TOKEN=secret_xxxxxxxxxxxx
NOTION_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxx
DELIVERY_METHOD=notion
```

---

## ✅ Test Your Setup

Run this command to test:

```bash
python scripts/collect_ideas.py
```

Check your Notion database - you should see new ideas appear!

---

## 📱 Daily Workflow

1. **Each morning at 8 AM:** System adds fresh AI ideas to your database
2. **You:** Open Notion (mobile or desktop)
3. **Review:** Check the ideas, mark ones you like as ✅ Approved
4. **Generate Script:** Copy the idea to your Claude Project for script generation

---

## 💡 Tips

- **Filter view:** Create a Notion view that only shows `Status = New`
- **Mobile notifications:** Use Notion mobile app to check ideas on the go
- **Archive old ideas:** Change status to "Reviewed" after you've seen them

---

## 🆓 Cost Breakdown

| Component | Cost |
|-----------|------|
| Notion API | **$0** (free forever) |
| Notion workspace | **$0** (free plan works) |
| Perplexity research | ~$0.02/day |
| GitHub Actions | **$0** (2000 min/month free) |
| **Total** | **~$0.60/month** |
