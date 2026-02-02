#!/usr/bin/env python3
"""
Daily AI Briefing - ELITE RESEARCH VERSION
==========================================
Delivers high-signal AI trends using the "AI Trends Researcher" persona.
Strict logic for freshness, novelty, and deduplication.

Schedule: 2x Daily (Morning/Evening)
Budget: <$5/mo
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.utils.logger import logger
from src.utils.budget_manager import BudgetManager
from src.utils.history_manager import HistoryManager
from src.generator.perplexity_discovery import PerplexityDiscovery
from src.interfaces.notion_delivery import NotionDelivery
from src.collectors.rss_collector import NewsItem

# --- THE RESEARCHER PROMPT TEMPLATE ---
RESEARCHER_PROMPT = """You are an AI trends researcher. Date: {CURRENT_DATE}. {TIME_OF_DAY} briefing.

MANDATE: Discover 3-5 high-signal, "underground" updates from the LAST 24 HOURS.
PRIORITY SOURCES: Reddit (r/LocalLLaMA, r/AutoGPT), HackerNews, X (Twitter) Dev Community, GitHub Trending.

FOCUS AREAS (Must match these exactly):
{FOCUS_AREAS}

CRITICAL RULES:
1. **NOVELTY**: No mainstream news (like "Google did X"). Find the TOOLS and TECHNIQUES developers are talking about.
2. **FRESHNESS**: Must be posted < 24 hours ago. Include the approx time (e.g., "4 hours ago").
3. **EXCLUSION**: Ignore these: {PREVIOUS_IDEAS}

