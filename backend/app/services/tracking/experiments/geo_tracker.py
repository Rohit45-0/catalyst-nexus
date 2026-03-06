"""
Geo Tracker Experiment
======================

Test mode for geo tracking with mock data.
"""

from typing import Dict, List
from backend.app.db.schemas import SpreadAnalysisResponse


class GeoTrackerExperiment:
    """Test implementation with mock data."""
    
    @staticmethod
    def mock_click_data() -> List[Dict]:
        """Generate mock click events."""
        return [
            {"campaign_id": "ig_test_001", "city": "Pune", "timestamp": "2024-01-01T10:00:00"},
            {"campaign_id": "ig_test_001", "city": "Mumbai", "timestamp": "2024-01-01T10:40:00"},
            {"campaign_id": "ig_test_001", "city": "Dubai", "timestamp": "2024-01-01T11:20:00"},
        ]
    
    @staticmethod
    def analyze_mock_spread(campaign_id: str) -> SpreadAnalysisResponse:
        """Analyze mock spread data."""
        # Simulate spread analysis
        return SpreadAnalysisResponse(
            campaign=campaign_id,
            nodes=["Pune", "Mumbai", "Dubai"],
            edges=[
                {"from": "Pune", "to": "Mumbai"},
                {"from": "Mumbai", "to": "Dubai"}
            ],
            trending="Mumbai",
            emerging="Dubai"
        )
    
    @staticmethod
    def print_console_output(analysis: SpreadAnalysisResponse):
        """Print analysis to console."""
        print(f"Campaign: {analysis.campaign}")
        print("Spread:")
        for edge in analysis.edges:
            print(f"  {edge['from']} → {edge['to']}")
        print(f"Trending: {analysis.trending or 'None'}")
        print(f"Emerging: {analysis.emerging or 'None'}")