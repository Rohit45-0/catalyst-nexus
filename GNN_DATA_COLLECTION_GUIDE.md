# 🧠 GNN TRAINING DATA COLLECTION SYSTEM

## Overview

This system collects **REAL Instagram viewing data** to train your Graph Neural Network (GNN) for viral spread prediction.

### ✅ What This System Does (Matching Your Workflow):

1. **Fetches Instagram Insights** → City-level impression/reach data
2. **Builds Graph Nodes** → Each city becomes a node
3. **Detects Spread Edges** → City A → City B connections
4. **Creates Snapshots** → Time-series of graph evolution
5. **Exports Dataset** → Ready for GNN training

### ❌ What It Does NOT Do:

- ❌ Track clicks on links (that's different system)
- ❌ Store IP addresses or personal data
- ❌ Require users to click anything

---

## 🎯 The Key Difference

### What I Built Before (WRONG):
```
User clicks link → Log city → Store in DB
```
**Problem:** Only tracks people who CLICKED

### What You Actually Need (CORRECT):
```
Instagram API → Fetch impressions by city → Build graph
```
**Benefit:** Tracks EVERYONE who VIEWED the post!

---

## 📊 Data Flow

```
┌─────────────────────┐
│ Post Published to   │
│ Instagram           │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Every 30 minutes:   │
│ Fetch Instagram     │
│ Insights API        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Parse City Data:    │
│ - Mumbai: 5000 imp  │
│ - Pune: 2000 imp    │
│ - Dubai: 1000 imp   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Update Graph:       │
│ - Create nodes      │
│ - Detect edges      │
│ - Calculate metrics │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Store Snapshot:     │
│ - Graph state @ t   │
│ - For GNN training  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Export Dataset:     │
│ - nodes.json        │
│ - edges.json        │
│ - timeseries.json   │
└─────────────────────┘
```

---

## 🗄️ Database Schema

### 1. `graph_nodes` Table
```python
city: Mumbai
country: India
campaign_id: laptop_xxx
impressions: 5000        # From Instagram API
reach: 3000              # From Instagram API
engagement: 450          # From Instagram API
first_seen: 2026-02-10 10:00
growth_rate: 0.45
engagement_rate: 0.15
```

### 2. `graph_edges` Table
```python
from_city: Pune
to_city: Mumbai
time_delta: 3600         # 1 hour
weight: 0.8
confidence: 0.7
transfer_rate: 2.5       # Mumbai got 2.5x impressions
```

### 3. `viral_spread_snapshots` Table
```python
snapshot_time: 2026-02-10 12:00
hours_since_publish: 2
total_nodes: 5
total_edges: 4
total_impressions: 10000
trending_city: Mumbai
graph_density: 0.6
```

---

## 🚀 How to Use

### Step 1: Publish Post to Instagram

```python
python test_laptop_publish_final.py
```

This publishes your laptop image to Instagram.

### Step 2: Run Automated Collector

```python
python run_gnn_data_collection.py
```

This will:
- Fetch Instagram insights every 30 minutes
- Build graph nodes and edges
- Create snapshots
- Export dataset

### Step 3: View Collected Data

```python
python view_gnn_data.py
```

Shows:
- All graph nodes (cities)
- All edges (spread paths)
- Time-series snapshots

### Step 4: Export for GNN Training

Dataset is automatically exported to: `gnn_training_dataset.json`

Format:
```json
{
  "nodes": [
    {
      "id": "Mumbai",
      "impressions": 5000,
      "reach": 3000,
      "engagement": 450,
      "engagement_rate": 0.15,
      "growth_rate": 0.45
    }
  ],
  "edges": [
    {
      "from": "Pune",
      "to": "Mumbai",
      "time_delta": 3600,
      "weight": 0.8,
      "transfer_rate": 2.5
    }
  ],
  "snapshots": [
    {
      "hours_since_publish": 2,
      "nodes": 5,
      "edges": 4,
      "impressions": 10000,
      "trending_city": "Mumbai"
    }
  ]
}
```

---

## 📈 GNN Training Features

### Node Features (Input to GNN):
- `impressions` - How many times shown
- `reach` - Unique accounts
- `engagement` - Total interactions
- `engagement_rate` - engagement/reach
- `growth_rate` - Change over time
- `first_seen` - Temporal feature

### Edge Features:
- `time_delta` - Time between cities
- `weight` - Connection strength
- `transfer_rate` - Spread multiplier
- `confidence` - How sure we are

### Graph Features:
- `density` - How connected
- `avg_node_degree` - Avg connections per city
- `clustering_coefficient` - Local clustering

### Temporal Features:
- `hours_since_publish` - Time evolution
- `snapshot_time` - When measured
- Multiple snapshots = time series

---

## 🎯 GNN Prediction Tasks

### What Your GNN Can Learn:

1. **Next City Prediction**
   - Input: Current graph state
   - Output: Which city activates next

2. **Spread Velocity**
   - Input: First N hours of data
   - Output: Impressions at hour N+1

3. **Final Reach Estimation**
   - Input: Early graph (< 24h)
   - Output: Estimated total reach

4. **Viral Detection**
   - Input: Graph features
   - Output: Will this go viral? (binary)

5. **Trending City Prediction**
   - Input: Current state
   - Output: Which city will trend

---

## 📊 Instagram API Details

### Metrics You Get (FREE):

From Instagram Graph API:
- ✅ Impressions (by city)
- ✅ Reach (by city)
- ✅ Engagement (likes + comments + shares)
- ✅ Profile visits
- ✅ Saves
- ✅ Shares

### What You DON'T Get:

- ❌ Individual user data
- ❌ Exact viewing times per user
- ❌ User demographics details

### Privacy Compliance:

- ✅ No personal data stored
- ✅ Only aggregated city counts
- ✅ Instagram API compliant
- ✅ GDPR/privacy safe

---

## 🔧 Installation

### 1. Create Database Tables

```python
# Add to backend/app/db/models.py
from backend.app.db.gnn_models import GraphNode, GraphEdge, ViralSpreadSnapshot
```

### 2. Run Migrations

```bash
alembic revision --autogenerate -m "Add GNN tables"
alembic upgrade head
```

### 3. Install Dependencies

```bash
pip install requests sqlalchemy psycopg2
```

---

## 📝 Configuration

Update `.env`:
```
INSTAGRAM_ACCESS_TOKEN=your_token
INSTAGRAM_ACCOUNT_ID=17841478698032119
```

---

## ⏰ Collection Schedule

### Default:
- **Interval:** Every 30 minutes
- **Duration:** Continuous (until stopped)
- **Snapshots:** Every hour

### Recommended:
- Collect for at least **48 hours** per post
- Run for **10-20 posts** to build dataset
- This gives you **500-1000 data points** for training

---

## 📤 Exporting Data

### Manual Export:
```python
from backend.app.services.gnn_data_collector import GNNDataCollector

collector = GNNDataCollector()
collector.export_gnn_dataset("my_dataset.json")
```

### Automatic Export:
Dataset is auto-exported when you stop collection (Ctrl+C).

---

## 🧪 Example GNN Training Code

```python
import torch
import torch.nn as nn
from torch_geometric.nn import GCNConv
from torch_geometric.data import Data
import json

# Load your dataset
with open('gnn_training_dataset.json') as f:
    dataset = json.load(f)

# Build PyTorch Geometric graph
nodes = dataset['nodes']
edges = dataset['edges']

# Create node feature matrix
node_features = torch.tensor([
    [n['impressions'], n['reach'], n['engagement_rate']]
    for n in nodes
], dtype=torch.float)

# Create edge index
city_to_idx = {n['id']: i for i, n in enumerate(nodes)}
edge_index = torch.tensor([
    [city_to_idx[e['from']], city_to_idx[e['to']]]
    for e in edges
], dtype=torch.long).t()

# Create PyG Data object
graph = Data(x=node_features, edge_index=edge_index)

# Define GNN model
class ViralSpreadGNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = GCNConv(3, 16)  # 3 input features
        self.conv2 = GCNConv(16, 8)
        self.fc = nn.Linear(8, 1)  # Predict next impressions
    
    def forward(self, data):
        x, edge_index = data.x, data.edge_index
        x = self.conv1(x, edge_index).relu()
        x = self.conv2(x, edge_index).relu()
        return self.fc(x)

# Train model
model = ViralSpreadGNN()
optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

# Your training loop here...
```

---

## 🎯 Success Metrics

### Data Collection Success:
- ✅ At least 20 posts tracked
- ✅ 10+ cities per post
- ✅ 48+ hours of snapshots per post
- ✅ Clean graph (edges make sense)

### GNN Training Success:
- ✅ Model converges (loss decreases)
- ✅ 70-85% prediction accuracy
- ✅ Generalizes to new posts
- ✅ Predicts trending cities correctly

---

## 🔍 Troubleshooting

### No City Data From Instagram:
**Problem:** `city_data` is empty

**Solutions:**
1. Post must be 24-48 hours old
2. Need sufficient reach (>1000 impressions)
3. Check Instagram API permissions
4. Verify access token

### Graph Not Building:
**Problem:** No nodes/edges created

**Solutions:**
1. Check database connection
2. Verify campaign exists
3. Ensure post_id is correct
4. Check Instagram API response

### Low Accuracy:
**Problem:** GNN predictions poor

**Solutions:**
1. Collect more data (more posts)
2. Add more node features
3. Tune GNN architecture
4. Use temporal features

---

## 📚 Files Created

1. `backend/app/db/gnn_models.py` - Database schema
2. `collect_gnn_training_data.py` - One-time collector
3. `run_gnn_data_collection.py` - Automated collector
4. `view_gnn_data.py` - Data viewer
5. `GNN_DATA_COLLECTION_GUIDE.md` - This guide

---

## 🚀 Next Steps

1. ✅ Publish laptop post (DONE)
2. ⏳ Run automated collector for 48 hours
3. ⏳ Collect data from 10-20 posts
4. ⏳ Train GNN model
5. ⏳ Predict viral spread in real-time

---

## 🎉 Summary

You now have a complete system for:
- ✅ Collecting REAL Instagram viewing data
- ✅ Building graph automatically
- ✅ Exporting for GNN training
- ✅ Privacy-safe (no personal data)
- ✅ Scalable (works for any post)

**Start collecting data now to train your viral spread prediction GNN!** 🧠📊