OUTPUT FORMAT (JSON ONLY):
[
  {{
    "category": "Category Name",
    "title": "Short, punchy title (No clickbait)",
    "source_name": "Source (e.g., 'Reddit', 'X')",
    "source_url": "Direct Link",
    "posted_time": "e.g., '6 hours ago'",
    "description": "What is it?",
    "why_it_matters": "Why is this important?",
    "how_to_build": "Technical implementation tip",
    "virality_score": 9 
  }}
]
"""

class DailyBriefing:
    def __init__(self):
        self.budget = BudgetManager()
        self.history = HistoryManager()
        self.perplexity = PerplexityDiscovery()
        self.notion = NotionDelivery(os.getenv("NOTION_TOKEN"), os.getenv("NOTION_DATABASE_ID"))
        
    def _run_research_pass(self, focus_areas: str, session_name: str) -> List[Dict]:
        """Run a specific research pass."""
        print(f"\n🔍 Researching: {session_name}...")
        
        # Prepare params
        time_of_day = "Morning" if datetime.now().hour < 12 else "Evening"
        previous_ideas = self.history.get_recent_titles()
        
        prompt = RESEARCHER_PROMPT.format(
            CURRENT_DATE=datetime.now().strftime('%Y-%m-%d'),
            TIME_OF_DAY=time_of_day,
            FOCUS_AREAS=focus_areas,
            PREVIOUS_IDEAS=previous_ideas
        )
        
        try:
            result = self.perplexity._query_perplexity(prompt, max_tokens=2000)
            if not result:
                print("   ⚠️ No response from Perplexity")
                return []
                
            items = self.perplexity._parse_json_response(result['content'])
            print(f"   ✅ Found {len(items)} ideas in {session_name} (${result['cost']:.4f})")
            
            # Record cost
            self.budget.record_spending(result['cost'])
            return items
            
        except Exception as e:
            print(f"   ❌ Error in research pass: {e}")
            return []

    def run(self):
        print("\n" + "="*50)
        print(f"🚀 AI INTELLIGENCE BRIEFING: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(self.budget.get_status())
        print("="*50)
        
        # 1. Budget Check
        if not self.budget.check_budget():
            print("❌ Budget Limit Reached. Stopping.")
            return

        all_raw_items = []
        
        # 2. Execute Focused Research Passes
        
        # Pass 1: How folks are building (Dev & Automation)
        pass1_focus = """
        1. AI Development: New open-source models (HuggingFace), fine-tuning tricks, new Python libraries.
        2. Automation Building: New integration patterns, agentic workflows (n8n/LangChain), no-code hacks.
        """
        all_raw_items.extend(self._run_research_pass(pass1_focus, "One: Dev & Automation"))
        
        # Pass 2: What is Hot/Trending (Agents & Trends)
        pass2_focus = """
        3. Agentic Trends: New autonomous frameworks (CrewAI, AutoGen updates), agent benchmarks.
        4. Viral Topics: What is the top debate on X/Reddit/HackerNews RIGHT NOW?
        """
        all_raw_items.extend(self._run_research_pass(pass2_focus, "Two: Agents & Trends"))

        # Pass 3: Community Questions (What are people ASKING?)
        pass3_focus = """
        5. Top Questions: What are the TOP 10 burning questions on Reddit, Quora, and X today?
        SCOPE: AI Agents, Automation, Tech Entrepreneurship, and Viral Debates.
        Focus on: "X vs Y" comparisons, "How to fix" debugging, and "What is the best tool for..."
        """
        all_raw_items.extend(self._run_research_pass(pass3_focus, "Three: Community Questions"))
        
        if not all_raw_items:
            print("\n📭 NO NEW IDEAS (All findings were too old or duplicates).")
            return

        # 3. Transform & Deduplicate
        notion_items = []
        questions_buffer = []
        
        for item in all_raw_items:
            # Separate Questions from regular news
            if "Question" in item.get('category', ''):
                questions_buffer.append(item)
                continue
                
            # Process regular news items
            summary_text = (
                f"**🕒 Freshness:** {item.get('posted_time', 'Recently')}\n"
                f"**💡 Why it matters:** {item.get('why_it_matters', '')}\n\n"
                f"**🛠️ How to Build/Use:** {item.get('how_to_build', 'See source')}\n\n"
                f"**Description:** {item.get('description', '')}"
            )
            
            news_item = NewsItem(
                id=f"idea_{int(time.time())}_{hash(item.get('title'))}",
                title=f"{self._get_emoji(item.get('category', ''))} {item.get('title')}",
                source=item.get('source_name', 'Research'),
                link=item.get('source_url', None),
                summary=summary_text,
                published=datetime.now(),
                score=min(int(item.get('virality_score', 8)), 10),
                category="ai_research"
            )
            notion_items.append(news_item)

        # 4. Create the Consolidated "Daily Questions" Page
        if questions_buffer:
            print(f"   📦 Consolidating {len(questions_buffer)} questions into one page...")
            
            # Group by Platform
            grouped_questions = {}
            for q in questions_buffer:
                # Simple extraction, assuming source_name contains platform
                platform = q.get('source_name', 'Other').split(' ')[0] 
                if platform not in grouped_questions: grouped_questions[platform] = []
                grouped_questions[platform].append(q)
            
            # Build Rich Content with Cleaner Formatting
            content_blocks = []
            content_blocks.append("# 🔥 Top Community Debates (Daily Digest)\n")
            content_blocks.append(f"_{len(questions_buffer)} trending discussions found across Reddit, X, and HackerNews._\n")
            content_blocks.append("---\n")
            
            for platform, quests in grouped_questions.items():
                # Platform Header with color
                emoji = "🔴" if "Reddit" in platform else "⚫" if "X" in platform else "🔵"
                content_blocks.append(f"## {emoji} {platform}\n")
                
                for q in quests:
                    title_text = q.get('title', 'Unknown').replace("❓", "").strip()
                    url = q.get('source_url', '#')
                    
                    # Clean, spacious format
                    content_blocks.append(f"**{title_text}**")
                    content_blocks.append(f"> {q.get('description')}")
                    content_blocks.append(f"🔗 [View Discussion]({url})\n")
                
                content_blocks.append("---\n")
            
            combined_summary = "\n".join(content_blocks)
            
            # Create the Single Item
            questions_item = NewsItem(
                id=f"questions_{datetime.now().strftime('%Y%m%d_%H%M')}",
                title=f"❓ Daily Community Digest: {len(questions_buffer)} Burning Questions",
                source="Multi-Platform",
                link="https://www.google.com", 
                summary=combined_summary,
                published=datetime.now(),
                score=95,
                category="daily_questions"
            )
            notion_items.append(questions_item)

        # 5. Delivery
        print(f"\n📤 Delivering {len(notion_items)} clutter-free ideas to Notion...")
        success_count = self.notion.deliver_daily_ideas(notion_items)
        
        # 6. Update History (Include question buffer so we don't repeat them)
        if success_count > 0:
            self.history.add_ideas(all_raw_items)
            
        print("\n✅ BRIEFING COMPLETE")

    def _get_emoji(self, category: str) -> str:
        cat_lower = category.lower()
        if "agent" in cat_lower: return "🤖"
        if "build" in cat_lower or "auto" in cat_lower: return "🛠️"
        if "market" in cat_lower or "trend" in cat_lower: return "🔥"
        return "💡"

if __name__ == "__main__":
    briefing = DailyBriefing()
    briefing.run()
