"""
News Aggregator
===============
Combines RSS and Trends collectors, scores items, and produces final ranked list.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List

from .rss_collector import RSSCollector, NewsItem
from .trends_collector import TrendsCollector
from .social_media_collector import SocialMediaCollector
from ..utils.config import settings
from ..utils.logger import logger
from ..utils.rate_limiter import rate_limiter


class NewsAggregator:
    """
    Orchestrates news collection from all sources.
    
    Features:
    - Combines AI news + Trending topics
    - Scores and ranks items
    - Deduplicates across sources
    - Respects rate limits
    - Persists history for deduplication across days
    """
    
    HISTORY_FILE = Path(__file__).parent.parent.parent / "data" / "news_history.json"
    
    def __init__(self):
        self.rss_collector = RSSCollector(feeds=settings.ai_news_feeds)
        self.trends_collector = TrendsCollector(geo="IN", max_items=3)
        self.social_collector = SocialMediaCollector(max_items=5)
        self.history = self._load_history()
    
    def _load_history(self) -> dict:
        """Load recent news history for deduplication."""
        self.HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        if self.HISTORY_FILE.exists():
            try:
                with open(self.HISTORY_FILE, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                logger.warning("Corrupted history file, starting fresh")
        
        return {"seen_titles": [], "last_updated": None}
    
    def _save_history(self, items: List[NewsItem]) -> None:
        """Save news titles to history (keep last 100)."""
        titles = [item.title.lower()[:50] for item in items]
        
        # Merge with existing, keep last 100
        all_titles = self.history.get("seen_titles", []) + titles
        self.history["seen_titles"] = all_titles[-100:]
        self.history["last_updated"] = datetime.now().isoformat()
        
        with open(self.HISTORY_FILE, 'w') as f:
            json.dump(self.history, f, indent=2)
    
    def _is_duplicate(self, title: str) -> bool:
        """Check if we've shown this title recently."""
        normalized = title.lower()[:50]
        return normalized in self.history.get("seen_titles", [])
    
    def _score_item(self, item: NewsItem) -> float:
        """
        Score item for ranking (higher = better).
        
        Factors:
        - Recency (40%): Newer is better
        - AI Relevance (30%): Keywords boost score
        - Engagement potential (30%): Questions, numbers, controversy
        """
        score = 0.0
        
        # Recency score (0-40)
        if item.published:
            hours_old = (datetime.now() - item.published).total_seconds() / 3600
            recency_score = max(0, 40 - (hours_old * 2))  # Lose 2 points per hour
            score += recency_score
        else:
            score += 20  # Unknown date gets middle score
        
        # AI relevance score (0-30)
        ai_keywords = [
            "ai", "gpt", "claude", "gemini", "llm", "chatgpt", "openai",
            "anthropic", "deepseek", "midjourney", "runway", "sora",
            "automation", "agent", "model", "neural", "machine learning"
        ]
        title_lower = item.title.lower()
        keyword_matches = sum(1 for kw in ai_keywords if kw in title_lower)
        score += min(30, keyword_matches * 10)
        
        # Engagement potential (0-30)
        engagement_signals = [
            ("?" in item.title, 10),  # Questions engage
            (any(char.isdigit() for char in item.title), 5),  # Numbers = specificity
            ("new" in title_lower or "launch" in title_lower, 10),  # Fresh news
            ("free" in title_lower, 5),  # People love free
            ("vs" in title_lower or "better" in title_lower, 5),  # Comparisons
        ]
        for signal, points in engagement_signals:
            if signal:
                score += points
        
        return min(100, score)  # Cap at 100
    
    def collect_all(self) -> List[NewsItem]:
        """
        Collect and rank news from all sources.
        
        Returns:
            Ranked list of NewsItem objects (top 8)
        """
        # Check rate limit
        if not rate_limiter.can_fetch_news(settings.max_news_fetches_per_hour):
            logger.warning("Rate limit hit for news fetching. Skipping collection.")
            return []
        
        all_items: List[NewsItem] = []
        
        # Collect AI News from RSS
        logger.info("Collecting AI news from RSS feeds...")
        ai_news = self.rss_collector.collect()
        all_items.extend(ai_news)
        
        # Collect from Reddit AI subreddits & X/Twitter
        logger.info("Collecting from Reddit AI communities and X/Twitter...")
        social_items = self.social_collector.collect_all()
        all_items.extend(social_items)
        
        # Collect Trending (Google Trends + Reddit r/all)
        logger.info("Collecting trending topics...")
        trending = self.trends_collector.collect()
        all_items.extend(trending)
        
        # Record the fetch
        rate_limiter.record_news_fetch()
        
        # Filter duplicates from history
        fresh_items = [item for item in all_items if not self._is_duplicate(item.title)]
        logger.info(f"After deduplication: {len(fresh_items)} items (from {len(all_items)})")
        
        # Score all items
        for item in fresh_items:
            item.score = self._score_item(item)
        
        # Sort by score
        fresh_items.sort(key=lambda x: x.score, reverse=True)
        
        # Take top 8 (5 AI + 3 Trending target, but take best overall)
        top_items = fresh_items[:8]
        
        # Save to history
        self._save_history(top_items)
        
        logger.info(f"Final curated list: {len(top_items)} items")
        return top_items
    
    def get_formatted_digest(self) -> str:
        """
        Get a human-readable digest of collected news.
        
        Returns:
            Formatted string for display/logging
        """
        items = self.collect_all()
        
        if not items:
            return "📭 No fresh news found today."
        
        lines = [
            "📰 **AI NEWS DIGEST**",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "-" * 40,
        ]
        
        for idx, item in enumerate(items, 1):
            emoji = "🤖" if item.category == "ai_news" else "🔥"
            lines.append(f"{idx}. {emoji} **{item.title}**")
            lines.append(f"   Source: {item.source} | Score: {item.score:.0f}")
        
        return "\n".join(lines)
