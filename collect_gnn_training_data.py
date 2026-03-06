"""
GNN TRAINING DATA COLLECTOR
===========================

This system collects REAL Instagram viewing data (not clicks) to train your GNN.

Flow:
1. Post published to Instagram
2. Instagram Graph API provides city-level reach data
3. Store as graph nodes/edges
4. Build dataset for GNN training

Data Source: Instagram Graph API Insights (city-level audience data)
"""

import sys
import os
from datetime import datetime, timedelta
import requests
from typing import List, Dict
import json

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.app.db.base import SessionLocal
from backend.app.db.models import Campaign, InsightSnapshot
from backend.app.core.config import settings

# Instagram credentials
ACCESS_TOKEN = 'EAAZA6ygrlE3EBQhwbXFqOZCI0zWsbGQHJGXu3IDjqYztPg1oltdA8WkKlfgZBOHccHEiCOHn4u958ikopKsnA1gk8GNZADiBT7NSImZB99vF9gSZBT9gtvTRsyUiuHK6lSKmKgPXKaQpY1ZCXDgIdvKkMp4K3ODgfjo6cx22jXQvyrGd0atsWm5N8mCH4ruWgZDZD'
ACCOUNT_ID = '17841478698032119'


class InstagramInsightsCollector:
    """
    Collects Instagram viewing data for GNN training.
    
    This captures REAL view data from Instagram, not clicks!
    Instagram provides:
    - Impressions per city
    - Reach per city  
    - Engagement per city
    - Time series data
    """
    
    def __init__(self):
        self.access_token = ACCESS_TOKEN
        self.account_id = ACCOUNT_ID
        self.db = SessionLocal()
    
    def fetch_post_insights_by_city(self, post_id: str) -> List[Dict]:
        """
        Fetch Instagram insights with city-level breakdown.
        
        This is the REAL data source for your GNN!
        """
        
        print(f"\n📊 Fetching Instagram insights for post: {post_id}")
        
        # Get post insights
        insights_url = f"https://graph.facebook.com/v18.0/{post_id}/insights"
        
        params = {
            'access_token': self.access_token,
            'metric': 'impressions,reach,engagement',
            'breakdown': 'city'  # This gives us city-level data!
        }
        
        response = requests.get(insights_url, params=params)
        
        if response.status_code != 200:
            print(f"❌ Failed to fetch insights: {response.text}")
            return []
        
        data = response.json()
        
        city_data = []
        
        # Parse city-level metrics
        if 'data' in data:
            for metric in data['data']:
                metric_name = metric.get('name')
                values = metric.get('values', [])
                
                for value_item in values:
                    breakdown = value_item.get('breakdown', {})
                    
                    if 'city' in breakdown:
                        city_info = breakdown['city']
                        
                        city_data.append({
                            'city': city_info.get('name', 'Unknown'),
                            'metric': metric_name,
                            'value': value_item.get('value', 0),
                            'timestamp': datetime.now()
                        })
        
        return city_data
    
    def fetch_account_insights_by_city(self, days_back: int = 7) -> List[Dict]:
        """
        Fetch account-level insights with city breakdown.
        
        This gives aggregate view data across all posts.
        """
        
        print(f"\n📊 Fetching account insights for last {days_back} days...")
        
        since = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        until = datetime.now().strftime('%Y-%m-%d')
        
        insights_url = f"https://graph.facebook.com/v18.0/{self.account_id}/insights"
        
        params = {
            'access_token': self.access_token,
            'metric': 'impressions,reach,profile_views',
            'period': 'day',
            'since': since,
            'until': until,
            'breakdown': 'city'  # City-level breakdown
        }
        
        response = requests.get(insights_url, params=params)
        
        if response.status_code != 200:
            print(f"❌ Failed to fetch account insights: {response.text}")
            return []
        
        data = response.json()
        print(f"✅ Received data: {json.dumps(data, indent=2)}")
        
        return self._parse_city_insights(data)
    
    def _parse_city_insights(self, api_data: Dict) -> List[Dict]:
        """Parse Instagram API response into city-level records"""
        
        city_records = []
        
        if 'data' not in api_data:
            return city_records
        
        for metric in api_data['data']:
            metric_name = metric.get('name')
            values = metric.get('values', [])
            
            for value_item in values:
                # Check if we have city breakdown
                if 'breakdown' in value_item and 'city' in value_item['breakdown']:
                    cities = value_item['breakdown']['city']
                    
                    for city_name, city_value in cities.items():
                        city_records.append({
                            'city': city_name,
                            'metric': metric_name,
                            'value': city_value,
                            'timestamp': value_item.get('end_time', datetime.now())
                        })
        
        return city_records
    
    def store_insights_as_graph_nodes(self, campaign_id: str, city_data: List[Dict]):
        """
        Store city viewing data as graph nodes for GNN training.
        
        Each city becomes a node with:
        - impressions (how many times seen)
        - reach (unique accounts)
        - engagement rate
        - timestamp
        """
        
        print(f"\n💾 Storing {len(city_data)} city records for GNN training...")
        
        for record in city_data:
            snapshot = InsightSnapshot(
                campaign_id=campaign_id,
                city=record['city'],
                timestamp=record['timestamp'],
                reach=record['value'] if record['metric'] == 'reach' else 0,
                impressions=record['value'] if record['metric'] == 'impressions' else 0,
                engagement=record['value'] if record['metric'] == 'engagement' else 0
            )
            
            self.db.add(snapshot)
        
        self.db.commit()
        print(f"✅ Stored in database (insight_snapshots table)")
    
    def export_gnn_training_data(self, output_file: str = "gnn_training_data.json"):
        """
        Export data in format ready for GNN training.
        
        Format:
        {
          "nodes": [
            {"id": "Mumbai", "impressions": 5000, "reach": 3000},
            {"id": "Pune", "impressions": 2000, "reach": 1500}
          ],
          "edges": [
            {"from": "Pune", "to": "Mumbai", "weight": 0.8, "time_delta": 3600}
          ]
        }
        """
        
        print(f"\n📤 Exporting GNN training data...")
        
        # Get all insight snapshots
        snapshots = self.db.query(InsightSnapshot).order_by(InsightSnapshot.timestamp).all()
        
        # Build nodes (cities)
        nodes = {}
        
        for snap in snapshots:
            if snap.city not in nodes:
                nodes[snap.city] = {
                    'id': snap.city,
                    'impressions': 0,
                    'reach': 0,
                    'engagement': 0,
                    'first_seen': snap.timestamp
                }
            
            nodes[snap.city]['impressions'] += snap.impressions
            nodes[snap.city]['reach'] += snap.reach
            nodes[snap.city]['engagement'] += snap.engagement
        
        # Build edges (spread pattern)
        edges = []
        cities_by_time = sorted(nodes.items(), key=lambda x: x[1]['first_seen'])
        
        for i in range(len(cities_by_time) - 1):
            from_city = cities_by_time[i][0]
            to_city = cities_by_time[i + 1][0]
            
            time_delta = (cities_by_time[i + 1][1]['first_seen'] - 
                         cities_by_time[i][1]['first_seen']).total_seconds()
            
            edges.append({
                'from': from_city,
                'to': to_city,
                'time_delta': time_delta,
                'weight': 1.0  # Can calculate based on engagement
            })
        
        gnn_data = {
            'nodes': list(nodes.values()),
            'edges': edges,
            'metadata': {
                'total_nodes': len(nodes),
                'total_edges': len(edges),
                'export_time': datetime.now().isoformat()
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(gnn_data, f, indent=2, default=str)
        
        print(f"✅ Exported to {output_file}")
        print(f"   Nodes: {len(nodes)}")
        print(f"   Edges: {len(edges)}")
        
        return gnn_data
    
    def close(self):
        self.db.close()


# MAIN EXECUTION
if __name__ == "__main__":
    print("="*80)
    print("🧠 GNN TRAINING DATA COLLECTOR")
    print("="*80)
    
    collector = InstagramInsightsCollector()
    
    try:
        # Step 1: Fetch Instagram insights
        print("\n📥 STEP 1: Fetching Instagram viewing data (NOT clicks!)")
        print("="*80)
        
        city_data = collector.fetch_account_insights_by_city(days_back=30)
        
        if city_data:
            print(f"\n✅ Collected {len(city_data)} city viewing records")
            
            # Show sample
            print(f"\n📊 Sample data:")
            for record in city_data[:5]:
                print(f"   {record['city']:15} | {record['metric']:15} | {record['value']:10}")
            
            # Step 2: Store as graph nodes
            print("\n💾 STEP 2: Storing as graph nodes for GNN")
            print("="*80)
            
            # Get or create campaign
            db = SessionLocal()
            campaign = db.query(Campaign).first()
            
            if campaign:
                collector.store_insights_as_graph_nodes(campaign.campaign_id, city_data)
            
            db.close()
            
            # Step 3: Export for GNN training
            print("\n📤 STEP 3: Exporting GNN training dataset")
            print("="*80)
            
            gnn_data = collector.export_gnn_training_data()
            
            print(f"\n✅ READY FOR GNN TRAINING!")
            print(f"   Data file: gnn_training_data.json")
            print(f"   Nodes (cities): {len(gnn_data['nodes'])}")
            print(f"   Edges (connections): {len(gnn_data['edges'])}")
            
        else:
            print(f"\n⚠️  No city-level data available yet")
            print(f"   Instagram needs:")
            print(f"   - Posts to be at least 24-48 hours old")
            print(f"   - Sufficient reach to provide city breakdowns")
            print(f"   - More posts over time to build patterns")
        
    finally:
        collector.close()
    
    print(f"\n{'='*80}")
    print(f"Collection completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
