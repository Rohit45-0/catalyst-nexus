"""
AUTOMATED GNN DATA COLLECTION WORKFLOW
======================================

This implements the EXACT workflow from your images:

1. Post published to Instagram
2. Every 30min: Fetch Instagram insights (impressions per city)
3. Create graph nodes for each city
4. Detect spread edges (City A → City B)
5. Store snapshots for GNN training
6. Export dataset periodically

This collects REAL viewing data from Instagram API, not clicks!
"""

import sys
import os
from datetime import datetime, timedelta
import requests
import time
import json
from typing import List, Dict, Optional

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.app.db.base import SessionLocal
from backend.app.db.models import Campaign
from backend.app.db.gnn_models import GraphNode, GraphEdge, ViralSpreadSnapshot
from sqlalchemy import func

# Instagram credentials
ACCESS_TOKEN = 'EAAZA6ygrlE3EBQhwbXFqOZCI0zWsbGQHJGXu3IDjqYztPg1oltdA8WkKlfgZBOHccHEiCOHn4u958ikopKsnA1gk8GNZADiBT7NSImZB99vF9gSZBT9gtvTRsyUiuHK6lSKmKgPXKaQpY1ZCXDgIdvKkMp4K3ODgfjo6cx22jXQvyrGd0atsWm5N8mCH4ruWgZDZD'
ACCOUNT_ID = '17841478698032119'


