"""
Synthetic Viral Spread Generator (Multi-Category Gravity Model)
===============================================================

Generates realistic viral spread datasets for GNN training across MULTIPLE CATEGORIES.
Solves the scalability problem by simulating how different niches spread differently.

The Core Idea:
- "Tech" content spreads faster in Bangalore/Hyderabad
- "Fashion" content spreads faster in Mumbai/Delhi
- "Finance" content spreads faster in Mumbai/Gurgaon

This allows ONE GNN model to learn all patterns by taking 'Category' as an input.

Phase 2 Enhancement:
Each training sample now includes an 8-dim 'content_features' vector representing
transcript signals (hook_strength, cta_density, sentiment, question_density,
urgency, phrase_diversity, avg_segment_length, keyword_density).

The content_features also MODULATE the spread probability: stronger hooks and
higher urgency = faster spread, giving the GNN a content-aware signal to learn from.
"""

import json
import random
import math
import uuid
import sys
import os

# Ensure project root is in sys.path for import
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.app.services.transcript_feature_extractor import (
    TranscriptFeatureExtractor,
    FEATURE_NAMES,
    CONTENT_FEATURE_DIM,
)

# 1. DEFINING THE NETWORK (Indian Tech Hubs)
# Base weights (Population/General internet usage)
CITIES = {
    "Mumbai":    {"lat": 19.0760, "lon": 72.8777, "base_weight": 1.0},
    "Delhi":     {"lat": 28.7041, "lon": 77.1025, "base_weight": 0.95},
    "Bangalore": {"lat": 12.9716, "lon": 77.5946, "base_weight": 0.90},
    "Hyderabad": {"lat": 17.3850, "lon": 78.4867, "base_weight": 0.85},
    "Pune":      {"lat": 18.5204, "lon": 73.8567, "base_weight": 0.70},
    "Chennai":   {"lat": 13.0827, "lon": 80.2707, "base_weight": 0.80},
    "Noida":     {"lat": 28.5355, "lon": 77.3910, "base_weight": 0.50},
    "Gurgaon":   {"lat": 28.4595, "lon": 77.0266, "base_weight": 0.60},
    "Ahmedabad": {"lat": 23.0225, "lon": 72.5714, "base_weight": 0.60},
    "Indore":    {"lat": 22.7196, "lon": 75.8577, "base_weight": 0.40},
    "Dubai":     {"lat": 25.2048, "lon": 55.2708, "base_weight": 0.50},
}

# 2. CATEGORY MODIFIERS
# How different niches boost specific cities
CATEGORY_MODIFIERS = {
    "Tech": {
        "Bangalore": 1.5, "Hyderabad": 1.4, "Pune": 1.3, "Gurgaon": 1.2,
        "Mumbai": 0.8, "Delhi": 0.8  # Tech spreads slightly less in general metros vs hubs
    },
    "Fashion": {
        "Mumbai": 1.5, "Delhi": 1.4, "Dubai": 1.3,
        "Bangalore": 0.8, "Hyderabad": 0.7  # Fashion spreads less in tech hubs
    },
    "Finance": {
        "Mumbai": 1.6, "Gurgaon": 1.4, "Ahmedabad": 1.3, "Dubai": 1.2
    },
    "General": {} # No modifiers, uses base population weights
}

def get_city_weight(city, category):
    """Calculate effective weight of a city for a specific category"""
    base = CITIES[city]['base_weight']
    
    # Apply modifier if exists for this category/city combo
    modifier = 1.0
    if category in CATEGORY_MODIFIERS:
        modifier = CATEGORY_MODIFIERS[category].get(city, 1.0)
        
    return base * modifier

def calculate_distance(city1, city2):
    """Calculate crude distance metric between two cities"""
    c1 = CITIES[city1]
    c2 = CITIES[city2]
    return math.sqrt((c1['lat']-c2['lat'])**2 + (c1['lon']-c2['lon'])**2)

def calculate_content_boost(content_features: list) -> float:
    """
    Calculate a spread multiplier from the 8-dim content feature vector.
    
    Key features that influence viral spread:
    - hook_strength [0]: strong opening = faster initial spread
    - cta_density [1]: more CTAs = more shares
    - urgency_score [4]: urgency drives immediate action
    - sentiment_score [2]: positive content spreads more naturally
    
    Returns a multiplier in range [0.7, 1.4]
    """
    if not content_features or len(content_features) < CONTENT_FEATURE_DIM:
        return 1.0
    
    hook     = content_features[0]  # hook_strength
    cta      = content_features[1]  # cta_density
    sentiment = content_features[2] # sentiment_score
    urgency  = content_features[4]  # urgency_score
    
    # Weighted combination: hook and urgency matter most for spread velocity
    raw_boost = (hook * 0.35) + (urgency * 0.30) + (cta * 0.20) + (sentiment * 0.15)
    
    # Map to [0.7, 1.4] range
    boost = 0.7 + (raw_boost * 0.7)
    return round(boost, 3)


