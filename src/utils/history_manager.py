import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict

class HistoryManager:
    """
    Tracks previously discovered ideas to prevent duplicates.
    Used to populate the {PREVIOUS_IDEAS_LIST} in prompts.
    """
    
    HISTORY_FILE = Path(__file__).parent.parent.parent / "data" / "ideas_history.json"
    MAX_HISTORY = 50  # Keep last 50 titles for context
    
    def __init__(self):
        self.HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.history = self._load_history()
        
    def _load_history(self) -> List[str]:
        if self.HISTORY_FILE.exists():
            try:
                with open(self.HISTORY_FILE, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def get_recent_titles(self) -> str:
        """Get flattened list of recent idea titles for the prompt."""
        if not self.history:
            return "None"
        return ", ".join(self.history[-20:])  # Return last 20 for prompt context
    
    def add_ideas(self, ideas: List[Dict]):
        """Add new ideas to history."""
        new_titles = [idea.get("title", "") for idea in ideas if idea.get("title")]
        self.history.extend(new_titles)
        
        # Keep manageable size
        if len(self.history) > self.MAX_HISTORY:
            self.history = self.history[-self.MAX_HISTORY:]
            
        self._save_history()
        
    def _save_history(self):
        with open(self.HISTORY_FILE, 'w') as f:
            json.dump(self.history, f, indent=2)