class GNNDataCollector:
    """
    Automated collector for GNN training data.
    
    Fetches Instagram viewing data and builds graph iteratively.
    """
    
    def __init__(self):
        self.access_token = ACCESS_TOKEN
        self.account_id = ACCOUNT_ID
    
    def fetch_post_audience_cities(self, post_id: str) -> List[Dict]:
        """
        Fetch city-level audience data from Instagram.
        
        Returns list of cities where post was VIEWED.
        """
        
        # Get post insights with city breakdown
        url = f"https://graph.facebook.com/v18.0/{post_id}/insights"
        
        params = {
            'access_token': self.access_token,
            'metric': 'impressions,reach,engagement',
            'breakdown': 'city'
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            print(f"⚠️  Could not fetch city data: {response.text}")
            return []
        
        data = response.json()
        
        # Parse city metrics
        city_metrics = {}
        
        if 'data' in data:
            for metric in data['data']:
                metric_name = metric.get('name')
                values = metric.get('values', [])
                
                for val_item in values:
                    if 'breakdown' in val_item and 'city' in val_item['breakdown']:
                        cities = val_item['breakdown']['city']
                        
                        for city_name, city_value in cities.items():
                            if city_name not in city_metrics:
                                city_metrics[city_name] = {
                                    'city': city_name,
                                    'country': 'Unknown',  # Can enhance
                                    'impressions': 0,
                                    'reach': 0,
                                    'engagement': 0
                                }
                            
                            city_metrics[city_name][metric_name] = city_value
        
        return list(city_metrics.values())
    
    def update_graph_nodes(self, campaign_id: str, city_data: List[Dict]) -> List[GraphNode]:
        """
        Create or update graph nodes for each city.
        
        Returns list of created/updated nodes.
        """
        
        db = SessionLocal()
        nodes = []
        
        try:
            for city_info in city_data:
                city = city_info['city']
                
                # Check if node exists
                node = db.query(GraphNode).filter(
                    GraphNode.campaign_id == campaign_id,
                    GraphNode.city == city
                ).first()
                
                if not node:
                    # Create new node
                    node = GraphNode(
                        campaign_id=campaign_id,
                        city=city,
                        country=city_info.get('country', 'Unknown'),
                        impressions=city_info.get('impressions', 0),
                        reach=city_info.get('reach', 0),
                        engagement=city_info.get('engagement', 0)
                    )
                    db.add(node)
                    print(f"   🆕 New city activated: {city}")
                else:
                    # Update existing node
                    old_impressions = node.impressions
                    node.impressions = city_info.get('impressions', node.impressions)
                    node.reach = city_info.get('reach', node.reach)
                    node.engagement = city_info.get('engagement', node.engagement)
                    node.last_updated = datetime.utcnow()
                    
                    # Calculate growth rate
                    if old_impressions > 0:
                        node.growth_rate = (node.impressions - old_impressions) / old_impressions
                    
                    print(f"   🔄 Updated: {city} ({old_impressions} → {node.impressions} impressions)")
               
                # Calculate engagement rate
                if node.reach > 0:
                    node.engagement_rate = node.engagement / node.reach
                
                nodes.append(node)
            
            db.commit()
            
        finally:
            db.close()
        
        return nodes
    
    def detect_spread_edges(self, campaign_id: str):
        """
        Detect viral spread edges between cities.
        
        Creates edge when City B appears after City A in timeline.
        """
        
        db = SessionLocal()
        
        try:
            # Get all nodes ordered by first_seen
            nodes = db.query(GraphNode).filter(
                GraphNode.campaign_id == campaign_id
            ).order_by(GraphNode.first_seen).all()
            
            # Create edges between consecutive cities
            for i in range(len(nodes) - 1):
                from_node = nodes[i]
                to_node = nodes[i + 1]
                
                # Check if edge already exists
                existing_edge = db.query(GraphEdge).filter(
                    GraphEdge.campaign_id == campaign_id,
                    GraphEdge.from_city == from_node.city,
                    GraphEdge.to_city == to_node.city
                ).first()
                
                if not existing_edge:
                    # Calculate time delta (seconds)
                    time_delta = (to_node.first_seen - from_node.first_seen).total_seconds()
                    
                    # Calculate transfer rate
                    transfer_rate = 0.0
                    if from_node.impressions > 0:
                        transfer_rate = to_node.impressions / from_node.impressions
                    
                    # Create edge
                    edge = GraphEdge(
                        campaign_id=campaign_id,
                        from_city=from_node.city,
                        from_country=from_node.country,
                        to_city=to_node.city,
                        to_country=to_node.country,
                        time_delta=time_delta,
                        weight=min(transfer_rate, 1.0),
                        confidence=0.7,  # Can improve with ML
                        from_city_impressions=from_node.impressions,
                        to_city_impressions=to_node.impressions,
                        transfer_rate=transfer_rate
                    )
                    
                    db.add(edge)
                    print(f"   ➡️  Edge created: {from_node.city} → {to_node.city} ({time_delta/3600:.1f}h)")
            
            db.commit()
            
        finally:
            db.close()
    
    def create_snapshot(self, campaign_id: str):
        """
        Create a snapshot of current graph state.
        
        This is used for time-series GNN training.
        """
        
        db = SessionLocal()
        
        try:
            # Get campaign
            campaign = db.query(Campaign).filter(
                Campaign.campaign_id == campaign_id
            ).first()
            
            if not campaign or not campaign.publish_time:
                return
            
            # Calculate time since publish
            hours_since_publish = (datetime.utcnow() - campaign.publish_time).total_seconds() / 3600
            
            # Aggregate graph metrics
            nodes = db.query(GraphNode).filter(
                GraphNode.campaign_id == campaign_id
            ).all()
            
            edges = db.query(GraphEdge).filter(
                GraphEdge.campaign_id == campaign_id
            ).all()
            
            total_impressions = sum(n.impressions for n in nodes)
            total_reach = sum(n.reach for n in nodes)
            total_engagement = sum(n.engagement for n in nodes)
            
            # Find trending city (highest growth rate)
            trending = max(nodes, key=lambda n: n.growth_rate) if nodes else None
            
            # Calculate graph density
            n = len(nodes)
            m = len(edges)
            density = (2 * m) / (n * (n - 1)) if n > 1 else 0.0
            
            # Create snapshot
            snapshot = ViralSpreadSnapshot(
                campaign_id=campaign_id,
                snapshot_time=datetime.utcnow(),
                hours_since_publish=hours_since_publish,
                total_nodes=len(nodes),
                total_edges=len(edges),
                total_impressions=total_impressions,
                total_reach=total_reach,
                total_engagement=total_engagement,
                trending_city=trending.city if trending else None,
                graph_density=density,
                avg_node_degree=m / n if n > 0 else 0.0
            )
            
            db.add(snapshot)
            db.commit()
            
            print(f"\n   📸 Snapshot created:")
            print(f"      Time: {hours_since_publish:.1f}h since publish")
            print(f"      Nodes: {len(nodes)}, Edges: {len(edges)}")
            print(f"      Total impressions: {total_impressions}")
            
        finally:
            db.close()
    
    def run_collection_cycle(self, campaign_id: str, post_id: str):
        """
        Run one collection cycle:
        1. Fetch Instagram data
        2. Update nodes
        3. Detect edges
        4. Create snapshot
        """
        
        print(f"\n{'='*80}")
        print(f"🔄 Collection Cycle: {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*80}")
        
        # Fetch city data from Instagram
        print("\n1️⃣ Fetching Instagram city data...")
        city_data = self.fetch_post_audience_cities(post_id)
        
        if city_data:
            print(f"   ✅ Found {len(city_data)} cities with viewing data")
            
            # Update graph nodes
            print("\n2️⃣ Updating graph nodes...")
            self.update_graph_nodes(campaign_id, city_data)
            
            # Detect spread edges
            print("\n3️⃣ Detecting spread edges...")
            self.detect_spread_edges(campaign_id)
            
            # Create snapshot
            print("\n4️⃣ Creating snapshot...")
            self.create_snapshot(campaign_id)
            
            print(f"\n✅ Collection cycle complete")
        else:
            print(f"   ⚠️  No city data available yet (post may be too new)")
    
    def export_gnn_dataset(self, output_file: str = "gnn_dataset.json"):
        """
        Export complete dataset for GNN training.
        """
        
        db = SessionLocal()
        
        try:
            # Get all nodes
            nodes = db.query(GraphNode).all()
            
            # Get all edges
            edges = db.query(GraphEdge).all()
            
            # Get all snapshots
            snapshots = db.query(ViralSpreadSnapshot).all()
            
            dataset = {
                'nodes': [
                    {
                        'id': n.city,
                        'campaign_id': n.campaign_id,
                        'impressions': n.impressions,
                        'reach': n.reach,
                        'engagement': n.engagement,
                        'engagement_rate': n.engagement_rate,
                        'growth_rate': n.growth_rate,
                        'first_seen': n.first_seen.isoformat()
                    }
                    for n in nodes
                ],
                'edges': [
                    {
                        'from': e.from_city,
                        'to': e.to_city,
                        'time_delta': e.time_delta,
                        'weight': e.weight,
                        'confidence': e.confidence,
                        'transfer_rate': e.transfer_rate
                    }
                    for e in edges
                ],
                'snapshots': [
                    {
                        'campaign_id': s.campaign_id,
                        'hours_since_publish': s.hours_since_publish,
                        'nodes': s.total_nodes,
                        'edges': s.total_edges,
                        'impressions': s.total_impressions,
                        'reach': s.total_reach,
                        'trending_city': s.trending_city
                    }
                    for s in snapshots
                ]
            }
            
            with open(output_file, 'w') as f:
                json.dump(dataset, f, indent=2)
            
            print(f"\n📤 GNN Dataset Exported:")
            print(f"   File: {output_file}")
            print(f"   Nodes: {len(dataset['nodes'])}")
            print(f"   Edges: {len(dataset['edges'])}")
            print(f"   Snapshots: {len(dataset['snapshots'])}")
            
        finally:
            db.close()


# MAIN EXECUTION
if __name__ == "__main__":
    print("="*80)
    print("🧠 AUTOMATED GNN DATA COLLECTOR")
    print("="*80)
    
    collector = GNNDataCollector()
    
    # Get latest campaign
    db = SessionLocal()
    campaign = db.query(Campaign).filter(
        Campaign.post_id.isnot(None)
    ).order_by(Campaign.created_at.desc()).first()
    
    if not campaign:
        print("\n❌ No published campaigns found!")
        print("   Publish a post to Instagram first.")
        db.close()
        exit(1)
    
    print(f"\n📊 Monitoring campaign: {campaign.campaign_id}")
    print(f"   Post ID: {campaign.post_id}")
    
    db.close()
    
    # Run collection cycles
    cycle_count = 0
    max_cycles = 10  # Run 10 cycles (for demo)
    interval_minutes = 30
    
    print(f"\n⏰ Will run {max_cycles} collection cycles every {interval_minutes} minutes")
    print(f"   Press Ctrl+C to stop and export data\n")
    
    try:
        while cycle_count < max_cycles:
            cycle_count += 1
            
            # Run collection
            collector.run_collection_cycle(campaign.campaign_id, campaign.post_id)
            
            if cycle_count < max_cycles:
                print(f"\n⏸️  Waiting {interval_minutes} minutes until next cycle...")
                print(f"   (Cycle {cycle_count}/{max_cycles} complete)")
                time.sleep(interval_minutes * 60)  # Wait 30 minutes
    
    except KeyboardInterrupt:
        print(f"\n\n⏹️  Collection stopped by user")
    
    # Export final dataset
    print(f"\n{'='*80}")
    print(f"📤 EXPORTING FINAL GNN DATASET")
    print(f"{'='*80}")
    
    collector.export_gnn_dataset("gnn_training_dataset.json")
    
    print(f"\n✅ GNN DATA COLLECTION COMPLETE!")
    print(f"   Dataset ready for training: gnn_training_dataset.json")
    print(f"{'='*80}\n")
