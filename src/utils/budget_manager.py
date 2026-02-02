import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

class BudgetManager:
    """
    Manages the $5/month budget for API usage.
    Tracks spending and prevents overruns.
    """
    
    BUDGET_FILE = Path(__file__).parent.parent.parent / "data" / "budget_tracking.json"
    MONTHLY_LIMIT = 5.0  # $5.00 USD
    
    def __init__(self):
        self.BUDGET_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.load_budget()
    
    def load_budget(self):
        """Load budget data from file."""
        if self.BUDGET_FILE.exists():
            try:
                with open(self.BUDGET_FILE, 'r') as f:
                    self.data = json.load(f)
            except json.JSONDecodeError:
                self.data = self._empty_budget()
        else:
            self.data = self._empty_budget()
            
    def _empty_budget(self) -> Dict:
        return {
            "current_month": datetime.now().strftime("%Y-%m"),
            "total_spend": 0.0,
            "daily_spend": 0.0,
            "last_reset": datetime.now().isoformat(),
            "runs_this_month": 0
        }
    
    def check_budget(self) -> bool:
        """Check if we have budget remaining for a run (approx $0.05)."""
        # Reset if new month
        current_month = datetime.now().strftime("%Y-%m")
        if self.data["current_month"] != current_month:
            self.data["current_month"] = current_month
            self.data["total_spend"] = 0.0
            self.data["runs_this_month"] = 0
            self.save_budget()
            
        # Check if we are over budget
        if self.data["total_spend"] >= self.MONTHLY_LIMIT:
            return False
            
        return True
        
    def record_spending(self, amount: float):
        """Record usage cost."""
        self.data["total_spend"] += amount
        self.data["runs_this_month"] += 1
        self.data["last_updated"] = datetime.now().isoformat()
        self.save_budget()
        
    def save_budget(self):
        """Save budget data to file."""
        with open(self.BUDGET_FILE, 'w') as f:
            json.dump(self.data, f, indent=2)

    def get_status(self) -> str:
        """Get formatted status string."""
        remaining = self.MONTHLY_LIMIT - self.data['total_spend']
        return f"Budget: ${self.data['total_spend']:.3f} / ${self.MONTHLY_LIMIT:.2f} (Remaining: ${remaining:.2f})"
