"""
Social Media Collector
======================
Collects trending AI discussions from Reddit (niche-specific) and X/Twitter alternatives.

Note on X/Twitter:
- Official Twitter API is now paid ($100/month minimum)
- We use Nitter (free Twitter frontend) RSS feeds as fallback
- Nitter instances may be unreliable, so we have multiple fallbacks
"""

from datetime import datetime
from typing import List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
import requests

from .rss_collector import NewsItem
from ..utils.logger import logger


class SocialMediaCollector:
    """
    Collects AI-specific trending content from social platforms.
    
    Sources:
    - Reddit: AI-focused subreddits (hot posts with high engagement)
    - X/Twitter via Nitter: AI influencer accounts
    """
    
    # Nitter instances (Twitter frontend with RSS)
    # These are public instances - availability may vary
    NITTER_INSTANCES = [
        "nitter.privacydev.net",
        "nitter.poast.org",
        "nitter.1d4.us",
    ]
    
    # AI influencers/accounts to track on X
    AI_TWITTER_ACCOUNTS = [
        "sama",           # Sam Altman (OpenAI CEO)
        "ylecun",         # Yann LeCun (Meta AI)
        "kaboris",        # AI researcher
        "emaboris",       # AI artist
        "ClementDelwordd", # AI influencer
    ]
    
    # Reddit AI subreddits for trending discussions
    AI_SUBREDDITS = [
        "ChatGPT",
        "OpenAI",
        "artificial",
        "MachineLearning",
        "LocalLLaMA",
        "singularity",
    ]
    
    def __init__(self, max_items: int = 5):
        self.max_items = max_items
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
    )
    def _fetch_reddit_hot(self, subreddit: str) -> List[NewsItem]:
        """
        Fetch hot posts from a specific subreddit.
        
        Args:
            subreddit: Subreddit name (without r/)
            
        Returns:
            List of NewsItem objects
        """
        items = []
        
        try:
            headers = {
                'User-Agent': 'AINewsBot/1.0 (Educational Project)'
            }
            
            response = requests.get(
                f"https://www.reddit.com/r/{subreddit}/hot.json",
                headers=headers,
                params={"limit": 10},
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            for post in data.get("data", {}).get("children", []):
                post_data = post.get("data", {})
                
                # Filter: Only high-engagement posts (100+ upvotes)
                score = post_data.get("score", 0)
                if score < 100:
                    continue
                
                # Filter: Skip stickied/pinned posts
                if post_data.get("stickied", False):
                    continue
                
                title = post_data.get("title", "")
                permalink = post_data.get("permalink", "")
                selftext = post_data.get("selftext", "")[:200]
                
                # Calculate freshness (posts within 24h get priority)
                created_utc = post_data.get("created_utc", 0)
                created_time = datetime.fromtimestamp(created_utc) if created_utc else None
                
                if created_time:
                    hours_old = (datetime.now() - created_time).total_seconds() / 3600
                    if hours_old > 24:
                        continue  # Skip posts older than 24 hours
                
                item = NewsItem(
                    id=f"reddit_{post_data.get('id', '')}",
                    title=title,
                    source=f"r/{subreddit}",
                    link=f"https://reddit.com{permalink}",
                    summary=selftext or f"Hot discussion on r/{subreddit} with {score:,} upvotes",
                    published=created_time,
                    score=score,
                    category="ai_news"  # These are AI-specific
                )
                items.append(item)
            
        except Exception as e:
            logger.warning(f"Failed to fetch r/{subreddit}: {e}")
        
        return items
    
    def _fetch_twitter_via_nitter(self, account: str) -> List[NewsItem]:
        """
        Fetch tweets from X/Twitter via Nitter RSS.
        
        Args:
            account: Twitter username (without @)
            
        Returns:
            List of NewsItem objects
        """
        import feedparser
        
        items = []
        
        for nitter_instance in self.NITTER_INSTANCES:
            try:
                feed_url = f"https://{nitter_instance}/{account}/rss"
                feed = feedparser.parse(feed_url)
                
                if feed.bozo:
                    continue  # Try next instance
                
                for entry in feed.entries[:3]:  # Last 3 tweets
                    title = entry.get('title', '')[:100]
                    link = entry.get('link', '')
                    
                    # Parse date
                    published = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        try:
                            published = datetime(*entry.published_parsed[:6])
                        except:
                            pass
                    
                    # Skip if older than 24h
                    if published:
                        hours_old = (datetime.now() - published).total_seconds() / 3600
                        if hours_old > 24:
                            continue
                    
                    item = NewsItem(
                        id=f"x_{account}_{hash(title) % 10000}",
                        title=f"@{account}: {title}",
                        source="X (Twitter)",
                        link=link.replace(nitter_instance, "twitter.com"),  # Convert to real Twitter link
                        summary=title,
                        published=published,
                        category="trending"
                    )
                    items.append(item)
                
                if items:
                    logger.debug(f"Fetched {len(items)} tweets from @{account}")
                    break  # Success, don't try other instances
                    
            except Exception as e:
                logger.debug(f"Nitter instance {nitter_instance} failed: {e}")
                continue
        
        return items
    
    def collect_reddit_ai_trending(self) -> List[NewsItem]:
        """
        Collect trending AI discussions from Reddit.
        
        Returns:
            List of hot AI posts from multiple subreddits
        """
        all_items: List[NewsItem] = []
        
        for subreddit in self.AI_SUBREDDITS:
            items = self._fetch_reddit_hot(subreddit)
            all_items.extend(items)
            
            # Small delay to be respectful to Reddit
            import time
            time.sleep(0.5)
        
        # Sort by score (engagement)
        all_items.sort(key=lambda x: x.score, reverse=True)
        
        logger.info(f"Collected {len(all_items)} trending AI posts from Reddit")
        return all_items[:self.max_items]
    
    def collect_twitter_ai(self) -> List[NewsItem]:
        """
        Collect AI-related tweets from influencers.
        
        Note: This uses Nitter which may be unreliable.
        Falls back gracefully if all instances fail.
        
        Returns:
            List of recent AI tweets
        """
        all_items: List[NewsItem] = []
        
        for account in self.AI_TWITTER_ACCOUNTS[:3]:  # Limit to avoid rate issues
            items = self._fetch_twitter_via_nitter(account)
            all_items.extend(items)
        
        if all_items:
            logger.info(f"Collected {len(all_items)} tweets via Nitter")
        else:
            logger.warning("Could not fetch tweets (Nitter may be down). Skipping X/Twitter.")
        
        return all_items[:self.max_items]
    
    def collect_all(self) -> List[NewsItem]:
        """
        Collect from all social media sources.
        
        Returns:
            Combined list of social media news items
        """
        all_items: List[NewsItem] = []
        
        # Reddit is reliable, prioritize it
        reddit_items = self.collect_reddit_ai_trending()
        all_items.extend(reddit_items)
        
        # Twitter via Nitter is best-effort
        twitter_items = self.collect_twitter_ai()
        all_items.extend(twitter_items)
        
        # Sort by score
        all_items.sort(key=lambda x: x.score, reverse=True)
        
        return all_items[:self.max_items]
