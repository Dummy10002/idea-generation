
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

def test_block_formatting():
    notion = NotionDelivery(os.getenv("NOTION_TOKEN"), os.getenv("NOTION_DATABASE_ID"))
    
    # 1. Title
    blocks = [
        {
            "object": "block", "type": "heading_1",
            "heading_1": {"rich_text": [{"type": "text", "text": {"content": "🔥 Top Community Debates (Daily Digest)"}}]}
        },
        # 2. Subtitle
        {
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": "4 trending discussions found across Reddit, X, and HackerNews.", "annotations": {"italic": True}}}]}
        },
        # Divider
        {"object": "block", "type": "divider", "divider": {}},
        
        # --- REDDIT ---
        {
            "object": "block", "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": "🔴 Reddit"}}]}
        },
        # Item 1
        {
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": "OpenClaw vs Moltbot: Rebranding Impact on AI Agent Devs", "annotations": {"bold": True}}}]}
        },
        {
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": "Developers debate if OpenClaw's latest rebrand from Clawdbot/Moltbot affects forking and integrations in local AI agents."}}]}
        },
        {
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [
                {"type": "text", "text": {"content": "🔗 "}},
                {"type": "text", "text": {"content": "View Discussion", "link": {"url": "https://www.reddit.com/r/LocalLLaMA/comments/1jabcde"}}}
            ]}
        },
        # Item 2
        {
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": "What is Best Local Agent: OpenClaw vs Auto-GPT for WhatsApp Bots", "annotations": {"bold": True}}}]}
        },
        {
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": "r/AutoGPT users compare OpenClaw's Telegram/Signal execution to AutoGPT for personal automation."}}]}
        },
        {
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [
                {"type": "text", "text": {"content": "🔗 "}},
                {"type": "text", "text": {"content": "View Discussion", "link": {"url": "https://www.reddit.com/r/AutoGPT/comments/1jabcdef"}}}
            ]}
        },
        
        # Divider
        {"object": "block", "type": "divider", "divider": {}},
        
        # --- HACKERNEWS ---
        {
            "object": "block", "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": "🔵 HackerNews"}}]}
        },
        {
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": "How to Fix Daggr Node Failures in Multi-Step Workflows", "annotations": {"bold": True}}}]}
        },
        {
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": "HN thread on debugging Gradio's new Daggr library: rerunning single nodes without full pipeline restarts."}}]}
        },
        {
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [
                {"type": "text", "text": {"content": "🔗 "}},
                {"type": "text", "text": {"content": "View Discussion", "link": {"url": "https://news.ycombinator.com/item?id=41234567"}}}
            ]}
        },
        
        # Divider
        {"object": "block", "type": "divider", "divider": {}},

        # --- X ---
        {
            "object": "block", "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": "⚫ X"}}]}
        },
        {
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": "Best Tool: Daggr vs LangGraph for AI Automation Graphs", "annotations": {"bold": True}}}]}
        },
        {
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": "Dev praises Daggr's Gradio integration over LangGraph for visual debugging in agent workflows."}}]}
        },
        {
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [
                {"type": "text", "text": {"content": "🔗 "}},
                {"type": "text", "text": {"content": "View Discussion", "link": {"url": "https://x.com/seb_buzdugan/status/1887654321"}}}
            ]}
        }
    ]

    # Create the test item with BLOCKS
    item = NewsItem(
        id=f"test_blocks_{datetime.now().strftime('%H%M%S')}",
        title="🧩 BLOCK FORMAT TEST",
        source="System Check",
        link="https://google.com",
        summary="Content is defined by blocks",
        published=datetime.now(),
        score=10,
        category="daily_questions",
        content_blocks=blocks  # <--- PASSING RAW BLOCKS
    )

    print("📤 Sending STATIC BLOCK test content to Notion...")
    notion.deliver_daily_ideas([item])
    print("✅ Done. Check Notion for 'BLOCK FORMAT TEST' page.")

if __name__ == "__main__":
    test_block_formatting()
