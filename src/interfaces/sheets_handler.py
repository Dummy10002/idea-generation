"""
Google Sheets Handler
=====================
Manages all interactions with Google Sheets (read/write news, approvals, scripts).
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
import gspread
from google.oauth2.service_account import Credentials

from ..collectors.rss_collector import NewsItem
from ..utils.config import settings
from ..utils.logger import logger


class SheetsHandler:
    """
    Handles Google Sheets operations with robust error handling.
    
    Features:
    - Connection pooling (reuses authenticated client)
    - Automatic tab creation
    - Structured data format
    - Approval detection
    - Script result storage
    """
    
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    def __init__(self):
        """Initialize Sheets handler with credentials."""
        self.client: Optional[gspread.Client] = None
        self.spreadsheet: Optional[gspread.Spreadsheet] = None
        self._connected = False
    
    def connect(self) -> bool:
        """
        Establish connection to Google Sheets.
        
        Returns:
            True if connection successful, False otherwise
        """
        if self._connected:
            return True
        
        try:
            # Check for credentials file
            creds_path = Path(settings.google_credentials_path)
            
            if not creds_path.exists():
                # Try to load from environment variable (for GitHub Actions)
                creds_json = self._get_creds_from_env()
                if creds_json:
                    creds = Credentials.from_service_account_info(
                        creds_json,
                        scopes=self.SCOPES
                    )
                else:
                    logger.error(f"Credentials file not found: {creds_path}")
                    return False
            else:
                creds = Credentials.from_service_account_file(
                    str(creds_path),
                    scopes=self.SCOPES
                )
            
            self.client = gspread.authorize(creds)
            self.spreadsheet = self.client.open_by_key(settings.google_sheet_id)
            
            self._connected = True
            logger.info(f"Connected to Google Sheet: {self.spreadsheet.title}")
            return True
            
        except gspread.exceptions.SpreadsheetNotFound:
            logger.error(f"Spreadsheet not found. Check GOOGLE_SHEET_ID: {settings.google_sheet_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Google Sheets: {e}")
            return False
    
    def _get_creds_from_env(self) -> Optional[dict]:
        """
        Get credentials from environment variable (for GitHub Actions).
        
        Returns:
            Parsed credentials JSON or None
        """
        import os
        creds_json_str = os.getenv("GDRIVE_CREDS")
        
        if creds_json_str:
            try:
                return json.loads(creds_json_str)
            except json.JSONDecodeError:
                logger.error("GDRIVE_CREDS environment variable contains invalid JSON")
        
        return None
    
    def _ensure_tab_exists(self, tab_name: str, headers: List[str]) -> gspread.Worksheet:
        """
        Ensure a worksheet tab exists, create if not.
        
        Args:
            tab_name: Name of the tab
            headers: Column headers for new tab
            
        Returns:
            Worksheet object
        """
        try:
            worksheet = self.spreadsheet.worksheet(tab_name)
        except gspread.exceptions.WorksheetNotFound:
            logger.info(f"Creating new tab: {tab_name}")
            worksheet = self.spreadsheet.add_worksheet(
                title=tab_name,
                rows=100,
                cols=len(headers)
            )
            worksheet.update('A1', [headers])
            worksheet.format('A1:Z1', {'textFormat': {'bold': True}})
        
        return worksheet
    
    def update_daily_news(self, items: List[NewsItem]) -> bool:
        """
        Update the Daily News tab with fresh items.
        
        Args:
            items: List of NewsItem objects to display
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connect():
            return False
        
        try:
            headers = ["ID", "Category", "Title", "Source", "Why It Matters", "Link", "Approve?", "Status"]
            worksheet = self._ensure_tab_exists(settings.daily_news_tab, headers)
            
            # Clear existing data (except header)
            worksheet.batch_clear(['A2:Z100'])
            
            # Prepare rows
            rows = []
            for idx, item in enumerate(items, 1):
                row = [
                    str(idx),
                    "🤖 AI" if item.category == "ai_news" else "🔥 Trending",
                    item.title,
                    item.source,
                    item.summary[:150] if item.summary else "No summary",
                    item.link,
                    "FALSE",  # Checkbox starts unchecked
                    "Pending"
                ]
                rows.append(row)
            
            # Write all rows at once
            if rows:
                worksheet.update(f'A2:H{len(rows) + 1}', rows)
            
            # Add timestamp
            timestamp_cell = f'J1'
            worksheet.update(timestamp_cell, f'Updated: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
            
            logger.info(f"Updated Daily News with {len(rows)} items")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update daily news: {e}")
            return False
    
    def check_for_approvals(self) -> List[Tuple[int, NewsItem]]:
        """
        Check for approved items in the Daily News tab.
        
        Returns:
            List of (row_index, NewsItem) tuples for approved items
        """
        if not self.connect():
            return []
        
        try:
            worksheet = self.spreadsheet.worksheet(settings.daily_news_tab)
            
            # Get all data
            all_values = worksheet.get_all_values()
            
            if len(all_values) <= 1:  # Only header or empty
                logger.info("No news items found in sheet")
                return []
            
            approved = []
            
            for idx, row in enumerate(all_values[1:], start=2):  # Skip header
                if len(row) < 8:
                    continue
                
                # Check if approved (column G) and not already processed (column H)
                approve_value = row[6].upper() if len(row) > 6 else ""
                status_value = row[7].lower() if len(row) > 7 else ""
                
                is_approved = approve_value == "TRUE"
                is_pending = status_value == "pending"
                
                if is_approved and is_pending:
                    item = NewsItem(
                        id=row[0],
                        category=row[1],
                        title=row[2],
                        source=row[3],
                        summary=row[4],
                        link=row[5],
                    )
                    approved.append((idx, item))
                    logger.info(f"Found approved item at row {idx}: {item.title[:50]}...")
            
            return approved
            
        except gspread.exceptions.WorksheetNotFound:
            logger.warning(f"Tab '{settings.daily_news_tab}' not found")
            return []
        except Exception as e:
            logger.error(f"Failed to check approvals: {e}")
            return []
    
    def mark_as_processing(self, row_index: int) -> bool:
        """
        Mark an approved item as 'Processing' to prevent duplicate processing.
        
        Args:
            row_index: Row index in the sheet
            
        Returns:
            True if successful
        """
        if not self.connect():
            return False
        
        try:
            worksheet = self.spreadsheet.worksheet(settings.daily_news_tab)
            worksheet.update_cell(row_index, 8, "Processing...")
            return True
        except Exception as e:
            logger.error(f"Failed to mark as processing: {e}")
            return False
    
    def mark_as_complete(self, row_index: int, script_row: int) -> bool:
        """
        Mark an item as complete with link to generated script.
        
        Args:
            row_index: Row index in Daily News tab
            script_row: Row index of the generated script
            
        Returns:
            True if successful
        """
        if not self.connect():
            return False
        
        try:
            worksheet = self.spreadsheet.worksheet(settings.daily_news_tab)
            worksheet.update_cell(row_index, 8, f"✅ Done (Row {script_row})")
            return True
        except Exception as e:
            logger.error(f"Failed to mark as complete: {e}")
            return False
    
    def write_generated_script(self, item: NewsItem, script: str) -> int:
        """
        Write a generated script to the Scripts tab.
        
        Args:
            item: The NewsItem that was approved
            script: The generated script text
            
        Returns:
            Row index where script was written, or -1 on failure
        """
        if not self.connect():
            return -1
        
        try:
            headers = ["Date", "Topic", "Source", "Script", "Character Count", "Word Count"]
            worksheet = self._ensure_tab_exists(settings.scripts_tab, headers)
            
            # Prepare row
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                item.title,
                item.source,
                script,
                str(len(script)),
                str(len(script.split()))
            ]
            
            # Append to sheet
            worksheet.append_row(row, value_input_option='RAW')
            
            # Get the row number
            all_values = worksheet.get_all_values()
            row_index = len(all_values)
            
            logger.info(f"Script written to row {row_index}")
            return row_index
            
        except Exception as e:
            logger.error(f"Failed to write script: {e}")
            return -1
    
    def log_usage(self, action: str, details: str) -> None:
        """
        Log an action to the Usage Log tab.
        
        Args:
            action: Type of action (e.g., "FETCH", "GENERATE", "ERROR")
            details: Additional details
        """
        if not self.connect():
            return
        
        try:
            headers = ["Timestamp", "Action", "Details"]
            worksheet = self._ensure_tab_exists(settings.usage_log_tab, headers)
            
            row = [
                datetime.now().isoformat(),
                action,
                details[:500]  # Limit detail length
            ]
            
            worksheet.append_row(row, value_input_option='RAW')
            
        except Exception as e:
            logger.warning(f"Failed to log usage (non-critical): {e}")
