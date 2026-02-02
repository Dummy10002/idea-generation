
import sys
import os
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.interfaces.notion_delivery import NotionDelivery
from src.collectors.rss_collector import NewsItem

def test_static_formatting():
    notion = NotionDelivery(os.getenv("NOTION_TOKEN"), os.getenv("NOTION_DATABASE_ID"))
    
    # YOUR EXACT CONTENT, CAREFULLY FORMATTED WITH NEWLINES
    summary_content = """# 🔥 Top Community Debates (Daily Digest)

*4 trending discussions found across Reddit, X, and HackerNews.*

---

## 🔴 Reddit

**OpenClaw vs Moltbot: Rebranding Impact on AI Agent Devs**
Developers debate if OpenClaw's latest rebrand from Clawdbot/Moltbot affects forking and integrations in local AI agents.
🔗 [View Discussion](https://www.reddit.com/r/LocalLLaMA/comments/1jabcde/openclaw_rebrand_from_clawdbot_moltbot_what_next/)

**What is Best Local Agent: OpenClaw vs Auto-GPT for WhatsApp Bots**
r/AutoGPT users compare OpenClaw's Telegram/Signal execution to AutoGPT for personal automation.
🔗 [View Discussion](https://www.reddit.com/r/AutoGPT/comments/1jabcdef/openclaw_vs_autogpt_for_local_messaging_agents/)

---

## 🔵 HackerNews

**How to Fix Daggr Node Failures in Multi-Step Workflows**
HN thread on debugging Gradio's new Daggr library: rerunning single nodes without full pipeline restarts.
🔗 [View Discussion](https://news.ycombinator.com/item?id=41234567)

---

## ⚫ X

**Best Tool: Daggr vs LangGraph for AI Automation Graphs**
Dev praises Daggr's Gradio integration over LangGraph for visual debugging in agent workflows.
🔗 [View Discussion](https://x.com/seb_buzdugan/status/1887654321)

---
"""

    # Create the test item
    item = NewsItem(
        id=f"test_format_{datetime.now().strftime('%H%M%S')}",
        title="🎨 FORMAT TEST: Static Content Validation",
        source="Formatting Check",
        link="https://google.com",
        summary=summary_content,
        published=datetime.now(),
        score=10,
        category="daily_questions"
    )

    print("📤 Sending STATIC test content to Notion...")
    notion.deliver_daily_ideas([item])
    print("✅ Done. Check Notion for 'FORMAT TEST' page.")

if __name__ == "__main__":
    test_static_formatting()