def calculate_probability(from_city, to_city, category, content_boost=1.0):
    """
    GRAVITY MODEL (Category + Content Aware):
    Prob ~ (Weight_A * Weight_B) / Distance * content_boost
    
    Weights depend on Category.
    Content boost modulates based on transcript signal quality.
    """
    if from_city == to_city: return 0
    
    dist = calculate_distance(from_city, to_city)
    
    # Get weights specific to this category context
    w_from = get_city_weight(from_city, category)
    w_to = get_city_weight(to_city, category)
    
    # Gravity formula with content boost
    probability = (w_from * w_to) / (dist ** 1.5) * content_boost
    return probability

def generate_viral_cascade(category, start_city=None, num_steps=10):
    """Simulates a post going viral in a specific category.
    
    Now generates per-campaign content_features and uses them to
    modulate spread probability, so the GNN learns content-aware patterns.
    """
    
    # Generate synthetic content features for this campaign
    content_features = TranscriptFeatureExtractor.generate_synthetic(category)
    content_boost = calculate_content_boost(content_features)
    
    # If no start city, pick one weighted by the category relevance
    if not start_city:
        cities = list(CITIES.keys())
        weights = [get_city_weight(c, category) for c in cities]
        start_city = random.choices(cities, weights=weights, k=1)[0]
    
    campaign_id = f"{category[:3].lower()}_{uuid.uuid4().hex[:8]}"
    current_active_nodes = {start_city}
    infected_nodes = {start_city: 0} # City: Time-step infected
    edges = []
    
    for t in range(1, num_steps + 1):
        new_infections = set()
        
        for source in current_active_nodes:
            for target in CITIES:
                if target not in infected_nodes:
                    # Pass category AND content boost to probability calculation
                    prob = calculate_probability(source, target, category, content_boost)
                    
                    roll = random.random() * 2.0 
                    
                    if roll < prob:
                        new_infections.add(target)
                        infected_nodes[target] = t
                        
                        edges.append({
                            "from": source,
                            "to": target,
                            "step": t,
                            "probability": round(prob, 3)
                        })
        
        if new_infections:
            current_active_nodes.update(new_infections)
        else:
            break
            
    return {
        "campaign_id": campaign_id,
        "category": category,
        "start_city": start_city,
        "content_features": content_features,
        "content_boost": content_boost,
        "nodes_hit": list(infected_nodes.keys()),
        "edges": edges,
        "total_steps": t
    }

# 3. GENERATE MULTI-CATEGORY TRAINING DATASET
print("="*80)
print("🧬 GENERATING MULTI-CATEGORY SYNTHETIC GNN DATA")
print("="*80)

dataset = []
NUM_SAMPLES = 2000  # More samples to cover multiple categories
CATEGORIES = ["Tech", "Fashion", "Finance", "General"]

print(f"🌍 Simulating {NUM_SAMPLES} campaigns across {len(CATEGORIES)} categories...")

for i in range(NUM_SAMPLES):
    # Randomly select a category for this simulation
    cat = random.choice(CATEGORIES)
    simulation = generate_viral_cascade(cat)
    dataset.append(simulation)

# 4. EXPORT
output_file = "gnn_synthetic_multicategory_data.json"
with open(output_file, "w") as f:
    json.dump(dataset, f, indent=2)

print(f"\n✅ GENERATION COMPLETE!")
print(f"   Created {len(dataset)} training samples.")
print(f"   File: {output_file}")

print("\n📊 SAMPLES BY CATEGORY:")
for cat in CATEGORIES:
    cat_samples = [d for d in dataset if d['category'] == cat]
    count = len(cat_samples)
    avg_boost = sum(d['content_boost'] for d in cat_samples) / max(count, 1)
    avg_cities = sum(len(d['nodes_hit']) for d in cat_samples) / max(count, 1)
    print(f"   - {cat}: {count} sims | avg content_boost: {avg_boost:.3f} | avg cities hit: {avg_cities:.1f}")

print(f"\n🎯 CONTENT FEATURE VECTOR ({CONTENT_FEATURE_DIM}-dim):")
for i, name in enumerate(FEATURE_NAMES):
    vals = [d['content_features'][i] for d in dataset]
    avg = sum(vals) / len(vals)
    print(f"   [{i}] {name:22s}: mean={avg:.3f}")

print("\n💡 SCALABILITY SOLVED:")
print("   We train ONE model that takes 'Category' + 'Content Features' as inputs.")
print("   The model learns: 'If Category=Tech + high hook_strength, prioritize Bangalore edges.'")
print(f"   Content boost range in dataset: {min(d['content_boost'] for d in dataset):.3f} — {max(d['content_boost'] for d in dataset):.3f}")
