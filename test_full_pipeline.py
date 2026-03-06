"""
Tuned training: content-aware GNN with proper hyperparameters.
Fixes: lower LR, weight decay, more epochs, gradient checks.
"""
import sys, os, json, random
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import torch
import torch.nn as nn
import torch.optim as optim

from backend.app.agents.gnn_model import ViralSpreadGNN, vocab_config, CONTENT_FEATURE_DIM
from backend.app.services.transcript_feature_extractor import TranscriptFeatureExtractor

LOG = "full_pipeline_output.txt"
def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(str(msg) + "\n")
with open(LOG, "w") as f: f.write("")

# ═══ LOAD DATA ═══
log("Loading data...")
with open("gnn_synthetic_multicategory_data.json", "r") as f:
    dataset = json.load(f)
log(f"Loaded {len(dataset)} samples, {sum(1 for d in dataset if 'content_features' in d)} with content features")

# ═══ MODEL SETUP ═══
model = ViralSpreadGNN(
    num_nodes=vocab_config["num_nodes"],
    num_categories=vocab_config["num_categories"],
    content_feature_dim=CONTENT_FEATURE_DIM,
    use_content_branch=True,
)

total_params = sum(p.numel() for p in model.parameters())
content_params = sum(p.numel() for p in model.content_encoder.parameters())
log(f"Model: {total_params:,} total params ({content_params:,} in content branch)")

# Use lower LR with weight decay for better generalization
optimizer = optim.Adam(model.parameters(), lr=0.005, weight_decay=1e-4)
criterion = nn.BCELoss()

# Shuffle dataset for better learning
random.shuffle(dataset)

def get_city_idx(c): return vocab_config["cities"].index(c)
def get_cat_idx(c): return vocab_config["categories"].index(c)

# Pre-build edge index (static)
edges = [[i,j] for i in range(11) for j in range(11) if i!=j]
static_edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()
static_x = torch.tensor(list(range(11)), dtype=torch.long)

# ═══ TRAINING ═══
EPOCHS = 80
log(f"\nTraining {EPOCHS} epochs, LR=0.005, weight_decay=1e-4")
log("=" * 60)

model.train()

for epoch in range(EPOCHS):
    total_loss = 0
    correct = 0
    total = 0

    # Shuffle each epoch for better convergence
    random.shuffle(dataset)

    for sim in dataset:
        cat_idx = get_cat_idx(sim.get('category', 'General'))
        targets = [get_city_idx(c) for c in sim['nodes_hit']]

        cat_t = torch.tensor([cat_idx], dtype=torch.long)
        cf = sim.get('content_features', [0.0]*8)
        cf_t = torch.tensor([cf], dtype=torch.float32)

        y = torch.zeros(1, 11)
        y[0, targets] = 1.0

        optimizer.zero_grad()
        pred = model(static_x, static_edge_index, cat_t, content_features=cf_t)
        loss = criterion(pred, y)
        loss.backward()
        optimizer.step()

        total_loss += loss.item()
        correct += ((pred > 0.5).float() == y).sum().item()
        total += 11

    avg_loss = total_loss / len(dataset)
    acc = correct / total

    if (epoch + 1) % 10 == 0:
        # Check content branch gradients
        cb_grad = sum(p.grad.abs().mean().item() for p in model.content_encoder.parameters() if p.grad is not None)
        log(f"  Epoch {epoch+1:2d}/{EPOCHS} | Loss: {avg_loss:.4f} | Acc: {acc:.2%} | ContentBranch grad: {cb_grad:.6f}")

log(f"\n✅ Training complete!")

# Save
torch.save(model.state_dict(), "viral_predictor.pth")
log("Model saved to viral_predictor.pth")

# ═══ INFERENCE COMPARISON ═══
log("\n" + "=" * 60)
log("CONTENT-AWARE vs CONTENT-WEAK PREDICTIONS")
log("=" * 60)

model.eval()
strong = [0.95, 0.35, 0.80, 0.12, 0.90, 0.55, 0.60, 0.45]
weak   = [0.10, 0.03, 0.35, 0.02, 0.05, 0.15, 0.25, 0.08]

for label, category, features in [
    ("Tech + STRONG", "Tech", strong),
    ("Tech + WEAK  ", "Tech", weak),
    ("Fashion + STRONG", "Fashion", strong),
    ("Fashion + WEAK  ", "Fashion", weak),
    ("Finance + STRONG", "Finance", strong),
    ("Finance + WEAK  ", "Finance", weak),
]:
    cat_idx = get_cat_idx(category)
    cat_t = torch.tensor([cat_idx], dtype=torch.long)
    cf_t = torch.tensor([features], dtype=torch.float32)

    with torch.no_grad():
        pred = model(static_x, static_edge_index, cat_t, content_features=cf_t)

    probs = pred[0].tolist()
    cities = vocab_config["cities"]
    top3 = sorted(zip(cities, probs), key=lambda x: x[1], reverse=True)[:3]
    avg_prob = sum(probs) / len(probs)
    top_str = ", ".join(f"{c}={p:.3f}" for c, p in top3)
    log(f"  {label}: avg={avg_prob:.3f} | top3: {top_str}")

# Show if model learned content differentiation
log("\n--- Content Differentiation Check ---")
for category in ["Tech", "Fashion", "Finance"]:
    cat_t = torch.tensor([get_cat_idx(category)], dtype=torch.long)
    s_t = torch.tensor([strong], dtype=torch.float32)
    w_t = torch.tensor([weak], dtype=torch.float32)
    with torch.no_grad():
        s_pred = model(static_x, static_edge_index, cat_t, content_features=s_t)
        w_pred = model(static_x, static_edge_index, cat_t, content_features=w_t)
    
    s_avg = s_pred[0].mean().item()
    w_avg = w_pred[0].mean().item()
    diff = s_avg - w_avg
    log(f"  {category:8s}: strong_avg={s_avg:.4f} | weak_avg={w_avg:.4f} | diff={diff:+.4f} {'✅' if abs(diff) > 0.01 else '⚠️ minimal'}")

log("\n=== PIPELINE COMPLETE ===")
