"""
View GNN Training Data
======================

View all collected graph nodes, edges, and snapshots for GNN training.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.app.db.base import SessionLocal
from backend.app.db.models import Campaign
from backend.app.db.gnn_models import GraphNode, GraphEdge, ViralSpreadSnapshot
from datetime import datetime

print("="*80)
print("🧠 GNN TRAINING DATA VIEWER")
print("="*80)

db = SessionLocal()

try:
    # 1. GRAPH NODES (Cities)
    print("\n" + "="*80)
    print("1️⃣ GRAPH NODES (Cities with Viewing Data)")
    print("="*80)
    
    nodes = db.query(GraphNode).order_by(GraphNode.first_seen).all()
    
    if nodes:
        print(f"\nTotal Nodes: {len(nodes)}\n")
        
        for i, node in enumerate(nodes, 1):
            print(f"Node {i}: {node.city}, {node.country}")
            print(f"   Campaign: {node.campaign_id}")
            print(f"   Impressions: {node.impressions}")
            print(f"   Reach: {node.reach}")
            print(f"   Engagement: {node.engagement}")
            print(f"   Engagement Rate: {node.engagement_rate:.2%}")
            print(f"   Growth Rate: {node.growth_rate:.2%}")
            print(f"   First Seen: {node.first_seen}")
            print()
    else:
        print("\n⚠️  No nodes collected yet.")
        print("   Run: python run_gnn_data_collection.py")
    
    # 2. GRAPH EDGES (Spread Connections)
    print("\n" + "="*80)
    print("2️⃣ GRAPH EDGES (Viral Spread Paths)")
    print("="*80)
    
    edges = db.query(GraphEdge).order_by(GraphEdge.created_at).all()
    
    if edges:
        print(f"\nTotal Edges: {len(edges)}\n")
        
        for i, edge in enumerate(edges, 1):
            print(f"Edge {i}: {edge.from_city} → {edge.to_city}")
            print(f"   Time Delta: {edge.time_delta/3600:.1f} hours")
            print(f"   Weight: {edge.weight:.2f}")
            print(f"   Confidence: {edge.confidence:.2f}")
            print(f"   Transfer Rate: {edge.transfer_rate:.2f}x")
            print(f"   From Impressions: {edge.from_city_impressions}")
            print(f"   To Impressions: {edge.to_city_impressions}")
            print()
    else:
        print("\n⚠️  No edges detected yet.")
        print("   Need at least 2 cities to create edges.")
    
    # 3. VIRAL SPREAD SNAPSHOTS
    print("\n" + "="*80)
    print("3️⃣ VIRAL SPREAD SNAPSHOTS (Time Series)")
    print("="*80)
    
    snapshots = db.query(ViralSpreadSnapshot).order_by(
        ViralSpreadSnapshot.snapshot_time
    ).all()
    
    if snapshots:
        print(f"\nTotal Snapshots: {len(snapshots)}\n")
        
        for i, snap in enumerate(snapshots, 1):
            print(f"Snapshot {i}:")
            print(f"   Time: {snap.snapshot_time}")
            print(f"   Hours Since Publish: {snap.hours_since_publish:.1f}h")
            print(f"   Active Cities: {snap.total_nodes}")
            print(f"   Connections: {snap.total_edges}")
            print(f"   Total Impressions: {snap.total_impressions}")
            print(f"   Total Reach: {snap.total_reach}")
            print(f"   Total Engagement: {snap.total_engagement}")
            print(f"   Trending City: {snap.trending_city or 'N/A'}")
            print(f"   Graph Density: {snap.graph_density:.3f}")
            print(f"   Avg Node Degree: {snap.avg_node_degree:.2f}")
            print()
    else:
        print("\n⚠️  No snapshots created yet.")
        print("   Snapshots are created during collection cycles.")
    
  # 4. STATISTICS
    print("\n" + "="*80)
    print("4️⃣ GNN TRAINING DATASET STATISTICS")
    print("="*80)
    
    total_nodes = len(nodes)
    total_edges = len(edges)
    total_snapshots = len(snapshots)
    
    unique_campaigns = db.query(GraphNode.campaign_id).distinct().count()
    
    print(f"\n📊 Dataset Size:")
    print(f"   Graph Nodes: {total_nodes}")
    print(f"   Graph Edges: {total_edges}")
    print(f"   Time-series Snapshots: {total_snapshots}")
    print(f"   Unique Campaigns: {unique_campaigns}")
    
    if nodes:
        total_impressions = sum(n.impressions for n in nodes)
        total_reach = sum(n.reach for n in nodes)
        total_engagement = sum(n.engagement for n in nodes)
        
        avg_impressions = total_impressions / total_nodes if total_nodes > 0 else 0
        avg_engagement_rate = sum(n.engagement_rate for n in nodes if n.engagement_rate) / total_nodes if total_nodes > 0 else 0
        
        print(f"\n📈 Aggregate Metrics:")
        print(f"   Total Impressions: {total_impressions:,}")
        print(f"   Total Reach: {total_reach:,}")
        print(f"   Total Engagement: {total_engagement:,}")
        print(f"   Avg Impressions/Node: {avg_impressions:.0f}")
        print(f"   Avg Engagement Rate: {avg_engagement_rate:.2%}")
    
    if edges:
        avg_time_delta = sum(e.time_delta for e in edges) / total_edges
        avg_transfer_rate = sum(e.transfer_rate for e in edges) / total_edges
        
        print(f"\n🔗 Edge Metrics:")
        print(f"   Avg Time Delta: {avg_time_delta/3600:.1f} hours")
        print(f"   Avg Transfer Rate: {avg_transfer_rate:.2f}x")
    
    # 5. READINESS ASSESSMENT
    print("\n" + "="*80)
    print("5️⃣ GNN TRAINING READINESS")
    print("="*80)
    
    print(f"\n🎯 Minimum Requirements:")
    print(f"   ✅ Nodes: {total_nodes}/20 {'✓' if total_nodes >= 20 else '✗'}")
    print(f"   ✅ Edges: {total_edges}/15 {'✓' if total_edges >= 15 else '✗'}")
    print(f"   ✅ Snapshots: {total_snapshots}/10 {'✓' if total_snapshots >= 10 else '✗'}")
    print(f"   ✅ Campaigns: {unique_campaigns}/5 {'✓' if unique_campaigns >= 5 else '✗'}")
    
    readiness = (
        (total_nodes >= 20) and
        (total_edges >= 15) and
        (total_snapshots >= 10) and
        (unique_campaigns >= 5)
    )
    
    if readiness:
        print(f"\n🎉 READY FOR GNN TRAINING!")
        print(f"   Export dataset: python collect_gnn_training_data.py")
    else:
        print(f"\n⏳ Keep collecting data...")
        needed = []
        if total_nodes < 20:
            needed.append(f"{20 - total_nodes} more nodes")
        if total_edges < 15:
            needed.append(f"{15 - total_edges} more edges")
        if total_snapshots < 10:
            needed.append(f"{10 - total_snapshots} more snapshots")
        if unique_campaigns < 5:
            needed.append(f"{5 - unique_campaigns} more campaigns")
        
        print(f"   Need: {', '.join(needed)}")
        print(f"   Run: python run_gnn_data_collection.py")

finally:
    db.close()

print(f"\n{'='*80}")
print(f"View completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*80}\n")
