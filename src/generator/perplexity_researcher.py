"""
Perplexity AI Deep Researcher
=============================
Uses Perplexity Sonar API for deep research across Reddit, Quora, Google Trends, and more.

COST OPTIMIZATION:
- Uses 'sonar' model (cheapest: $1/1M tokens in + $1/1M tokens out)
- ~$0.002 per request average
- With $5 credit = ~2,500 requests = ~83/day for a month
- We use 8 ideas × 1 research = 8 requests/day
- Your $5 will last well over 3 months!

API Setup:
1. Go to: https://www.perplexity.ai/settings/api
2. Copy your API key (starts with 'pplx-')
3. Add to .env: PERPLEXITY_API_KEY=pplx-xxxxx
"""

import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from ..utils.logger import logger


@dataclass
class PerplexityUsage:
    """Track API usage for cost monitoring."""
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float = 0.0


class PerplexityResearcher:
    """
    Deep research engine powered by Perplexity AI.
    
    Perplexity automatically searches:
    - Reddit discussions
    - Quora Q&A
    - News articles
    - Academic sources
    - Google results
    - And more...
    
    All in a single API call! Much better than manual scraping.
    """
    
    API_URL = "https://api.perplexity.ai/chat/completions"
    
    # Cost per 1M tokens (for monitoring)
    INPUT_COST_PER_M = 1.0   # $1 per 1M input tokens
    OUTPUT_COST_PER_M = 1.0  # $1 per 1M output tokens
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Perplexity researcher.
        
        Args:
            api_key: Perplexity API key (or set PERPLEXITY_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY", "")
        self.session_usage = PerplexityUsage()
        
        if not self.api_key:
            logger.warning("PERPLEXITY_API_KEY not set. Research will fail.")
    
    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate estimated cost in USD."""
        input_cost = (input_tokens / 1_000_000) * self.INPUT_COST_PER_M
        output_cost = (output_tokens / 1_000_000) * self.OUTPUT_COST_PER_M
        return input_cost + output_cost
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def _query_perplexity(self, prompt: str, max_tokens: int = 500) -> Optional[Dict]:
        """
        Make a single query to Perplexity API.
        
        Args:
            prompt: The research prompt
            max_tokens: Maximum response tokens (keep low to save costs)
            
        Returns:
            Response dict with content and usage
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "sonar",  # Cheapest model: $1/1M tokens
            "messages": [
                {
                    "role": "system",
                    "content": "You are a research assistant. Provide factual, concise information with specific numbers, dates, and sources when possible. Focus on recent information (last 24-48 hours for news)."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": max_tokens,
            "temperature": 0.1,  # Low for factual responses
            "return_citations": True,  # Include source URLs
            "search_recency_filter": "day"  # Last 24 hours only!
        }
        
        try:
            response = requests.post(
                self.API_URL,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Track usage
            usage = data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            
            self.session_usage.input_tokens += input_tokens
            self.session_usage.output_tokens += output_tokens
            self.session_usage.estimated_cost += self._estimate_cost(input_tokens, output_tokens)
            
            logger.debug(f"Perplexity tokens: {input_tokens} in, {output_tokens} out, ${self._estimate_cost(input_tokens, output_tokens):.4f}")
            
            return {
                "content": data.get("choices", [{}])[0].get("message", {}).get("content", ""),
                "citations": data.get("citations", []),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens
            }
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Perplexity API error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Perplexity request failed: {e}")
            return None
    
    def research_topic(self, topic: str) -> Dict:
        """
        Perform comprehensive research on a topic.
        
        Uses a SINGLE Perplexity query that searches across:
        - Reddit (all relevant subreddits)
        - Quora discussions
        - Google Trends data
        - Recent news articles
        - And more...
        
        Returns:
            Comprehensive research report
        """
        logger.info(f"🔍 Perplexity researching: {topic}")
        
        # COMPREHENSIVE prompt - explicitly covers ALL relevant sources for AI niche
        prompt = f"""You are researching an AI/tech news topic. Search DEEPLY across ALL these sources.

**TOPIC:** {topic}

---

## REQUIRED RESEARCH (Cover ALL of these):

### 1. 📊 KEY FACTS & NUMBERS
- What exactly happened? (specific dates, version numbers, company names)
- Any performance benchmarks or statistics?
- Pricing or cost information?
- Release dates or availability?

### 2. 💬 REDDIT DISCUSSIONS (Search these subreddits specifically)
- r/MachineLearning - What are ML researchers saying?
- r/ChatGPT - User experiences and reactions?
- r/OpenAI - OpenAI community discussions?
- r/LocalLLaMA - Is there a local/open-source angle?
- r/artificial - General AI community sentiment?
- r/singularity - Future implications?
- r/StableDiffusion - If image/video related
- What are the TOP UPVOTED comments? Any controversies?

### 3. 🤔 QUORA Q&A
- Any questions being asked about this topic?
- What answers are getting upvotes?
- Expert opinions on Quora?

### 4. 🐦 TWITTER/X DISCUSSIONS
- What are AI influencers saying? (@sama, @ylecun, @kaboris, @DrJimFan)
- Any viral tweets about this topic?
- Community reactions on X?

### 5. 📰 NEWS & TECH PUBLICATIONS
- TechCrunch, The Verge, Wired, Ars Technica coverage?
- Any exclusive interviews or announcements?
- Tech blog reactions (Simon Willison, etc.)?

### 6. 🚀 HACKER NEWS (news.ycombinator.com)
- Is this on the front page?
- What do developers/engineers think?
- Any technical criticisms or praise?

### 7. 📈 GOOGLE TRENDS
- Is this topic trending? In which regions?
- Related search queries?
- Trend velocity (rising fast or slow)?

### 8. 🎯 CONTENT ANGLES (for short-form video)
- 3 attention-grabbing hooks for this topic
- What's the "viewer transformation"? (What can viewers DO with this info?)
- Any controversial or surprising angles?

---

**IMPORTANT:** 
- Focus on the LAST 24-48 HOURS only
- Include SPECIFIC numbers, dates, usernames when available
- Note which sources had the most engagement
- Highlight any CONTROVERSIES or DEBATES"""

        result = self._query_perplexity(prompt, max_tokens=1000)  # Increased for comprehensive response
        
        if not result:
            logger.warning("Perplexity research failed, returning empty report")
            return self._empty_report(topic)
        
        # Parse and structure the response
        report = {
            "topic": topic,
            "researched_at": datetime.now().isoformat(),
            "content": result["content"],
            "citations": result["citations"],
            "tokens_used": result["input_tokens"] + result["output_tokens"],
            "estimated_cost": self._estimate_cost(result["input_tokens"], result["output_tokens"])
        }
        
        logger.info(f"✅ Research complete: {report['tokens_used']} tokens, ${report['estimated_cost']:.4f}")
        
        return report
    
    def _empty_report(self, topic: str) -> Dict:
        """Return empty report on failure."""
        return {
            "topic": topic,
            "researched_at": datetime.now().isoformat(),
            "content": "Research failed. Please check your Perplexity API key.",
            "citations": [],
            "tokens_used": 0,
            "estimated_cost": 0.0
        }
    
    def get_session_stats(self) -> Dict:
        """Get usage statistics for the current session."""
        return {
            "total_input_tokens": self.session_usage.input_tokens,
            "total_output_tokens": self.session_usage.output_tokens,
            "total_cost": f"${self.session_usage.estimated_cost:.4f}",
            "remaining_budget": f"${5.0 - self.session_usage.estimated_cost:.2f} (assuming $5 credit)"
        }
    
    def format_for_notion(self, report: Dict) -> str:
        """Format research report for Notion delivery."""
        lines = [
            f"# 🔬 Research: {report['topic']}",
            f"*Generated: {report['researched_at'][:16]}*",
            "",
            report['content'],
            "",
            "---",
            "",
            f"**Sources:** {len(report['citations'])} citations",
        ]
        
        if report['citations']:
            for i, url in enumerate(report['citations'][:5], 1):
                lines.append(f"{i}. {url}")
        
        lines.extend([
            "",
            f"💰 **Cost:** ${report['estimated_cost']:.4f} ({report['tokens_used']} tokens)"
        ])
        
        return "\n".join(lines)
    
    def batch_research(self, topics: List[str], max_topics: int = 3) -> Dict[str, Dict]:
        """
        Research multiple topics efficiently.
        
        Args:
            topics: List of topic strings
            max_topics: Maximum topics to research (cost control)
            
        Returns:
            Dict mapping topic -> research report
        """
        reports = {}
        
        for topic in topics[:max_topics]:
            report = self.research_topic(topic)
            reports[topic] = report
            
            # Small delay to be respectful
            import time
            time.sleep(0.5)
        
        # Log session stats
        stats = self.get_session_stats()
        logger.info(f"📊 Session stats: {stats['total_cost']} used, {stats['remaining_budget']} remaining")
        
        return reports
