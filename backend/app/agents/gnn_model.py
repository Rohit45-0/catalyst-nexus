"""
GNN MODEL ARCHITECTURE - VIRAL SPREAD PREDICTOR (v2: Content-Aware)
===================================================================

This Neural Network learns the "Physics of Viral Spread" from city-to-city graph data,
now enhanced with CONTENT SIGNALS from video transcripts.

Architecture:
1. Spatial Dependencies (Which cities are connected?) -> GCNConv
2. Temporal Dynamics (How spread evolves over time steps?) -> LSTM
3. Category Embeddings (How 'Tech' spreads differently from 'Fashion') -> Embedding Layer
4. Content Branch  [NEW]  (How content quality affects spread velocity) -> MLP

Input:
- Current State of Graph (Active cities, Time step)
- Category Context (e.g., "Tech")
- Content Feature Vector (8-dim: hook_strength, cta_density, sentiment, ...)  [NEW]

Output:
- Probability of infection for every city in the network at the next time step.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv, global_mean_pool


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT FEATURE DIMENSION (must match transcript_feature_extractor.py)
# ═══════════════════════════════════════════════════════════════════════════════

CONTENT_FEATURE_DIM = 8


class ContentEncoder(nn.Module):
    """
    Small MLP that projects the raw 8-dim content feature vector into a
    latent embedding space compatible with the GNN hidden dimension.

    Architecture: 8 -> 32 -> hidden_dim (default 32)
    """

    def __init__(self, input_dim: int = CONTENT_FEATURE_DIM, hidden_dim: int = 32):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.15),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
        )

    def forward(self, content_features: torch.Tensor) -> torch.Tensor:
        """
        Args:
            content_features: [1, 8] raw feature vector
        Returns:
            [1, hidden_dim] content embedding
        """
        return self.net(content_features)


class ViralSpreadGNN(torch.nn.Module):
    def __init__(
        self,
        num_nodes,
        num_categories=4,
        embedding_dim=16,
        hidden_dim=32,
        content_feature_dim=CONTENT_FEATURE_DIM,
        use_content_branch=True,
    ):
        super(ViralSpreadGNN, self).__init__()

        self.num_nodes = num_nodes
        self.use_content_branch = use_content_branch

        # 1. CATEGORY EMBEDDING
        # Learns a vector representation for each category (Tech, Fashion, etc.)
        # Input: Category ID (0-3) -> Output: 16-dim vector
        self.category_emb = nn.Embedding(num_categories, embedding_dim)

        # 2. NODE EMBEDDING
        # Learns a vector for each City (Mumbai, Delhi, etc.)
        # Input: City ID (0-10) -> Output: 16-dim vector
        self.node_emb = nn.Embedding(num_nodes, embedding_dim)

        # 3. GRAPH CONVOLUTION (Spatial Logic)
        # GCN layer combines city features + neighbor features
        # Input: Node Features (16) -> Output: Hidden Features (32)
        self.conv1 = GCNConv(embedding_dim, hidden_dim)
        self.conv2 = GCNConv(hidden_dim, hidden_dim)

        # 4. TEMPORAL PROCESSING (Time Logic)
        # LSTM processes the sequence of graph states
        # Input: Graph State Vector -> Output: Dynamic Hidden State
        self.lstm = nn.LSTM(hidden_dim, hidden_dim, batch_first=True)

        # 5. CONTENT BRANCH  [NEW]
        # Encodes the 8-dim transcript feature vector into hidden_dim space
        if use_content_branch:
            self.content_encoder = ContentEncoder(
                input_dim=content_feature_dim,
                hidden_dim=hidden_dim,
            )

        # 6. PREDICTION HEAD
        # Combines Graph State + Category Context + Content Signal -> Probability per city
        # Input dimension depends on whether content branch is active
        fusion_dim = hidden_dim + embedding_dim  # graph_vec + cat_vec
        if use_content_branch:
            fusion_dim += hidden_dim  # + content_vec

        self.fc1 = nn.Linear(fusion_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, num_nodes)  # Output: Score for each city

        self.dropout = nn.Dropout(0.2)

    def forward(self, x, edge_index, category_id, content_features=None, hidden_state=None):
        """
        Forward pass of the model.

        Args:
            x: Node features (or Node IDs) [Num Nodes]
            edge_index: Graph connectivity [2, Num Edges]
            category_id: Category of the post (Int) [1]
            content_features: [NEW] 8-dim content signal [1, 8] or None
            hidden_state: Previous LSTM state (optional)
        """

        # 1. Embed Inputs
        x = self.node_emb(x)  # [Num Nodes, Emb Dim]
        cat_vec = self.category_emb(category_id)  # [1, Emb Dim]

        # 2. Spatial Graph Convolutions
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = self.dropout(x)
        x = self.conv2(x, edge_index)  # [Num Nodes, Hidden Dim]

        # 3. Global Graph Representation (Pooling)
        # Collapse all node features into one "Graph Vector" representing current state
        graph_vec = global_mean_pool(
            x, torch.zeros(x.size(0), dtype=torch.long)
        )  # [1, Hidden Dim]

        # 4. Combine Graph State + Category + Content
        if self.use_content_branch and content_features is not None:
            content_vec = self.content_encoder(content_features)  # [1, Hidden Dim]
            combined = torch.cat([graph_vec, cat_vec, content_vec], dim=1)
        else:
            # Backward compatible: works without content features
            combined = torch.cat([graph_vec, cat_vec], dim=1)
            # Pad with zeros if model expects content branch but no features given
            if self.use_content_branch:
                zero_content = torch.zeros(1, self.fc1.in_features - combined.size(1))
                combined = torch.cat([combined, zero_content], dim=1)

        # 5. Predict Next Active Nodes
        out = self.fc1(combined)
        out = F.relu(out)
        out = self.fc2(out)  # [1, Num Nodes]

        # Sigmoid gives probability (0 to 1) for each city activating
        return torch.sigmoid(out)


vocab_config = {
    "num_nodes": 11,  # Number of cities in network
    "num_categories": 4,  # Tech, Fashion, Finance, General
    "content_feature_dim": CONTENT_FEATURE_DIM,  # 8-dim transcript features [NEW]
    "cities": [
        "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Pune",
        "Chennai", "Noida", "Gurgaon", "Ahmedabad", "Indore", "Dubai"
    ],
    "categories": ["Tech", "Fashion", "Finance", "General"],
}
