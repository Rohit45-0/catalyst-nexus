"""
Spread Graph
============

Analyzes spread patterns and generates graph data.
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.app.db.models import ClickEvent, InsightSnapshot
from backend.app.services.tracking.analytics.spike_detector import SpikeDetector


class SpreadGraph:
    """Analyzes geo spread of engagement."""
    
    def __init__(self, db: Session):
        self.db = db
        self.spike_detector = SpikeDetector(db)
    
    def analyze_spread(self, campaign_id: str) -> Dict:
        """Analyze spread and return graph data."""
        # Get click events
        clicks = self.db.query(ClickEvent).filter(
            ClickEvent.campaign_id == campaign_id
        ).order_by(ClickEvent.timestamp).all()
        
        # Group by city and time
        city_timeline = {}
        for click in clicks:
            city = click.city
            time = click.timestamp.replace(minute=0, second=0, microsecond=0)  # Hourly buckets
            
            if city not in city_timeline:
                city_timeline[city] = []
            city_timeline[city].append(time)
        
        # Find active nodes (cities with spikes)
        active_nodes = self.spike_detector.detect_spikes(campaign_id)
        
        # Infer edges based on time order
        edges = []
        sorted_cities = sorted(city_timeline.keys(), 
                              key=lambda c: min(city_timeline[c]) if city_timeline[c] else datetime.max)
        
        for i in range(len(sorted_cities) - 1):
            from_city = sorted_cities[i]
            to_city = sorted_cities[i + 1]
            if from_city in active_nodes and to_city in active_nodes:
                edges.append({"from": from_city, "to": to_city, "confidence": 0.8})
        
        # Find trending (most recent spike)
        trending = active_nodes[-1] if active_nodes else None
        
        # Find emerging (rapid growth)
        emerging = None
        if len(active_nodes) > 1:
            emerging = active_nodes[-2]  # Second most recent
        
        return {
            "campaign": campaign_id,
            "nodes": list(city_timeline.keys()),
            "edges": edges,
            "trending": trending,
            "emerging": emerging
        }
