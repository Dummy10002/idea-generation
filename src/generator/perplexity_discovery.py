"""
Perplexity-Powered Idea Discovery
=================================
Uses Perplexity AI to intelligently discover content ideas across categories:
1. 🚀 AI Breakthroughs - New models, agentic tools, research
2. 🔥 Viral AI - Hot discussions, controversial takes, demos
3. 📈 General Trending - Tech news with AI angles

This replaces broken RSS feeds with intelligent discovery.
"""

import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from ..utils.logger import logger


@dataclass
class DiscoveredIdea:
    """A discovered content idea with metadata."""
    title: str
    category: str  # "breakthrough", "viral", "trending"
    source: str
    summary: str
    hook_angles: List[str] = field(default_factory=list)
    key_stats: List[str] = field(default_factory=list)
    virality_score: int = 50
    relevance_score: int = 50
    url: str = ""


class PerplexityDiscovery:
    """
    Discovers content ideas using Perplexity AI.
    
    Instead of scraping broken RSS feeds, we ask Perplexity
    intelligent questions to find the best content.
    """
    
    API_URL = "https://api.perplexity.ai/chat/completions"
    
    # Discovery prompts for each category
    DISCOVERY_PROMPTS = {
        "breakthrough": """You are an AI news researcher. Find the TOP 3 AI breakthroughs from the LAST 24 HOURS.

Focus on:
- New AI model releases (open-source especially: DeepSeek, Qwen, Mistral, Llama)
- New agentic frameworks or autonomous agent tools
- Significant AI research papers with real-world impact
- AI startup launches or major funding
- Developer tools gaining traction

For EACH discovery, provide:
1. **Title**: Clear, engaging headline
2. **Source**: Where you found it (Reddit post, GitHub, news site, paper)
3. **Why it matters**: 1-2 sentences
4. **Key stats**: Numbers, benchmarks, dates
5. **Hook angles**: 2 content angles for short-form video

FORMAT your response as JSON array:
```json
[
  {
    "title": "DeepSeek-R1 Released: Beats GPT-4 on Reasoning",
    "source": "Reddit r/LocalLLaMA (5.2k upvotes)",
    "summary": "DeepSeek released R1, a reasoning-focused model that outperforms GPT-4 on math and coding benchmarks. Fully open-source with MIT license.",
    "key_stats": ["671B parameters", "Runs on 24GB VRAM", "MIT license", "97% on MATH benchmark"],
    "hook_angles": ["The free AI that just embarrassed ChatGPT", "Why OpenAI should be worried right now"]
  }
]
```

Return ONLY the JSON array, no other text.""",

        "viral": """You are a viral content researcher. Find the TOP 3 AI-related discussions that are going VIRAL right now.

Look for:
- Reddit posts with 1000+ upvotes in AI communities
- Twitter/X posts about AI that went viral
- Controversial AI takes or debates
- Amazing AI demos that people are sharing
- AI fails or wins that are getting attention

For EACH viral moment, provide:
1. **Title**: The main topic/headline
2. **Source**: Platform and engagement (upvotes, likes, views)
3. **Why it's viral**: What's making people engage
4. **The controversy/hook**: What's the debate or wow factor
5. **Content angles**: 2 angles you could use

FORMAT as JSON array:
```json
[
  {
    "title": "AI Girlfriend App Made $100M in 30 Days",
    "source": "Twitter @aibreakfast (45k likes)",
    "summary": "A solo developer's AI companion app hit $100M revenue in a month, sparking debate about AI relationships and the loneliness epidemic.",
    "key_stats": ["$100M in 30 days", "1 developer", "10M downloads"],
    "hook_angles": ["This guy made $100M with an AI girlfriend app", "The dark side of AI companions nobody talks about"]
  }
]
```

Return ONLY the JSON array.""",

        "trending": """You are a trend analyst. Find TOP 3 trending tech/general topics that could be given an AI ANGLE for content.

Look for:
- Tech news that intersects with AI
- Pop culture moments that can connect to AI
- Business news about AI companies
- Policy/regulation news about AI
- "Future of X" topics where AI is relevant

For EACH trend, provide:
1. **Title**: The trending topic
2. **Source**: Where it's trending
3. **The AI angle**: How to connect this to AI content
4. **Why it works**: Why this would resonate with audiences
5. **Content angles**: 2 ways to cover this

FORMAT as JSON array:
```json
[
  {
    "title": "Apple Delays AI Features in EU Due to Regulations",
    "source": "TechCrunch, trending on HackerNews",
    "summary": "Apple won't launch Apple Intelligence in EU due to DMA regulations. Shows the growing tension between AI development and regulation.",
    "key_stats": ["500M EU users affected", "DMA regulation", "2025 delay"],
    "hook_angles": ["Why your iPhone AI is different in Europe", "The law that's holding back AI in Europe"]
  }
]
```

Return ONLY the JSON array."""
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with Perplexity API key."""
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            logger.warning("PERPLEXITY_API_KEY not set - discovery will fail")
        
        self.session_cost = 0.0
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def _query_perplexity(self, prompt: str, max_tokens: int = 1500) -> Optional[Dict]:
        """Query Perplexity API."""
        if not self.api_key:
            return None
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "sonar",  # Cheapest model
            "messages": [
                {
                    "role": "system",
                    "content": "You are a content researcher. Return ONLY valid JSON arrays. No markdown, no explanations, just the JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": max_tokens,
            "temperature": 0.2,
            "return_citations": True,
            "search_recency_filter": "day"
        }
        
        try:
            response = requests.post(
                self.API_URL,
                headers=headers,
                json=payload,
                timeout=45
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Track cost
            usage = data.get("usage", {})
            tokens = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
            cost = tokens * 0.000001  # $1 per 1M tokens
            self.session_cost += cost
            
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            citations = data.get("citations", [])
            
            return {
                "content": content,
                "citations": citations,
                "tokens": tokens,
                "cost": cost
            }
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Perplexity API error: {e.response.status_code} - {e.response.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"Perplexity request failed: {e}")
            return None
    
    def _parse_json_response(self, content: str) -> List[Dict]:
        """Parse JSON from Perplexity response."""
        import json
        import re
        
        # Try to extract JSON from the response
        # Sometimes Perplexity wraps it in markdown code blocks
        json_match = re.search(r'\[[\s\S]*\]', content)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Try parsing the whole thing
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.warning("Could not parse JSON from Perplexity response")
            return []
    
    def discover_category(self, category: str) -> List[DiscoveredIdea]:
        """
        Discover ideas for a specific category.
        
        Args:
            category: One of "breakthrough", "viral", "trending"
            
        Returns:
            List of DiscoveredIdea objects
        """
        if category not in self.DISCOVERY_PROMPTS:
            logger.error(f"Unknown category: {category}")
            return []
        
        prompt = self.DISCOVERY_PROMPTS[category]
        
        logger.info(f"🔍 Discovering {category} ideas...")
        result = self._query_perplexity(prompt)
        
        if not result:
            logger.warning(f"Discovery failed for {category}")
            return []
        
        # Parse the JSON response
        items = self._parse_json_response(result["content"])
        
        ideas = []
        for item in items:
            try:
                idea = DiscoveredIdea(
                    title=item.get("title", "Untitled"),
                    category=category,
                    source=item.get("source", "Unknown"),
                    summary=item.get("summary", ""),
                    hook_angles=item.get("hook_angles", []),
                    key_stats=item.get("key_stats", []),
                    virality_score=80 if category == "viral" else 60,
                    relevance_score=90 if category == "breakthrough" else 70,
                    url=""
                )
                ideas.append(idea)
            except Exception as e:
                logger.warning(f"Failed to parse idea: {e}")
                continue
        
        logger.info(f"   Found {len(ideas)} {category} ideas (cost: ${result['cost']:.4f})")
        return ideas
    
    def discover_all(self) -> List[DiscoveredIdea]:
        """
        Discover ideas across all categories.
        
        Returns:
            Combined list of ideas from all categories
        """
        all_ideas = []
        
        for category in ["breakthrough", "viral", "trending"]:
            ideas = self.discover_category(category)
            all_ideas.extend(ideas)
        
        logger.info(f"📊 Total discovered: {len(all_ideas)} ideas, Session cost: ${self.session_cost:.4f}")
        return all_ideas
    
    def get_session_cost(self) -> float:
        """Return total cost for this session."""
        return self.session_cost
