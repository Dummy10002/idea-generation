"""
AI Idea Discovery - ULTIMATE VERSION
=====================================
Combines the best of V2 (AI breakthroughs) and V3 (deep research) into one powerful system.

Discovery Categories:
1. 🚀 AI Breakthroughs - New models, agentic tools, research (from Perplexity)
2. 🔥 Reddit Trending - Hot AI discussions from r/ChatGPT, r/LocalLLaMA, etc.
3. 📈 Viral Content - What's going viral on X/Twitter
4. ❓ Quora Debates - Popular AI questions and controversies

Budget: ~$0.015 per run (under 2 cents!)
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
class DiscoveredIdea:
    """A fully researched content idea."""
    title: str
    category: str  # breakthrough, reddit, twitter, quora
    source: str
    engagement: str
    summary: str
    key_facts: List[str]
    hook_angles: List[str]
    controversy: str
    full_research: str


class UltimateAIDiscovery:
    """
    The ultimate AI content idea discovery system.
    
    Uses targeted Perplexity prompts optimized for each platform.
    """
    
    API_URL = "https://api.perplexity.ai/chat/completions"
    
    # Optimized prompts for each discovery type
    DISCOVERY_PROMPTS = {
        "ai_breakthroughs": """What are the TOP 5 most significant AI breakthroughs, releases, or announcements from TODAY?

Include:
- New AI model releases (DeepSeek, Qwen, Mistral, Llama, GPT, Claude updates)
- New agentic frameworks or autonomous agent tools  
- Major AI research papers or demos
- AI company announcements (funding, launches, acquisitions)
- Developer tools gaining traction

Return JSON array:
[{"title": "What happened", "source": "Where it was announced", "impact": "Why it matters", "stats": "Key numbers/benchmarks", "category": "model/tool/research/company"}]

Return ONLY valid JSON array. Be specific with real names and numbers.""",

        "reddit_hot": """What are the TOP 5 hottest discussions happening RIGHT NOW on Reddit AI communities?

Search these subreddits: r/ChatGPT, r/LocalLLaMA, r/MachineLearning, r/artificial, r/OpenAI, r/singularity

For each, provide the discussion topic, subreddit, approximate engagement, and why people are excited/upset.

Return JSON array:
[{"topic": "Discussion topic", "subreddit": "r/SubName", "engagement": "2k upvotes", "why_hot": "Why people are talking about it"}]

Return ONLY valid JSON array.""",

        "twitter_viral": """What AI-related content went VIRAL on X/Twitter in the last 24 hours?

Look for:
- AI demos that blew up
- Controversial takes from @sama, @ylecun, @karpathy, @DrJimFan
- New tool announcements
- AI memes or debates

Return JSON array:
[{"content": "What the viral thing is about", "author": "@username", "engagement": "50k likes", "why_viral": "What made it spread"}]

Return ONLY valid JSON array.""",

        "quora_debates": """What are the HOTTEST AI-related questions being debated on Quora right now?

Focus on:
- GPT vs Claude vs Gemini comparisons
- AI job replacement fears
- New AI capabilities
- AI ethics debates

Return JSON array:
[{"question": "The question", "views": "100k views", "debate": "The main argument", "insight": "Key takeaway"}]

Return ONLY valid JSON array."""
    }
    
    # Deep research prompt for each discovered idea
    RESEARCH_PROMPT = """Research this AI topic for content creation:

TOPIC: {topic}
SOURCE: {source}
CONTEXT: {context}

Provide:

## CORE FACTS
- What exactly is this? (specific names, versions, dates)
- Who's involved? (companies, researchers)

## KEY STATISTICS  
- Numbers and benchmarks
- Comparisons to competitors

## THE HOOK
- Why should viewers care?
- What's controversial or surprising?
- 3 attention-grabbing angles

## CONTENT IDEAS
- Hook for short-form video
- Transformation for viewer
- Call to action

