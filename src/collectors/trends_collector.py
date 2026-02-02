"""
Google Trends Collector
=======================
Fetches trending topics with fallback to Reddit r/all if pytrends fails.
"""

from datetime import datetime
from typing import List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
import requests

from .rss_collector import NewsItem
from ..utils.logger import logger


class TrendsCollector:
    """
    Collects trending topics from Google Trends (via pytrends) with Reddit fallback.
    
    Why fallback: pytrends is unofficial and breaks frequently.
    Reddit r/all provides a reliable backup for viral content.
    """
    
    def __init__(self, geo: str = "IN", max_items: int = 5):
        """
        Initialize trends collector.
        
        Args:
            geo: Geographic region code (e.g., 'IN' for India, 'US' for USA)
            max_items: Maximum trending items to return
        """
        self.geo = geo
        self.max_items = max_items
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=5),
    )
    def _fetch_google_trends(self) -> List[NewsItem]:
        """
        Fetch trending searches from Google Trends.
        
        Returns:
            List of trending NewsItem objects
        """
        items = []
        
        try:
            from pytrends.request import TrendReq
            
            pytrends = TrendReq(hl='en-US', tz=330)  # IST timezone offset
            
            # Get real-time trending searches
            trending_df = pytrends.trending_searches(pn='india')
            
            for idx, row in trending_df.head(self.max_items).iterrows():
                topic = row[0] if isinstance(row, (list, tuple)) else str(row.values[0])
                
                item = NewsItem(
                    id=f"trend_{idx}_{datetime.now().strftime('%Y%m%d')}",
                    title=topic,
                    source="Google Trends",
                    link=f"https://trends.google.com/trends/explore?q={topic.replace(' ', '%20')}&geo={self.geo}",
                    summary=f"Trending search in {self.geo}: {topic}",
                    published=datetime.now(),
                    category="trending"
                )
                items.append(item)
            
            logger.info(f"Fetched {len(items)} items from Google Trends")
            
        except ImportError:
            logger.warning("pytrends not installed, skipping Google Trends")
        except Exception as e:
            logger.warning(f"Google Trends failed: {e}. Will use fallback.")
        
        return items
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=5),
    )
    def _fetch_reddit_trending(self) -> List[NewsItem]:
        """
        Fetch viral posts from Reddit r/all as fallback.
        
        Returns:
            List of trending NewsItem objects
        """
        items = []
        
        try:
            headers = {
                'User-Agent': 'AINewsBot/1.0 (Educational Project)'
            }
            
            response = requests.get(
                "https://www.reddit.com/r/all/hot.json",
                headers=headers,
                params={"limit": 15},
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            for idx, post in enumerate(data.get("data", {}).get("children", [])):
                post_data = post.get("data", {})
                
                # Filter: Only high-engagement posts
                score = post_data.get("score", 0)
                if score < 5000:  # Minimum 5k upvotes
                    continue
                
                title = post_data.get("title", "")
                subreddit = post_data.get("subreddit", "unknown")
                permalink = post_data.get("permalink", "")
                
                item = NewsItem(
                    id=f"reddit_{post_data.get('id', idx)}",
                    title=title,
                    source=f"r/{subreddit}",
                    link=f"https://reddit.com{permalink}",
                    summary=f"Viral on Reddit with {score:,} upvotes",
                    published=datetime.now(),
                    score=score,
                    category="trending"
                )
                items.append(item)
                
                if len(items) >= self.max_items:
                    break
            
            logger.info(f"Fetched {len(items)} viral posts from Reddit")
            
        except Exception as e:
            logger.error(f"Reddit trending fetch failed: {e}")
        
        return items
    
    def collect(self) -> List[NewsItem]:
        """
        Collect trending topics with automatic fallback.
        
        Strategy:
        1. Try Google Trends first
        2. If fails or returns < 2 items, use Reddit fallback
        3. Combine and deduplicate
        
        Returns:
            List of trending NewsItem objects
        """
        all_items = []
        
        # Try Google Trends
        google_items = self._fetch_google_trends()
        all_items.extend(google_items)
        
        # Use Reddit fallback if Google Trends didn't work well
        if len(google_items) < 2:
            logger.info("Google Trends underperformed, using Reddit fallback")
            reddit_items = self._fetch_reddit_trending()
            all_items.extend(reddit_items)
        
        # Sort by score (popularity)
        all_items.sort(key=lambda x: x.score, reverse=True)
        
        # Return top items
        result = all_items[:self.max_items]
        logger.info(f"Total trending items: {len(result)}")
        
        return result
