"""
Notion Delivery Handler
=======================
Alternative to Google Sheets - requires only a Notion account (NO GCP needed).

Notion offers:
- Free API access
- No credit card required
- Simple database interface
- Mobile app for easy access

Setup:
1. Create a Notion Integration at: https://www.notion.so/my-integrations
2. Create a database page and share it with your integration
3. Copy the database ID and integration token

IMPORTANT: Your Notion database only needs a "Title" column (default).
All other properties are auto-created or optional.
"""

import json
from datetime import datetime
from typing import List, Optional, Dict
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from ..collectors.rss_collector import NewsItem
from ..utils.logger import logger


class NotionDelivery:
    """
    Delivers news ideas to a Notion database.
    
    NO GCP ACCOUNT NEEDED - just a free Notion account.
    
    Features:
    - Create database entries (only requires Title column)
    - Rich page content
    - Research notes embedded in page
    """
    
    NOTION_API_VERSION = "2022-06-28"
    BASE_URL = "https://api.notion.com/v1"
    
    def __init__(self, token: str, database_id: str):
        """
        Initialize Notion delivery.
        
        Args:
            token: Notion integration token (starts with 'secret_' or 'ntn_')
            database_id: The ID of your Notion database
        """
        self.token = token
        self.database_id = database_id
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": self.NOTION_API_VERSION
        }
        self.db_properties = {}  # Cache of database properties
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """Make API request to Notion with detailed error logging."""
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            if method == "POST":
                response = requests.post(url, headers=self.headers, json=data, timeout=30)
            elif method == "PATCH":
                response = requests.patch(url, headers=self.headers, json=data, timeout=30)
            elif method == "GET":
                response = requests.get(url, headers=self.headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            if response.status_code >= 400:
                error_body = response.json() if response.text else {}
                error_msg = error_body.get("message", response.text[:200])
                logger.error(f"Notion API error {response.status_code}: {error_msg}")
                
                # Log helpful debugging info
                if response.status_code == 400:
                    logger.error("Hint: Check that your database has the required properties")
                elif response.status_code == 401:
                    logger.error("Hint: Check your NOTION_TOKEN is correct")
                elif response.status_code == 404:
                    logger.error("Hint: Check your NOTION_DATABASE_ID and ensure the database is shared with your integration")
                
                return None
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Notion request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in Notion request: {e}")
            return None
    
    def test_connection(self) -> bool:
        """Test if the Notion connection works and cache database schema."""
        result = self._make_request("GET", f"databases/{self.database_id}")
        if result:
            db_title = "Unnamed"
            title_arr = result.get("title", [])
            if title_arr:
                db_title = title_arr[0].get("plain_text", "Unnamed")
            
            logger.info(f"✅ Connected to Notion database: {db_title}")
            
            # Cache the database properties
            self.db_properties = result.get("properties", {})
            logger.info(f"   Database has {len(self.db_properties)} properties")
            
            return True
        return False
    
    def _build_simple_properties(self, item: NewsItem) -> Dict:
        """
        Build minimal properties that work with any Notion database.
        
        Only requires "Title" (or "Name") property which every database has.
        """
        # Find the title property (could be "Title", "Name", etc.)
        title_prop_name = "Title"  # Default
        
        for prop_name, prop_config in self.db_properties.items():
            if prop_config.get("type") == "title":
                title_prop_name = prop_name
                break
        
        # Build minimal properties - just the title
        properties = {
            title_prop_name: {
                "title": [{
                    "text": {"content": item.title[:90]}
                }]
            }
        }
        
        # Add optional properties if they exist in the database
        if "Source" in self.db_properties:
            properties["Source"] = {"select": {"name": item.source[:30]}}
        
        if "Link" in self.db_properties and item.link:
            properties["Link"] = {"url": item.link}
        
        if "Score" in self.db_properties:
            properties["Score"] = {"number": item.score}
        
        if "Status" in self.db_properties:
            prop_type = self.db_properties["Status"]["type"]
            if prop_type == "status":
                properties["Status"] = {"status": {"name": "New"}}
            elif prop_type == "select":
                properties["Status"] = {"select": {"name": "New"}}
        
        if "Category" in self.db_properties:
            category = "AI" if item.category == "ai_news" else "Trending"
            prop_type = self.db_properties["Category"]["type"]
            if prop_type == "select":
                properties["Category"] = {"select": {"name": category}}
            elif prop_type == "multi_select":
                properties["Category"] = {"multi_select": [{"name": category}]}
        
        return properties
    
    def _build_page_content(self, item: NewsItem, research: Optional[str] = None) -> List[Dict]:
        """
        Build the page body content.
        Style: Minimalist. Quote block for summary + View Link.
        """
        # Use raw blocks if provided (Exact Control Mode)
        if hasattr(item, 'content_blocks') and item.content_blocks:
            return item.content_blocks

        children = []
        
        # 1. Summary (Quote Block)
        # Split summary into chunks if needed (Notion limit 2000 chars)
        summary_text = item.summary[:1900] if item.summary else "No summary provided."
        children.append({
            "object": "block",
            "type": "quote",
            "quote": {
                "rich_text": [{"type": "text", "text": {"content": summary_text}}]
            }
        })

        # 2. Link (Paragraph with link)
        if item.link:
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"type": "text", "text": {"content": "🔗 "}},
                        {"type": "text", "text": {"content": "View Discussion", "link": {"url": item.link}}}
                    ]
                }
            })
        
        # 3. Research notes if provided
        if research:
            children.append({"object": "block", "type": "divider", "divider": {}})
            
            children.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": "🔬 Deep Research"}}]
                }
            })
            
            # Split research into chunks
            research_chunks = [research[i:i+1900] for i in range(0, len(research), 1900)]
            for chunk in research_chunks[:5]:  # Allow a few more blocks for research
                children.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": chunk}}]
                    }
                })
        
        return children
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
    )
    def add_news_item(self, item: NewsItem, research: Optional[str] = None) -> bool:
        """
        Add a news item to the Notion database.
        
        Args:
            item: NewsItem to add
            research: Optional research notes
            
        Returns:
            True if successful
        """
        properties = self._build_simple_properties(item)
        children = self._build_page_content(item, research)
        
        data = {
            "parent": {"database_id": self.database_id},
            "properties": properties,
            "children": children
        }
        
        result = self._make_request("POST", "pages", data)
        
        if result:
            logger.info(f"   ✅ Added: {item.title[:50]}...")
            return True
        
        logger.warning(f"   ❌ Failed: {item.title[:50]}...")
        return False
    
    def deliver_daily_ideas(self, items: List[NewsItem], research_reports: Optional[Dict] = None) -> int:
        """
        Deliver all daily news items to Notion.
        
        Args:
            items: List of NewsItem objects
            research_reports: Optional dict mapping item.id -> research string
            
        Returns:
            Number of items successfully added
        """
        logger.info(f"📤 Delivering {len(items)} items to Notion...")
        
        if not self.test_connection():
            logger.error("❌ Failed to connect to Notion database")
            logger.error("   Check: NOTION_TOKEN and NOTION_DATABASE_ID in .env")
            logger.error("   Ensure: Database is shared with your Notion integration")
            return 0
        
        success_count = 0
        research_reports = research_reports or {}
        
        for i, item in enumerate(items, 1):
            logger.info(f"   [{i}/{len(items)}] Processing: {item.title[:40]}...")
            
            research = research_reports.get(item.id)
            
            try:
                if self.add_news_item(item, research):
                    success_count += 1
            except Exception as e:
                logger.warning(f"   Error adding item: {e}")
                continue
        
        logger.info(f"✅ Delivered {success_count}/{len(items)} items to Notion")
        return success_count
