"""
GNN TRAINING PIPELINE (v2: Content-Aware)
==========================================

Trains the ViralSpreadGNN on the multi-category synthetic dataset,
now with 8-dim CONTENT FEATURES per campaign.

Process:
1. Load 'gnn_synthetic_multicategory_data.json' (includes content_features)
2. Preprocess data into Graph Tensors (PyTorch Geometric Data objects)
3. Build content feature tensors from each sample
4. Train the model (Binary Cross Entropy Loss) with content branch
5. Evaluate prediction accuracy
6. Save model checkpoint

Content Features (8-dim):
  [0] hook_strength      [1] cta_density        [2] sentiment_score
  [3] question_density   [4] urgency_score      [5] phrase_diversity
  [6] avg_segment_length [7] keyword_density
"""

import json
import torch
import torch.nn as nn
import torch.optim as optim
from torch_geometric.data import Data
import numpy as np
import os
import sys

# Ensure project root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Simple Log Helper
def log_info(msg):
    print(msg, flush=True)
    with open("training_flow.log", "a", encoding="utf-8") as f:
        f.write(f"{msg}\n")

log_info(f"🚀 Script started at {os.getcwd()}")

try:
    from backend.app.agents.gnn_model import (
        ViralSpreadGNN,
        vocab_config,
        CONTENT_FEATURE_DIM,
    )
    log_info("✅ Imported ViralSpreadGNN (v2: Content-Aware) successfully.")
except Exception as e:
    log_info(f"❌ Import failed: {e}")
    import traceback
    log_info(traceback.format_exc())
    sys.exit(1)


# --- CONFIGURATION ---
DATA_FILE = "gnn_synthetic_multicategory_data.json"
MODEL_SAVE_PATH = "viral_predictor.pth"
EPOCHS = 50
LEARNING_RATE = 0.01

# --- PREPROCESSING ---

def load_data():
    log_info(f"📥 Loading dataset: {DATA_FILE}")
    try:
        with open(DATA_FILE, 'r') as f:
            raw_data = json.load(f)
        log_info(f"✅ Loaded {len(raw_data)} samples.")

        # Check if content_features are present
        has_content = any("content_features" in s for s in raw_data[:5])
        log_info(f"📊 Content features present: {'Yes' if has_content else 'No (legacy data)'}")

        return raw_data
    except FileNotFoundError:
        log_info(f"❌ Data file not found: {DATA_FILE}")
        sys.exit(1)
    except json.JSONDecodeError:
        log_info(f"❌ Invalid JSON in data file: {DATA_FILE}")
        sys.exit(1)


def get_city_index(city_name):
    return vocab_config["cities"].index(city_name)

def get_category_index(category_name):
    return vocab_config["categories"].index(category_name)

def build_graph_tensor(simulation_step):
    """
    Converts a simulation step into graph tensors.
    """
    # Nodes are always the same 11 cities
    # Features: Just their ID for now (embedding layer handles the rest)
    x = torch.tensor(list(range(vocab_config["num_nodes"])), dtype=torch.long)

    # Edges: fully connected graph for message passing
    edges = []
    for i in range(vocab_config["num_nodes"]):
        for j in range(vocab_config["num_nodes"]):
            if i != j:
                edges.append([i, j])

    edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()

    return x, edge_index


def build_content_tensor(simulation_step):
    """
    Extract the 8-dim content feature vector from a training sample.

    If the sample doesn't have content_features (legacy data),
    returns a zero vector so the model can still train.
    """
    features = simulation_step.get("content_features", None)

    if features and len(features) == CONTENT_FEATURE_DIM:
        return torch.tensor([features], dtype=torch.float32)  # [1, 8]
    else:
        return torch.zeros(1, CONTENT_FEATURE_DIM, dtype=torch.float32)


# --- TRAINING LOOP ---

