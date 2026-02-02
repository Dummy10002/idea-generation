"""
Deep AI Trend Discovery - PRODUCTION QUALITY
=============================================
Finds REAL trending content from Reddit, Quora, X/Twitter with complete research.

This is NOT a simple news aggregator. It:
1. Queries Perplexity to find ACTUAL trending posts with engagement stats
2. Deep dives into each topic for complete research
3. Delivers COMPLETE content-ready packages to Notion

Budget: ~$0.01 per run (3 discovery + 5 research queries = 8 total)
"""

import os
import json
import re
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from ..utils.logger import logger


@dataclass
class TrendingIdea:
    """A fully researched trending idea ready for content creation."""
    title: str
    category: str
    platform: str
    engagement: str  # e.g., "2.5k upvotes on r/ChatGPT"
    summary: str
    why_trending: str
    key_facts: List[str]
    statistics: List[str]
    controversy_or_hook: str
    content_angles: List[str]
    sources: List[str]
    full_research: str  # Complete research text


class DeepTrendDiscovery:
    """
    Deep discovery of REAL trending AI content from Reddit, Quora, X.
    
    Uses Perplexity to find actual posts with engagement metrics,
    then does deep research on each topic.
    """
    
    API_URL = "https://api.perplexity.ai/chat/completions"
    
    # Multi-step discovery: First find trends, then research each
    TREND_FINDER_PROMPTS = {
        "reddit_ai": """What are the TOP 5 most upvoted posts from TODAY on AI subreddits like r/ChatGPT, r/LocalLLaMA, r/MachineLearning, r/OpenAI, r/artificial?

Return as a JSON array with exactly this structure:
[{"title": "Post title", "subreddit": "r/SubName", "upvotes": "1.5k", "why_trending": "Brief reason", "topic": "Category"}]

Focus on AI breakthroughs, new models, agentic tools, AI debates. Skip memes.
Return ONLY the JSON array, nothing else.""",

        "quora_ai": """What are the TOP 3 most discussed AI questions on Quora from the last 48 hours?

Return as a JSON array with exactly this structure:
[{"question": "Question text", "engagement": "50k views", "main_insight": "Key insight from answers", "why_trending": "Brief reason"}]

Focus on AI breakthroughs, model comparisons, job impact, controversial takes.
Return ONLY the JSON array, nothing else.""",

        "twitter_ai": """What are the TOP 3 viral AI posts on X/Twitter from TODAY?

Return as a JSON array with exactly this structure:
[{"topic": "What the post is about", "author": "@username", "engagement": "25k likes", "insight": "Key takeaway", "why_viral": "Brief reason"}]

Focus on AI demos, company announcements, agentic tools, breakthroughs, controversies.
Return ONLY the JSON array, nothing else."""
    }
    
    DEEP_RESEARCH_PROMPT = """You are researching a trending AI topic for content creation. Research this topic DEEPLY:

**TOPIC:** {topic}
**SOURCE:** {source}
**WHY IT'S TRENDING:** {why_trending}

---

Provide COMPREHENSIVE research including:

## 1. CORE FACTS
- What exactly is this about? (specific names, dates, versions)
- Who is involved? (companies, people, researchers)
- When did this happen/start trending?

## 2. KEY STATISTICS & NUMBERS
- Any benchmarks or performance numbers?
- User counts, growth rates, funding amounts?
- Comparison numbers (X% better than Y)?

## 3. THE CONTROVERSY/DEBATE
- What are people arguing about?
- What are the opposing viewpoints?
- Any drama or conflict?

## 4. COMMUNITY REACTIONS
- What are Reddit users saying?
- What are Twitter/X experts saying?
- Common praises and criticisms?

## 5. CONTENT ANGLES (For short-form video)
- 3 attention-grabbing hooks
- The "viewer transformation" - what can viewers DO with this info?
- Controversy angle to drive engagement
- Educational angle for authority

## 6. SOURCES USED
- List the main sources you found

---

Be SPECIFIC. Include REAL numbers, REAL usernames, REAL quotes when possible.
This research should be complete enough that someone could create content WITHOUT additional research."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with Perplexity API key."""
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            logger.warning("PERPLEXITY_API_KEY not set")
        
        self.session_cost = 0.0
        self.query_count = 0
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def _query_perplexity(self, prompt: str, max_tokens: int = 2000) -> Optional[Dict]:
        """Query Perplexity API."""
        if not self.api_key:
            return None
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "sonar",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a trend researcher. Return data ONLY as valid JSON arrays. No explanations, no markdown, no code blocks - just the raw JSON array starting with [ and ending with ]."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": max_tokens,
            "temperature": 0.1,
            "return_citations": True,
            "search_recency_filter": "day"
        }
        
        try:
            response = requests.post(
                self.API_URL,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Track cost
            usage = data.get("usage", {})
            tokens = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
            cost = tokens * 0.000001
            self.session_cost += cost
            self.query_count += 1
            
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            citations = data.get("citations", [])
            
            return {
                "content": content,
                "citations": citations,
                "tokens": tokens,
                "cost": cost
            }
            
        except Exception as e:
            logger.error(f"Perplexity request failed: {e}")
            return None
    
    def _parse_json(self, content: str) -> List[Dict]:
        """Parse JSON from response - handles various Perplexity formats."""
        import json
        import re
        
        # Clean up the content
        content = content.strip()
        
        # Remove markdown code blocks
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        
        # Try to find the JSON array
        # First, look for array brackets
        start_idx = content.find('[')
        end_idx = content.rfind(']')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = content[start_idx:end_idx + 1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # Try to fix common issues
                json_str = json_str.replace('\n', ' ')
                json_str = re.sub(r',\s*]', ']', json_str)  # Trailing commas
                json_str = re.sub(r',\s*}', '}', json_str)  # Trailing commas in objects
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
        
        # If that fails, try parsing the whole content
        try:
            result = json.loads(content)
            if isinstance(result, list):
                return result
            return []
        except json.JSONDecodeError:
            logger.warning(f"Could not parse JSON from response (length: {len(content)})")
            logger.debug(f"Response content: {content[:500]}...")
            return []
    
    def discover_trends(self) -> List[Dict]:
        """
        Step 1: Find trending topics across platforms.
        Returns raw trend data for deep research.
        """
        all_trends = []
        
        for platform, prompt in self.TREND_FINDER_PROMPTS.items():
            logger.info(f"🔍 Finding trends on {platform}...")
            
            result = self._query_perplexity(prompt, max_tokens=1500)
            if not result:
                continue
            
            items = self._parse_json(result["content"])
            
            for item in items:
                item["platform"] = platform
                item["citations"] = result.get("citations", [])
            
            all_trends.extend(items)
            logger.info(f"   Found {len(items)} trends (cost: ${result['cost']:.4f})")
        
        return all_trends
    
    def deep_research_topic(self, trend: Dict) -> Optional[TrendingIdea]:
        """
        Step 2: Deep research a single trending topic.
        Returns a fully researched idea ready for content.
        """
        # Build the topic description
        if "title" in trend:
            topic = trend["title"]
            source = f"{trend.get('subreddit', trend.get('platform', 'Unknown'))} ({trend.get('upvotes', 'popular')})"
            why = trend.get("why_trending", trend.get("topic", ""))
        elif "question" in trend:
            topic = trend["question"]
            source = f"Quora ({trend.get('engagement', 'popular')})"
            why = trend.get("why_trending", "")
        elif "topic" in trend:
            topic = trend["topic"]
            source = f"X/Twitter - {trend.get('author', '')} ({trend.get('engagement', '')})"
            why = trend.get("why_viral", trend.get("insight", ""))
        else:
            return None
        
        logger.info(f"   📚 Deep researching: {topic[:50]}...")
        
        prompt = self.DEEP_RESEARCH_PROMPT.format(
            topic=topic,
            source=source,
            why_trending=why
        )
        
        result = self._query_perplexity(prompt, max_tokens=2500)
        if not result:
            return None
        
        # Parse the research into structured format
        research_text = result["content"]
        
        # Extract content angles from research
        angles = []
        hooks_match = re.search(r'hooks?[:\s]*(.*?)(?:\n\n|\n##|\Z)', research_text, re.IGNORECASE | re.DOTALL)
        if hooks_match:
            angle_lines = hooks_match.group(1).strip().split('\n')
            angles = [line.strip('- •').strip() for line in angle_lines if line.strip('- •').strip()][:3]
        
        # Extract key facts
        facts = []
        facts_match = re.search(r'CORE FACTS[:\s]*(.*?)(?:\n##|\Z)', research_text, re.IGNORECASE | re.DOTALL)
        if facts_match:
            fact_lines = facts_match.group(1).strip().split('\n')
            facts = [line.strip('- •').strip() for line in fact_lines if line.strip('- •').strip()][:5]
        
        # Extract statistics
        stats = []
        stats_match = re.search(r'STATISTICS[:\s]*(.*?)(?:\n##|\Z)', research_text, re.IGNORECASE | re.DOTALL)
        if stats_match:
            stat_lines = stats_match.group(1).strip().split('\n')
            stats = [line.strip('- •').strip() for line in stat_lines if line.strip('- •').strip()][:5]
        
        # Extract controversy
        controversy = ""
        controversy_match = re.search(r'CONTROVERSY[:\s]*(.*?)(?:\n##|\Z)', research_text, re.IGNORECASE | re.DOTALL)
        if controversy_match:
            controversy = controversy_match.group(1).strip()[:500]
        
        idea = TrendingIdea(
            title=topic,
            category=trend.get("platform", "unknown").replace("_", " ").title(),
            platform=trend.get("subreddit", trend.get("author", trend.get("platform", ""))),
            engagement=trend.get("upvotes", trend.get("engagement", "")),
            summary=why,
            why_trending=why,
            key_facts=facts or ["See full research below"],
            statistics=stats or ["See full research below"],
            controversy_or_hook=controversy or "See full research below",
            content_angles=angles or ["See full research below"],
            sources=result.get("citations", [])[:5],
            full_research=research_text
        )
        
        logger.info(f"      ✅ Research complete (${result['cost']:.4f})")
        return idea
    
    def run_full_discovery(self, max_research: int = 5) -> List[TrendingIdea]:
        """
        Full discovery pipeline:
        1. Find trends across platforms
        2. Deep research top N trends
        3. Return fully researched ideas
        """
        logger.info("=" * 60)
        logger.info("🚀 DEEP TREND DISCOVERY - Finding REAL trending content")
        logger.info("=" * 60)
        
        # Step 1: Find trends
        logger.info("")
        logger.info("📡 STEP 1: Scanning Reddit, Quora, X for trends...")
        trends = self.discover_trends()
        
        if not trends:
            logger.error("❌ No trends found. Check Perplexity API.")
            return []
        
        logger.info(f"")
        logger.info(f"✅ Found {len(trends)} trending topics")
        
        # Step 2: Deep research top trends
        logger.info("")
        logger.info(f"📚 STEP 2: Deep researching top {max_research} trends...")
        
        researched_ideas = []
        for i, trend in enumerate(trends[:max_research], 1):
            title = trend.get("title", trend.get("question", trend.get("topic", "Unknown")))
            logger.info(f"   [{i}/{min(len(trends), max_research)}] {title[:50]}...")
            
            idea = self.deep_research_topic(trend)
            if idea:
                researched_ideas.append(idea)
        
        logger.info("")
        logger.info(f"💰 Total cost: ${self.session_cost:.4f} ({self.query_count} queries)")
        
        return researched_ideas
    
    def get_session_stats(self) -> Dict:
        """Return session statistics."""
        return {
            "cost": self.session_cost,
            "queries": self.query_count,
            "cost_per_query": self.session_cost / max(1, self.query_count)
        }
