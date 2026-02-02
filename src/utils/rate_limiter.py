"""
Rate Limiter
============
Prevents API abuse and runaway costs. Uses file-based tracking for persistence across runs.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from .logger import logger


class RateLimiter:
    """
    File-based rate limiter for tracking daily/hourly usage.
    Persists across GitHub Actions runs.
    """
    
    USAGE_FILE = Path(__file__).parent.parent.parent / "data" / "usage_tracking.json"
    
    def __init__(self):
        self.USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._load_usage()
    
    def _load_usage(self) -> None:
        """Load usage data from file."""
        if self.USAGE_FILE.exists():
            try:
                with open(self.USAGE_FILE, 'r') as f:
                    self.usage = json.load(f)
            except (json.JSONDecodeError, IOError):
                logger.warning("Corrupted usage file, resetting...")
                self.usage = self._empty_usage()
        else:
            self.usage = self._empty_usage()
    
    def _save_usage(self) -> None:
        """Persist usage data to file."""
        with open(self.USAGE_FILE, 'w') as f:
            json.dump(self.usage, f, indent=2)
    
    @staticmethod
    def _empty_usage() -> dict:
        """Return empty usage structure."""
        return {
            "scripts_today": 0,
            "scripts_date": datetime.now().strftime("%Y-%m-%d"),
            "news_fetches_this_hour": 0,
            "news_fetch_hour": datetime.now().strftime("%Y-%m-%d %H"),
            "last_updated": datetime.now().isoformat(),
        }
    
    def _reset_if_needed(self) -> None:
        """Reset counters if day/hour has changed."""
        today = datetime.now().strftime("%Y-%m-%d")
        current_hour = datetime.now().strftime("%Y-%m-%d %H")
        
        # Reset daily counter
        if self.usage.get("scripts_date") != today:
            logger.info(f"New day detected ({today}), resetting daily script counter")
            self.usage["scripts_today"] = 0
            self.usage["scripts_date"] = today
        
        # Reset hourly counter
        if self.usage.get("news_fetch_hour") != current_hour:
            logger.debug(f"New hour detected ({current_hour}), resetting hourly news counter")
            self.usage["news_fetches_this_hour"] = 0
            self.usage["news_fetch_hour"] = current_hour
        
        self.usage["last_updated"] = datetime.now().isoformat()
        self._save_usage()
    
    def can_generate_script(self, max_per_day: int) -> bool:
        """
        Check if script generation is allowed.
        
        Args:
            max_per_day: Maximum scripts allowed per day
        
        Returns:
            True if generation is allowed, False otherwise
        """
        self._reset_if_needed()
        
        if self.usage["scripts_today"] >= max_per_day:
            logger.warning(f"Daily script limit reached ({max_per_day}). Blocking generation.")
            return False
        return True
    
    def record_script_generation(self) -> None:
        """Record that a script was generated."""
        self._reset_if_needed()
        self.usage["scripts_today"] += 1
        self._save_usage()
        logger.info(f"Script generated. Daily count: {self.usage['scripts_today']}")
    
    def can_fetch_news(self, max_per_hour: int) -> bool:
        """
        Check if news fetching is allowed.
        
        Args:
            max_per_hour: Maximum fetches allowed per hour
        
        Returns:
            True if fetching is allowed, False otherwise
        """
        self._reset_if_needed()
        
        if self.usage["news_fetches_this_hour"] >= max_per_hour:
            logger.warning(f"Hourly news fetch limit reached ({max_per_hour}). Blocking fetch.")
            return False
        return True
    
    def record_news_fetch(self) -> None:
        """Record that news was fetched."""
        self._reset_if_needed()
        self.usage["news_fetches_this_hour"] += 1
        self._save_usage()
        logger.debug(f"News fetched. Hourly count: {self.usage['news_fetches_this_hour']}")
    
    def get_status(self) -> dict:
        """Get current usage status."""
        self._reset_if_needed()
        return {
            "scripts_today": self.usage["scripts_today"],
            "scripts_remaining": max(0, 5 - self.usage["scripts_today"]),  # Default max
            "news_fetches_this_hour": self.usage["news_fetches_this_hour"],
            "last_updated": self.usage["last_updated"],
        }


# Singleton instance
rate_limiter = RateLimiter()
