"""
RSS Feed Collector
==================
Fetches and parses AI news from RSS feeds with error handling and retries.
"""

import hashlib
from datetime import datetime, timedelta
from typing import List, Optional
from dataclasses import dataclass, field
import feedparser
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests.exceptions

from ..utils.logger import logger


@dataclass
class NewsItem:
    """Represents a single news item."""
    id: str
    title: str
    source: str
    link: str
    summary: str
    published: Optional[datetime] = None
    score: float = 0.0
    category: str = "ai_news"  # 'ai_news' or 'trending'
    content_blocks: Optional[List[dict]] = None # Raw Notion blocks
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "link": self.link,
            "summary": self.summary[:200] + "..." if len(self.summary) > 200 else self.summary,
            "published": self.published.isoformat() if self.published else None,
            "score": self.score,
            "category": self.category,
        }


class RSSCollector:
    """
    Collects news from RSS feeds with robust error handling.
    
    Features:
    - Retry logic with exponential backoff
    - Deduplication
    - Freshness filtering (last 24 hours only)
    - Rate limiting friendly (respects feed servers)
    """
    
    def __init__(self, feeds: List[str], max_age_hours: int = 24):
        """
        Initialize RSS collector.
        
        Args:
            feeds: List of RSS feed URLs
            max_age_hours: Maximum age of news items to include
        """
        self.feeds = feeds
        self.max_age = timedelta(hours=max_age_hours)
        self.seen_ids: set = set()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.exceptions.RequestException, Exception)),
        before_sleep=lambda retry_state: logger.warning(
            f"RSS fetch failed, retrying in {retry_state.next_action.sleep} seconds..."
        )
    )
    def _fetch_feed(self, feed_url: str) -> feedparser.FeedParserDict:
        """
        Fetch a single RSS feed with retries.
        
        Args:
            feed_url: URL of the RSS feed
            
        Returns:
            Parsed feed data
        """
        logger.debug(f"Fetching feed: {feed_url}")
        feed = feedparser.parse(feed_url)
        
        if feed.bozo and feed.bozo_exception:
            # Feed had parsing issues but may still have data
            logger.warning(f"Feed parse warning for {feed_url}: {feed.bozo_exception}")
        
        return feed
    
    def _generate_id(self, title: str, link: str) -> str:
        """Generate unique ID for deduplication."""
        content = f"{title}{link}".lower()
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _parse_date(self, entry: dict) -> Optional[datetime]:
        """
        Parse publication date from feed entry.
        
        Args:
            entry: Feed entry dictionary
            
        Returns:
            Parsed datetime or None
        """
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            try:
                return datetime(*entry.published_parsed[:6])
            except (ValueError, TypeError):
                pass
        if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            try:
                return datetime(*entry.updated_parsed[:6])
            except (ValueError, TypeError):
                pass
        return None
    
    def _extract_source(self, feed_url: str, feed: feedparser.FeedParserDict) -> str:
        """Extract source name from feed."""
        if hasattr(feed.feed, 'title') and feed.feed.title:
            return feed.feed.title[:30]  # Limit length
        
        # Fallback to domain extraction
        from urllib.parse import urlparse
        domain = urlparse(feed_url).netloc
        return domain.replace("www.", "").split(".")[0].title()
    
    def _is_fresh(self, published: Optional[datetime]) -> bool:
        """Check if news item is within freshness window."""
        if not published:
            return True  # Include if no date (can't verify)
        
        cutoff = datetime.now() - self.max_age
        return published > cutoff
    
    def collect(self) -> List[NewsItem]:
        """
        Collect news from all configured feeds.
        
        Returns:
            List of NewsItem objects, sorted by recency
        """
        all_items: List[NewsItem] = []
        
        for feed_url in self.feeds:
            try:
                feed = self._fetch_feed(feed_url)
                source = self._extract_source(feed_url, feed)
                
                for entry in feed.entries[:15]:  # Limit per feed
                    title = getattr(entry, 'title', 'No Title')
                    link = getattr(entry, 'link', '')
                    summary = getattr(entry, 'summary', '')
                    
                    # Skip if no title or link
                    if not title or not link:
                        continue
                    
                    # Generate unique ID
                    item_id = self._generate_id(title, link)
                    
                    # Skip duplicates
                    if item_id in self.seen_ids:
                        continue
                    self.seen_ids.add(item_id)
                    
                    # Parse date
                    published = self._parse_date(entry)
                    
                    # Skip stale items
                    if not self._is_fresh(published):
                        continue
                    
                    # Create NewsItem
                    item = NewsItem(
                        id=item_id,
                        title=title.strip(),
                        source=source,
                        link=link,
                        summary=summary.strip() if summary else "",
                        published=published,
                        category="ai_news"
                    )
                    all_items.append(item)
                    
                logger.info(f"Collected {len(feed.entries[:15])} items from {source}")
                
            except Exception as e:
                logger.error(f"Failed to fetch feed {feed_url}: {e}")
                continue  # Don't let one bad feed kill the whole run
        
        # Sort by recency (newest first)
        all_items.sort(
            key=lambda x: x.published if x.published else datetime.min,
            reverse=True
        )
        
        logger.info(f"Total fresh AI news items collected: {len(all_items)}")
        return all_items
