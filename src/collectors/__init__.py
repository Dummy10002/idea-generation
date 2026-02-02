# Collectors package
from .rss_collector import RSSCollector, NewsItem
from .trends_collector import TrendsCollector
from .social_media_collector import SocialMediaCollector
from .news_aggregator import NewsAggregator

__all__ = ["RSSCollector", "NewsItem", "TrendsCollector", "SocialMediaCollector", "NewsAggregator"]
