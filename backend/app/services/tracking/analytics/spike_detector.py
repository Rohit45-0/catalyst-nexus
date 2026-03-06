"""
Spike Detector
==============

Detects engagement spikes in cities.
"""

from typing import List, Dict
from sqlalchemy.orm import Session
from backend.app.db.models import InsightSnapshot


class SpikeDetector:
    """Detects spikes in engagement data."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def detect_spikes(self, campaign_id: str, threshold: float = 1.5) -> List[str]:
        """Detect cities with engagement spikes."""
        # Get recent snapshots
        snapshots = self.db.query(InsightSnapshot).filter(
            InsightSnapshot.campaign_id == campaign_id
        ).order_by(InsightSnapshot.timestamp).all()
        
        spikes = []
        prev_reach = {}
        
        for snapshot in snapshots:
            city = snapshot.city or "global"
            current = snapshot.reach or 0
            
            if city in prev_reach:
                growth = current / prev_reach[city] if prev_reach[city] > 0 else 0
                if growth > threshold:
                    spikes.append(city)
            
            prev_reach[city] = current
        
        return list(set(spikes))  # Unique cities