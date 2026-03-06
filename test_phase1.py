import sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
LOG = "test_phase1_output.txt"
def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(str(msg) + "\n")
with open(LOG, "w") as f: f.write("")

try:
    log("STEP3: Importing torch...")
    import torch
    log(f"  torch {torch.__version__} OK")
    
    log("STEP3: Importing torch_geometric...")
    from torch_geometric.nn import GCNConv, global_mean_pool
    log("  torch_geometric OK")
    
    log("STEP3: Importing gnn_model...")
    from backend.app.agents.gnn_model import ViralSpreadGNN, vocab_config, CONTENT_FEATURE_DIM
    log(f"  gnn_model OK. vocab keys={list(vocab_config.keys())}")
    log(f"  content_feature_dim={vocab_config.get('content_feature_dim')}")

    log("\nSTEP4: Creating model...")
    model = ViralSpreadGNN(
        num_nodes=vocab_config["num_nodes"],
        num_categories=vocab_config["num_categories"],
        content_feature_dim=CONTENT_FEATURE_DIM,
        use_content_branch=True,
    )
    total_params = sum(p.numel() for p in model.parameters())
    log(f"  Model: {total_params:,} params")
    log(f"  Architecture:\n{model}")

    log("\nSTEP5: Forward pass...")
    from backend.app.services.transcript_feature_extractor import TranscriptFeatureExtractor
    x = torch.tensor(list(range(11)), dtype=torch.long)
    edges = [[i,j] for i in range(11) for j in range(11) if i!=j]
    edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()
    cat = torch.tensor([0], dtype=torch.long)
    cf = torch.tensor([TranscriptFeatureExtractor.generate_synthetic("Tech")], dtype=torch.float32)
    with torch.no_grad():
        out = model(x, edge_index, cat, content_features=cf)
    log(f"  Output shape: {out.shape}")
    probs = out[0].tolist()
    cities = vocab_config["cities"]
    for c, p in sorted(zip(cities, probs), key=lambda x: x[1], reverse=True):
        log(f"    {c:12s}: {p:.3f}")

    log("\n=== ALL TESTS PASSED ===")
except Exception as e:
    import traceback
    log(f"ERROR: {e}")
    log(traceback.format_exc())
