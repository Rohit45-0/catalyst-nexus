
import sys
import os
import json

print("Starting debug...", flush=True)

# Ensure current directory is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

print(f"Path: {sys.path}", flush=True)

try:
    print("Importing ViralSpreadGNN...", flush=True)
    from backend.app.agents.gnn_model import ViralSpreadGNN
    print("✅ Imported ViralSpreadGNN", flush=True)
except Exception as e:
    print(f"❌ Failed import: {e}", flush=True)
    sys.exit(1)

DATA_FILE = "gnn_synthetic_multicategory_data.json"
try:
    print(f"Loading {DATA_FILE}...", flush=True)
    with open(DATA_FILE, 'r') as f:
        data = json.load(f)
    print(f"✅ Loaded {len(data)} items", flush=True)
except Exception as e:
    print(f"❌ Failed load: {e}", flush=True)

print("Debug complete.", flush=True)
