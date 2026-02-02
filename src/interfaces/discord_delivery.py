"""
Discord Webhook Delivery
========================
Simplest delivery option - NO ACCOUNT SETUP NEEDED beyond Discord.

Just create a webhook in any Discord channel and paste the URL.

Pros:
- Instant mobile notifications
- Free forever
- 5 minutes to set up
- Rich embeds with colors
"""

from datetime import datetime
from typing import List, Optional
import requests

from ..collectors.rss_collector import NewsItem
from ..utils.logger import logger


class DiscordDelivery:
    """
    Delivers news ideas via Discord webhook.
    
    Setup:
    1. Right-click any Discord channel → Edit Channel → Integrations → Webhooks
    2. Create webhook, copy URL
    3. Paste URL in .env as DISCORD_WEBHOOK_URL
    """
    
    def __init__(self, webhook_url: str):
        """
        Initialize Discord delivery.
        
        Args:
            webhook_url: Discord webhook URL
        """
        self.webhook_url = webhook_url
    
    def _send_message(self, content: str = None, embeds: List[dict] = None) -> bool:
        """Send message to Discord webhook."""
        data = {}
        if content:
            data["content"] = content
        if embeds:
            data["embeds"] = embeds
        
        try:
            response = requests.post(
                self.webhook_url,
                json=data,
                timeout=10
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Discord webhook failed: {e}")
            return False
    
    def deliver_daily_ideas(self, items: List[NewsItem]) -> bool:
        """
        Deliver all daily news items as Discord embeds.
        
        Args:
            items: List of NewsItem objects
            
        Returns:
            True if successful
        """
        # Header message
        header = f"# 📰 AI News Ideas - {datetime.now().strftime('%B %d, %Y')}\n"
        header += f"*{len(items)} fresh ideas for today*\n\n"
        
        # Create embeds for each item
        embeds = []
        
        for idx, item in enumerate(items[:10], 1):  # Discord limit: 10 embeds
            # Color based on category
            color = 0x00ff00 if item.category == "ai_news" else 0xff6600
            
            embed = {
                "title": f"{idx}. {item.title[:100]}",
                "description": item.summary[:200] if item.summary else "No summary",
                "color": color,
                "fields": [
                    {"name": "Source", "value": item.source, "inline": True},
                    {"name": "Score", "value": f"{item.score:.0f}/100", "inline": True},
                    {"name": "Type", "value": "🤖 AI" if item.category == "ai_news" else "🔥 Trending", "inline": True}
                ],
                "url": item.link,
                "footer": {"text": f"ID: {item.id}"},
                "timestamp": datetime.now().isoformat()
            }
            embeds.append(embed)
        
        # Send in batches (Discord limit: 10 embeds per message)
        self._send_message(content=header)
        
        # Send embeds in chunks of 10
        for i in range(0, len(embeds), 10):
            chunk = embeds[i:i+10]
            if not self._send_message(embeds=chunk):
                return False
        
        logger.info(f"Delivered {len(items)} items to Discord")
        return True
    
    def send_research_report(self, topic: str, research: str) -> bool:
        """
        Send a research report for a specific topic.
        
        Args:
            topic: The topic name
            research: Formatted research text
            
        Returns:
            True if successful
        """
        embed = {
            "title": f"🔬 Research: {topic[:100]}",
            "description": research[:2000],
            "color": 0x9b59b6,  # Purple
            "timestamp": datetime.now().isoformat()
        }
        
        return self._send_message(embeds=[embed])