def train_model():
    log_info("=" * 60)
    log_info("🚀 STARTING GNN TRAINING (v2: Content-Aware)")
    log_info("=" * 60)

    raw_data = load_data()
    log_info(f"📊 Training samples: {len(raw_data)}")
    log_info(f"📐 Content feature dimension: {CONTENT_FEATURE_DIM}")

    # Check content feature statistics
    content_samples = [s for s in raw_data if "content_features" in s]
    if content_samples:
        log_info(f"🎯 Samples with content features: {len(content_samples)}/{len(raw_data)}")
        avg_boost = sum(s.get("content_boost", 1.0) for s in content_samples) / len(content_samples)
        log_info(f"📈 Avg content boost: {avg_boost:.3f}")
    else:
        log_info("⚠️  No content features in dataset (legacy mode; zero vectors used)")

    # Initialize Model with content branch
    model = ViralSpreadGNN(
        num_nodes=vocab_config["num_nodes"],
        num_categories=vocab_config["num_categories"],
        content_feature_dim=CONTENT_FEATURE_DIM,
        use_content_branch=True,
    )

    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    log_info(f"🏗️  Model parameters: {total_params:,} total ({trainable_params:,} trainable)")

    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    criterion = nn.BCELoss()  # Binary Cross Entropy for "Will City X activate?"

    # Training Loop
    model.train()

    for epoch in range(EPOCHS):
        total_loss = 0
        correct_predictions = 0
        total_predictions = 0

        for sim in raw_data:
            category_idx = get_category_index(sim.get('category', 'General'))
            target_cities = [get_city_index(c) for c in sim['nodes_hit']]

            # Prepare Inputs
            x, edge_index = build_graph_tensor(sim)
            cat_tensor = torch.tensor([category_idx], dtype=torch.long)
            content_tensor = build_content_tensor(sim)  # [1, 8]  [NEW]

            # Target Vector (Multi-hot encoding of active cities)
            y_target = torch.zeros(1, vocab_config["num_nodes"])
            y_target[0, target_cities] = 1.0

            # Forward Pass with content features
            optimizer.zero_grad()
            prediction = model(x, edge_index, cat_tensor, content_features=content_tensor)

            # Loss Calculation
            loss = criterion(prediction, y_target)
            loss.backward()
            optimizer.step()

            total_loss += loss.item()

            # Accuracy Metric (Threshold 0.5)
            predicted_labels = (prediction > 0.5).float()
            correct_predictions += (predicted_labels == y_target).sum().item()
            total_predictions += vocab_config["num_nodes"]

        avg_loss = total_loss / len(raw_data)
        accuracy = correct_predictions / total_predictions

        if (epoch + 1) % 5 == 0:
            log_info(f"Epoch {epoch+1}/{EPOCHS} | Loss: {avg_loss:.4f} | Accuracy: {accuracy:.2%}")

    log_info("\n✅ Training Complete!")

    # Save Model
    torch.save(model.state_dict(), MODEL_SAVE_PATH)
    log_info(f"💾 Model saved to: {MODEL_SAVE_PATH}")
    log_info(f"   Architecture: GNN + Category Emb + Content Branch ({CONTENT_FEATURE_DIM}-dim)")

    return model

# --- INFERENCE TEST ---

def predict_spread(model, start_city, category, content_features=None):
    """
    Predict probability of spread for a hypothetical scenario.

    Args:
        model: Trained ViralSpreadGNN
        start_city: Starting city name
        category: Content category
        content_features: Optional 8-dim content feature vector
    """
    model.eval()

    cat_idx = get_category_index(category)
    x, edge_index = build_graph_tensor(None)
    cat_tensor = torch.tensor([cat_idx], dtype=torch.long)

    # Build content tensor
    if content_features:
        content_tensor = torch.tensor([content_features], dtype=torch.float32)
    else:
        content_tensor = torch.zeros(1, CONTENT_FEATURE_DIM, dtype=torch.float32)

    with torch.no_grad():
        prediction = model(x, edge_index, cat_tensor, content_features=content_tensor)

    log_info(f"\n🔮 PREDICTION: Start in {start_city} ({category})")
    if content_features:
        log_info(f"   Content Signal: hook={content_features[0]:.2f} urgency={content_features[4]:.2f}")
    log_info("-" * 40)

    probs = prediction[0].tolist()
    cities = vocab_config["cities"]

    # Sort by probability
    results = sorted(zip(cities, probs), key=lambda x: x[1], reverse=True)

    for city, prob in results:
        bar = "█" * int(prob * 20)
        log_info(f"{city:12} : {prob:.2%} {bar}")

if __name__ == "__main__":
    trained_model = train_model()

    # Test 1: Tech content with STRONG hook + urgency (should spread faster)
    log_info("\n" + "=" * 60)
    log_info("🧪 CONTENT-AWARE PREDICTION TESTS")
    log_info("=" * 60)

    strong_content = [0.90, 0.30, 0.75, 0.10, 0.85, 0.50, 0.55, 0.40]
    weak_content   = [0.15, 0.05, 0.40, 0.02, 0.10, 0.20, 0.30, 0.10]

    log_info("\n📊 Scenario A: Tech + STRONG content (high hook + urgency)")
    predict_spread(trained_model, "Pune", "Tech", content_features=strong_content)

    log_info("\n📊 Scenario B: Tech + WEAK content (low hook + urgency)")
    predict_spread(trained_model, "Pune", "Tech", content_features=weak_content)

    log_info("\n📊 Scenario C: Fashion + STRONG content")
    predict_spread(trained_model, "Mumbai", "Fashion", content_features=strong_content)

    log_info("\n📊 Scenario D: Fashion + WEAK content")
    predict_spread(trained_model, "Mumbai", "Fashion", content_features=weak_content)
