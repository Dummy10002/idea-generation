"""
Configuration Management
========================
Centralized settings with validation. Uses Pydantic for type safety.
ALL values come from .env - nothing hardcoded!
"""

import os
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class Settings(BaseModel):
    """Application settings with validation."""
    
    # --- Perplexity AI (Deep Research) ---
    perplexity_api_key: str = Field(
        default="",
        description="Perplexity API key for deep research"
    )
    max_research_per_day: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum Perplexity research queries per day"
    )
    max_deep_research: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of top ideas to deeply research"
    )
    
    # --- Notion Delivery ---
    notion_token: str = Field(
        default="",
        description="Notion integration token"
    )
    notion_database_id: str = Field(
        default="",
        description="Notion database ID"
    )
    
    # --- Discord Delivery (Alternative) ---
    discord_webhook_url: str = Field(
        default="",
        description="Discord webhook URL for delivery"
    )
    
    # --- Google Sheets (Alternative) ---
    google_credentials_path: str = Field(
        default="credentials.json",
        description="Path to Google Cloud service account JSON"
    )
    google_sheet_id: str = Field(
        default="",
        description="Google Sheet ID from URL"
    )
    
    # --- Delivery Method ---
    delivery_method: str = Field(
        default="notion",
        description="Delivery method: 'notion', 'discord', or 'sheets'"
    )
    
    # --- Rate Limits (Cost Control) ---
    max_news_fetches_per_hour: int = Field(
        default=2,
        ge=1,
        le=10,
        description="Maximum news fetch operations per hour"
    )
    max_ideas_per_day: int = Field(
        default=10,
        ge=1,
        le=20,
        description="Maximum ideas to collect per day"
    )
    news_max_age_hours: int = Field(
        default=24,
        ge=1,
        le=72,
        description="Only include news from the last X hours"
    )
    
    # --- Timezone ---
    timezone: str = Field(
        default="Asia/Kolkata",
        description="Timezone for scheduling"
    )
    
    # --- RSS Feeds (Can override in .env as JSON) ---
    ai_news_feeds: List[str] = Field(
        default=[
            # AI News Sites
            "https://news.ycombinator.com/rss",
            "https://simonwillison.net/atom/everything/",
            # Reddit AI Subreddits
            "https://www.reddit.com/r/MachineLearning/.rss",
            "https://www.reddit.com/r/artificial/.rss",
            "https://www.reddit.com/r/ChatGPT/.rss",
            "https://www.reddit.com/r/OpenAI/.rss",
            "https://www.reddit.com/r/LocalLLaMA/.rss",
            "https://www.reddit.com/r/StableDiffusion/.rss",
            # Tech News with AI Coverage
            "https://techcrunch.com/category/artificial-intelligence/feed/",
            "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        ],
        description="RSS feeds to monitor for AI news"
    )
    
    # --- Sheet Tab Names ---
    daily_news_tab: str = Field(default="Daily_News")
    scripts_tab: str = Field(default="Scripts_Generated")
    usage_log_tab: str = Field(default="Usage_Log")
    
    @field_validator('perplexity_api_key', 'notion_token')
    @classmethod
    def check_not_placeholder(cls, v: str, info) -> str:
        """Warn if placeholder values are still in use."""
        if v and ('xxxxx' in v or 'your_' in v or v.startswith('pplx-xxxxx')):
            raise ValueError(f"{info.field_name} appears to be a placeholder. Please set a real value.")
        return v
    
    @property
    def has_perplexity(self) -> bool:
        """Check if Perplexity is configured."""
        return bool(self.perplexity_api_key and len(self.perplexity_api_key) > 10)
    
    @property
    def has_notion(self) -> bool:
        """Check if Notion is configured."""
        return bool(self.notion_token and self.notion_database_id)
    
    @property
    def has_discord(self) -> bool:
        """Check if Discord is configured."""
        return bool(self.discord_webhook_url and 'discord.com' in self.discord_webhook_url)
    
    def validate_for_production(self) -> List[str]:
        """
        Returns a list of missing/invalid configuration items.
        Empty list means ready for production.
        """
        issues = []
        
        # Check required based on delivery method
        if self.delivery_method == "notion":
            if not self.notion_token:
                issues.append("NOTION_TOKEN is not set")
            if not self.notion_database_id:
                issues.append("NOTION_DATABASE_ID is not set")
        elif self.delivery_method == "discord":
            if not self.discord_webhook_url:
                issues.append("DISCORD_WEBHOOK_URL is not set")
        elif self.delivery_method == "sheets":
            if not self.google_sheet_id:
                issues.append("GOOGLE_SHEET_ID is not set")
            if not Path(self.google_credentials_path).exists():
                issues.append(f"Google credentials file not found: {self.google_credentials_path}")
        
        # Perplexity is optional but recommended
        if not self.has_perplexity:
            issues.append("PERPLEXITY_API_KEY not set (deep research will be disabled)")
        
        return issues
    
    def get_cost_estimate(self) -> dict:
        """Estimate monthly cost based on current settings."""
        # Perplexity: ~$0.003 per research (1000 tokens)
        perplexity_cost_per_research = 0.003
        daily_cost = self.max_deep_research * perplexity_cost_per_research
        monthly_cost = daily_cost * 30
        
        return {
            "per_research": f"${perplexity_cost_per_research:.4f}",
            "per_day": f"${daily_cost:.4f}",
            "per_month": f"${monthly_cost:.2f}",
            "researches_per_5_dollars": int(5 / perplexity_cost_per_research)
        }


def load_settings() -> Settings:
    """Load settings from environment variables."""
    return Settings(
        # Perplexity
        perplexity_api_key=os.getenv("PERPLEXITY_API_KEY", ""),
        max_research_per_day=int(os.getenv("MAX_RESEARCH_PER_DAY", "10")),
        max_deep_research=int(os.getenv("MAX_DEEP_RESEARCH", "3")),
        
        # Notion
        notion_token=os.getenv("NOTION_TOKEN", ""),
        notion_database_id=os.getenv("NOTION_DATABASE_ID", ""),
        
        # Discord
        discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL", ""),
        
        # Google Sheets
        google_credentials_path=os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json"),
        google_sheet_id=os.getenv("GOOGLE_SHEET_ID", ""),
        
        # General
        delivery_method=os.getenv("DELIVERY_METHOD", "notion"),
        max_news_fetches_per_hour=int(os.getenv("MAX_NEWS_FETCHES_PER_HOUR", "2")),
        max_ideas_per_day=int(os.getenv("MAX_IDEAS_PER_DAY", "10")),
        news_max_age_hours=int(os.getenv("NEWS_MAX_AGE_HOURS", "24")),
        timezone=os.getenv("TIMEZONE", "Asia/Kolkata"),
    )


# Singleton instance
settings = load_settings()