Be SPECIFIC with real data."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            logger.warning("PERPLEXITY_API_KEY not set")
        self.session_cost = 0.0
        self.query_count = 0
    
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=2, max=10))
    def _query(self, prompt: str, max_tokens: int = 2000, is_json: bool = True) -> Optional[Dict]:
        """Query Perplexity API."""
        if not self.api_key:
            return None
        
        system_msg = "Return ONLY valid JSON arrays, no markdown, no explanation." if is_json else "Provide detailed, accurate research."
        
        payload = {
            "model": "sonar",
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.1,
            "return_citations": True,
            "search_recency_filter": "day"
        }
        
        try:
            response = requests.post(
                self.API_URL,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            
            usage = data.get("usage", {})
            tokens = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
            cost = tokens * 0.000001
            self.session_cost += cost
            self.query_count += 1
            
            return {
                "content": data.get("choices", [{}])[0].get("message", {}).get("content", ""),
                "citations": data.get("citations", []),
                "cost": cost
            }
        except Exception as e:
            logger.error(f"Perplexity error: {e}")
            return None
    
    def _parse_json(self, content: str) -> List[Dict]:
        """Robust JSON parsing."""
        content = content.strip()
        content = re.sub(r'```json?\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        
        start = content.find('[')
        end = content.rfind(']')
        
        if start != -1 and end != -1 and end > start:
            json_str = content[start:end + 1]
            # Fix common issues
            json_str = json_str.replace('\n', ' ')
            json_str = re.sub(r',\s*]', ']', json_str)
            json_str = re.sub(r',\s*}', '}', json_str)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        try:
            result = json.loads(content)
            return result if isinstance(result, list) else []
        except:
            logger.warning(f"JSON parse failed: {content[:200]}...")
            return []
    
    def discover_all(self) -> List[Dict]:
        """Discover trends across all platforms."""
        all_discoveries = []
        
        for category, prompt in self.DISCOVERY_PROMPTS.items():
            logger.info(f"🔍 Discovering {category}...")
            result = self._query(prompt, max_tokens=1500)
            
            if result:
                items = self._parse_json(result["content"])
                for item in items:
                    item["category"] = category
                all_discoveries.extend(items)
                logger.info(f"   Found {len(items)} (${result['cost']:.4f})")
            else:
                logger.warning(f"   Failed to discover {category}")
        
        return all_discoveries
    
    def deep_research(self, item: Dict) -> Optional[DiscoveredIdea]:
        """Deep research a single discovery."""
        # Determine topic and context based on category
        category = item.get("category", "unknown")
        
        if category == "ai_breakthroughs":
            topic = item.get("title", "")
            source = item.get("source", "")
            context = item.get("impact", "")
        elif category == "reddit_hot":
            topic = item.get("topic", "")
            source = item.get("subreddit", "Reddit")
            context = item.get("why_hot", "")
        elif category == "twitter_viral":
            topic = item.get("content", "")
            source = f"X/Twitter - {item.get('author', '')}"
            context = item.get("why_viral", "")
        elif category == "quora_debates":
            topic = item.get("question", "")
            source = "Quora"
            context = item.get("debate", "")
        else:
            return None
        
        if not topic:
            return None
        
        logger.info(f"   📚 Researching: {topic[:50]}...")
        
        prompt = self.RESEARCH_PROMPT.format(
            topic=topic,
            source=source,
            context=context
        )
        
        result = self._query(prompt, max_tokens=2000, is_json=False)
        if not result:
            return None
        
        research = result["content"]
        
        # Extract key parts
        facts = []
        facts_match = re.search(r'CORE FACTS.*?(?=##|\Z)', research, re.IGNORECASE | re.DOTALL)
        if facts_match:
            facts = [l.strip('- •').strip() for l in facts_match.group().split('\n') if l.strip('- •').strip()][:4]
        
        hooks = []
        hook_match = re.search(r'(?:HOOK|CONTENT IDEAS).*?(?=##|\Z)', research, re.IGNORECASE | re.DOTALL)
        if hook_match:
            hooks = [l.strip('- •').strip() for l in hook_match.group().split('\n') if l.strip('- •').strip()][:3]
        
        controversy = ""
        cont_match = re.search(r'(?:controversial|surprising|hook).*?[:\s](.*?)(?:\n|$)', research, re.IGNORECASE)
        if cont_match:
            controversy = cont_match.group(1).strip()[:300]
        
        engagement = item.get("engagement", item.get("stats", "trending"))
        
        idea = DiscoveredIdea(
            title=topic,
            category=category,
            source=source,
            engagement=engagement,
            summary=context,
            key_facts=facts or ["See research below"],
            hook_angles=hooks or ["See research below"],
            controversy=controversy or "See research below",
            full_research=research
        )
        
        logger.info(f"      ✅ Done (${result['cost']:.4f})")
        return idea
    
    def run(self, max_research: int = 6) -> List[DiscoveredIdea]:
        """Full discovery pipeline."""
        logger.info("=" * 70)
        logger.info("🚀 ULTIMATE AI IDEA DISCOVERY")
        logger.info("=" * 70)
        
        # Step 1: Discover across all platforms
        logger.info("")
        logger.info("📡 STEP 1: Multi-Platform Discovery...")
        discoveries = self.discover_all()
        
        if not discoveries:
            logger.error("❌ No discoveries")
            return []
        
        logger.info(f"")
        logger.info(f"✅ Found {len(discoveries)} raw ideas")
        
        # Step 2: Deep research top items
        logger.info("")
        logger.info(f"📚 STEP 2: Deep Research (top {max_research})...")
        
        ideas = []
        for i, item in enumerate(discoveries[:max_research], 1):
            title = item.get("title", item.get("topic", item.get("content", item.get("question", "?"))))
            logger.info(f"   [{i}/{min(len(discoveries), max_research)}] {title[:50]}...")
            
            idea = self.deep_research(item)
            if idea:
                ideas.append(idea)
        
        logger.info("")
        logger.info(f"💰 Total: ${self.session_cost:.4f} ({self.query_count} queries)")
        
        return ideas
    
    def get_stats(self) -> Dict:
        return {"cost": self.session_cost, "queries": self.query_count}
