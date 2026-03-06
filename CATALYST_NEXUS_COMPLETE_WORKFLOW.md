# CATALYST NEXUS - COMPLETE SYSTEM WORKFLOW
## From Product Image to Viral Prediction (Everything We Built)

**Last Updated:** 2026-02-11

---

## VISUAL OVERVIEW

```
                         CATALYST NEXUS - FULL ARCHITECTURE
  ═══════════════════════════════════════════════════════════════════

  [USER UPLOADS PRODUCT IMAGE]
           │
           ▼
  ┌─────────────────────────────────────────────────────────────┐
  │  PHASE 1: IDENTITY                                         │
  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
  │  │ GPT-4o Vision│───▶│ Visual DNA   │───▶│Identity Vault│  │
  │  │ (Analyze Img)│    │ JSON Extract │    │  (Supabase)  │  │
  │  └──────────────┘    └──────────────┘    └──────────────┘  │
  └─────────────────────────────────────────────────────────────┘
           │
           ▼
  ┌─────────────────────────────────────────────────────────────┐
  │  PHASE 2: INTELLIGENCE                                     │
  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
  │  │ Tavily Search│───▶│ YouTube/Jina │───▶│ GPT-4o DNA   │  │
  │  │ (Find Rivals)│    │ (Extract)    │    │ (Deconstruct)│  │
  │  └──────────────┘    └──────────────┘    └──────────────┘  │
  │                                               │            │
  │                                    ┌──────────┘            │
  │                                    ▼                       │
  │                           ┌──────────────┐                 │
  │                           │  GAP ANALYSIS │                │
  │                           │  (What rivals │                │
  │                           │   missed)     │                │
  │                           └──────────────┘                 │
  └─────────────────────────────────────────────────────────────┘
           │
           ▼
  ┌─────────────────────────────────────────────────────────────┐
  │  PHASE 3: CONTENT CREATION                                 │
  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
  │  │ GPT-4o Write │───▶│ Motion       │───▶│ Neural       │  │
  │  │ (Script/Post)│    │ Scaffold     │    │ Renderer     │  │
  │  └──────────────┘    └──────────────┘    └──────────────┘  │
  │  Uses: Visual DNA + Competitor Gaps + Market Data          │
  └─────────────────────────────────────────────────────────────┘
           │
           ▼
  ┌─────────────────────────────────────────────────────────────┐
  │  PHASE 4: DISTRIBUTION                                     │
  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
  │  │ Instagram    │    │ Campaign ID  │    │ Tracking     │  │
  │  │ Graph API    │    │ Generation   │    │ Link         │  │
  │  │ (Publish)    │    │              │    │ /p/camp_xxx  │  │
  │  └──────────────┘    └──────────────┘    └──────────────┘  │
  └─────────────────────────────────────────────────────────────┘
           │
           ▼
  ┌─────────────────────────────────────────────────────────────┐
  │  PHASE 5: ANALYTICS & TRACKING                             │
  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
  │  │ Click Track  │    │ IG Insights  │    │ Engagement   │  │
  │  │ Endpoint     │    │ Per City     │    │ Spread Track │  │
  │  │ IP → City    │    │ Impressions  │    │ Likers/Comms │  │
  │  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
  │         │                   │                   │          │
  │         └───────────┬───────┘───────────────────┘          │
  │                     ▼                                      │
  │            ┌──────────────┐    ┌──────────────┐            │
  │            │ Spike        │───▶│ Spread Graph │            │
  │            │ Detector     │    │ Builder      │            │
  │            └──────────────┘    └──────────────┘            │
  └─────────────────────────────────────────────────────────────┘
           │
           ▼
  ┌─────────────────────────────────────────────────────────────┐
  │  PHASE 6: GNN VIRAL PREDICTION                             │
  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
  │  │ Graph Nodes  │    │ Graph Edges  │    │ Snapshots    │  │
  │  │ (Cities)     │    │ (Spread)     │    │ (Time-series)│  │
  │  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
  │         │                   │                   │          │
  │         └───────────┬───────┘───────────────────┘          │
  │                     ▼                                      │
  │        ┌──────────────────────────┐                        │
  │        │ GNN Model (PyTorch Geo)  │                        │
  │        │ Predicts:                │                        │
  │        │  - Next city to activate │                        │
  │        │  - Spread velocity       │                        │
  │        │  - Final reach estimate  │                        │
  │        └──────────────────────────┘                        │
  │                     │                                      │
  │     ┌───────────────┼───────────────┐                      │
  │     ▼               ▼               ▼                      │
  │  ┌────────┐   ┌──────────┐   ┌──────────┐                 │
  │  │Synthetic│   │Real IG   │   │Engagement│                 │
  │  │Training │   │Insights  │   │Based     │                 │
  │  │(Gravity)│   │(API)     │   │(Comments)│                 │
  │  └────────┘   └──────────┘   └──────────┘                 │
  │  3 DATA SOURCES FOR GNN TRAINING                           │
  └─────────────────────────────────────────────────────────────┘
```

---

## PHASE 1: IDENTITY EXTRACTION

### What Happens
User uploads a product image. GPT-4o Vision analyzes it and extracts a structured "Visual DNA" — the product's soul. This gets stored in Supabase with a 1536-dim vector embedding for similarity search.

### Files Involved
| File | Role |
|------|------|
| `backend/app/agents/vision_dna.py` | VisionDNAAgent - GPT-4o Vision analysis, embedding generation |
| `backend/app/services/identity_vault.py` | IdentityVault - Supabase storage, pgvector similarity search |

### Data Flow
```
User Image (JPG/PNG)
    │
    ▼
GPT-4o Vision API
    │
    ▼
Visual DNA JSON:
{
  "product_name": "sleek thin laptop with a large display",
  "materials": {"primary": "metal", "finish": "matte"},
  "colors": {"primary": "#C0C0C0", "secondary": "#333333"},
  "geometry": {"shape": "rectangular", "edges": "rounded", "thickness": "ultra-thin"},
  "distinctive_features": ["edge-to-edge display", "minimal bezels", "compact keyboard"],
  "identity_fingerprint": "A modern ultra-thin metallic laptop..."
}
    │
    ▼
Azure OpenAI Embedding API → 1536-dim vector
    │
    ▼
Supabase PostgreSQL (identity_vault table, pgvector)
```

### APIs Used
| API | Cost | Purpose |
|-----|------|---------|
| Azure OpenAI GPT-4o Vision | ~$0.01/image | Analyze product image |
| Azure OpenAI Embeddings | ~$0.0001/call | Generate 1536-dim vector |
| Supabase PostgreSQL | FREE tier | Store DNA + vector |

---

## PHASE 2: COMPETITIVE INTELLIGENCE

### What Happens
Tavily Search finds the top-performing competitor content for our topic. If it's a YouTube video, we extract the transcript. If it's a blog, Jina Reader converts it to clean text. Then GPT-4o deconstructs the competitor's strategy into a structured "Competitor DNA" — finding their hook, triggers, and most importantly, their **missing gaps**.

### Files Involved
| File | Role |
|------|------|
| `competitor_analysis.py` | TavilySearch, ContentExtractor, CompetitorAnalyst classes |
| `demo_competitor_dna.py` | End-to-end demo script |

### Data Flow
```
Topic: "Best High Performance Laptop for Creatives 2025"
    │
    ▼
Tavily Search API → Top competitor URL
    │
    ├─── YouTube video? → YouTubeTranscriptApi().fetch(video_id)
    │                      → Timestamped transcript text
    │
    └─── Blog/Article? → Jina Reader (https://r.jina.ai/URL)
                          → Clean markdown text
    │
    ▼
GPT-4o Analysis (Content Strategist prompt)
    │
    ▼
Competitor DNA JSON:
{
  "hook_strategy": "Budget scenario ($500) with specific needs",
  "structure_outline": ["Intro", "Product A review", "Product B review", "Verdict"],
  "psychological_triggers": ["FOMO", "Authority", "Greed", "Practicality"],
  "keyword_clusters": ["graphic design laptops", "budget laptops", ...],
  "missing_gaps": [
    "No software compatibility (Adobe, Figma)",     ← OUR OPPORTUNITY
    "No benchmark data or performance metrics",      ← OUR OPPORTUNITY
    "No future-proofing considerations",             ← OUR OPPORTUNITY
    "No multi-creative audience appeal"              ← OUR OPPORTUNITY
  ],
  "tone_voice": "Practical, conversational, first-person"
}
```

### APIs Used
| API | Cost | Purpose |
|-----|------|---------|
| Tavily Search | FREE (1000/mo) | Find top competitor content |
| YouTube Transcript API | FREE (Python lib) | Extract video transcripts |
| Jina Reader | FREE (no key) | Extract blog/article text |
| Azure OpenAI GPT-4o | ~$0.04/call | Deconstruct competitor strategy |

---

## PHASE 3: CONTENT CREATION

### What Happens
GPT-4o combines our Visual DNA + Competitor Gaps + Market Data to generate content that strategically outranks competitors. The content specifically fills the gaps competitors missed while using their proven structure.

For video content, the system additionally creates a motion scaffold (camera movements, transitions) and renders frames.

### Files Involved
| File | Role |
|------|------|
| `competitor_analysis.py` | CompetitorAnalyst.generate_superior_content() |
| `backend/app/agents/orchestrator.py` | ContentNode - script/storyboard generation |
| `backend/app/agents/orchestrator.py` | MotionNode - 4D depth skeleton, camera paths |
| `backend/app/agents/spatiotemporal.py` | Spatiotemporal scaffolding |
| `backend/app/agents/neural_render.py` | Frame-by-frame neural rendering |

### Data Flow
```
Visual DNA + Competitor DNA + Market Research
    │
    ▼
GPT-4o (World-Class Copywriter prompt)
    │
    ├─── Strategy: Steal their Structure (it works)
    ├─── Strategy: Improve their Hook
    ├─── Strategy: Fill their 'Missing Gaps' (Adversarial Value)
    └─── Strategy: Use OUR Brand Voice/Visual Identity
    │
    ▼
Generated Content:
  - LinkedIn Post (long-form thought leadership)
  - Mentions specific product features from Visual DNA
  - Fills every gap the competitor missed
  - Uses competitor's proven psychological triggers
    │
    ▼ (For video workflow only)
    │
Motion Scaffold → Camera paths, transitions, depth maps
    │
    ▼
Neural Renderer → Rendered video file (MP4)
```

### APIs Used
| API | Cost | Purpose |
|-----|------|---------|
| Azure OpenAI GPT-4o | ~$0.06/call | Generate superior content |
| Azure OpenAI GPT-4o | ~$0.04/call | Generate motion scaffold (video only) |

---

## PHASE 4: DISTRIBUTION (PUBLISHING)

### What Happens
The generated content/video gets published to Instagram via the Graph API. A unique campaign ID is generated, a tracking link is created, and the link is appended to the caption. A Campaign record is stored in the database.

### Files Involved
| File | Role |
|------|------|
| `backend/app/agents/publish_node.py` | PublishNode - orchestrator stage for publishing |
| `backend/app/services/publishing_service.py` | PublishingService - Instagram/LinkedIn API calls |
| `backend/app/services/tracking/instagram/publisher.py` | InstagramPublisher - Meta Graph API calls |
| `backend/app/services/tracking/link_generator.py` | LinkGenerator - campaign ID + tracking URL |

### Data Flow
```
Content/Video + Caption
    │
    ▼
LinkGenerator.generate_campaign_id() → "ig_a1b2c3d4"
LinkGenerator.generate_tracking_link() → "https://yourdomain.com/p/ig_a1b2c3d4"
    │
    ▼
Caption = original_caption + "\n\n" + tracking_link
    │
    ▼
Instagram Graph API (POST /media + POST /media_publish)
    │
    ▼
Response: { post_id: "17841478698032119_..." }
    │
    ▼
Database: Campaign record created
{
  campaign_id: "ig_a1b2c3d4",
  platform: "instagram",
  post_id: "17841478698032119_...",
  tracking_link: "https://yourdomain.com/p/ig_a1b2c3d4",
  publish_time: "2026-02-11T14:00:00Z"
}
```

### APIs Used
| API | Cost | Purpose |
|-----|------|---------|
| Instagram Graph API (Meta) | FREE | Publish posts |
| Supabase PostgreSQL | FREE | Store campaign records |

---

## PHASE 5: ANALYTICS & TRACKING

### What Happens
After publishing, the system tracks how content spreads geographically using THREE different data collection methods:

### Method 1: Click Tracking (Our Endpoint)
When a user clicks the tracking link in the caption, our FastAPI endpoint captures their IP, converts it to city/country, and logs it. The IP is immediately discarded (privacy-safe).

### Method 2: Instagram Insights API (Official)
Every 30 minutes, we fetch Instagram's built-in insights which provide city-level reach and impression data. This is the primary data source.

### Method 3: Engagement-Based Tracking (Inferred)
We analyze who liked/commented on the post, check their profile locations, and infer geographic spread from engagement timestamps. No user interaction required.

### Files Involved
| File | Role |
|------|------|
| `backend/app/api/v1/tracking_endpoint.py` | FastAPI endpoint: `/p/{campaign_id}` → IP → City → Log |
| `backend/app/services/analytics_service.py` | AnalyticsService - fetch IG insights, dashboard queries |
| `engagement_spread_tracker.py` | EngagementSpreadTracker - likes/comments → location inference |
| `backend/app/services/tracking/analytics/spike_detector.py` | SpikeDetector - detect engagement spikes per city |
| `backend/app/services/tracking/analytics/spread_graph.py` | SpreadGraph - build geographic spread graph from clicks |

### Data Flow - Click Tracking
```
User clicks tracking link in bio/caption
    │
    ▼
FastAPI Endpoint: GET /p/ig_a1b2c3d4
    │
    ▼
IP Address → ip-api.com (FREE) → { city: "Mumbai", country: "India" }
    │
    ▼  (IP deleted immediately)
Database: ClickEvent record
{
  campaign_id: "ig_a1b2c3d4",
  city: "Mumbai",
  country: "India",
  timestamp: "2026-02-11T15:23:00Z"
}
    │
    ▼
User redirected to → https://www.instagram.com/itsfunyyyyyyyy/
```

### Data Flow - Instagram Insights
```
Scheduler (every 30 min)
    │
    ▼
Instagram Graph API: GET /{post_id}/insights
    │
    ▼
Response:
{
  "impressions": 15000,
  "reach": 8500,
  "audience_city": {
    "Mumbai": 3200,
    "Delhi": 2100,
    "Bangalore": 1800,
    "Pune": 1400
  }
}
    │
    ▼
Database: InsightSnapshot records (per city)
```

### Data Flow - Engagement Spread
```
Instagram Graph API: GET /{post_id}/comments
Instagram Graph API: GET /{post_id}/likes
    │
    ▼
For each commenter/liker:
  → Check profile for location
  → Scan comment text for city mentions
  → Record timestamp + inferred city
    │
    ▼
Spread Pattern:
[
  { from: "Pune",      to: "Mumbai",    time: "2h after post" },
  { from: "Mumbai",    to: "Delhi",     time: "4h after post" },
  { from: "Delhi",     to: "Bangalore", time: "6h after post" }
]
```

### Analytics Dashboard
```
AnalyticsService.get_analytics_dashboard():
{
  "total_campaigns": 12,
  "total_clicks": 4500,
  "total_reach": 85000,
  "top_cities": ["Mumbai", "Delhi", "Bangalore"],
  "spike_cities": ["Pune"],       ← SpikeDetector found abnormal growth
  "spread_graph": {
    "nodes": ["Mumbai", "Delhi", "Bangalore", "Pune"],
    "edges": [
      {"from": "Mumbai", "to": "Delhi", "confidence": 0.8},
      {"from": "Delhi", "to": "Bangalore", "confidence": 0.6}
    ],
    "trending": "Pune",            ← Most recent spike
    "emerging": "Bangalore"        ← Second most recent
  }
}
```

### APIs Used
| API | Cost | Purpose |
|-----|------|---------|
| ip-api.com | FREE (45 req/min) | IP → City geolocation |
| Instagram Graph API | FREE | Post insights, comments, likes |
| Supabase PostgreSQL | FREE | Store click events, insights |

---

## PHASE 6: GNN VIRAL SPREAD PREDICTION

### What Happens
This is the predictive intelligence layer. We model how content spreads between cities as a **graph problem**. Cities are nodes, spread connections are edges. A Graph Neural Network (GNN) learns the "physics of viral spread" and predicts WHERE content will go next.

### THREE Data Sources for GNN Training

#### Source 1: Synthetic Data (Gravity Model) → READY
We generate 1000+ simulated viral campaigns using a gravity model:
```
Spread Probability = (Weight_CityA × Weight_CityB) / Distance^1.5
```

11 Indian tech hubs + Dubai, each with population/tech-density weights.

#### Source 2: Real Instagram Insights → BUILT (needs data)
Every 30 minutes, we fetch city-level impressions from Instagram and build the real graph:
- New city appears → create GraphNode
- City B appears after City A → create GraphEdge
- Every hour → create ViralSpreadSnapshot

#### Source 3: Engagement-Based Spread → BUILT (needs data)
Track likers/commenters → infer locations → build spread timeline.

### Files Involved
| File | Role |
|------|------|
| `generate_synthetic_gnn_data.py` | Gravity model, generates 1000 training cascades |
| `collect_gnn_training_data.py` | InstagramInsightsCollector - real IG data → graph |
| `run_gnn_data_collection.py` | GNNDataCollector - automated 30-min collection cycles |
| `engagement_spread_tracker.py` | EngagementSpreadTracker - engagement → locations |
| `backend/app/db/gnn_models.py` | GraphNode, GraphEdge, ViralSpreadSnapshot DB models |

### Database Schema
```sql
-- NODES: Each city where content was viewed
TABLE graph_nodes (
  id              UUID PRIMARY KEY,
  city            VARCHAR NOT NULL,
  country         VARCHAR NOT NULL,
  campaign_id     VARCHAR REFERENCES campaigns,
  impressions     INTEGER DEFAULT 0,
  reach           INTEGER DEFAULT 0,
  engagement      INTEGER DEFAULT 0,
  saves           INTEGER DEFAULT 0,
  shares          INTEGER DEFAULT 0,
  first_seen      TIMESTAMP,           -- When this city first saw the content
  growth_rate     FLOAT DEFAULT 0.0,   -- Impressions growth rate
  engagement_rate FLOAT DEFAULT 0.0,   -- engagement / reach
  virality_score  FLOAT DEFAULT 0.0    -- Calculated score
);

-- EDGES: Spread connections between cities
TABLE graph_edges (
  id                    UUID PRIMARY KEY,
  campaign_id           VARCHAR REFERENCES campaigns,
  from_city             VARCHAR NOT NULL,
  to_city               VARCHAR NOT NULL,
  time_delta            FLOAT NOT NULL,  -- Seconds between first impressions
  weight                FLOAT DEFAULT 1.0,
  confidence            FLOAT DEFAULT 0.5,
  from_city_impressions INTEGER DEFAULT 0,
  to_city_impressions   INTEGER DEFAULT 0,
  transfer_rate         FLOAT DEFAULT 0.0  -- to_impressions / from_impressions
);

-- SNAPSHOTS: Time-series state of the graph
TABLE viral_spread_snapshots (
  id                     UUID PRIMARY KEY,
  campaign_id            VARCHAR REFERENCES campaigns,
  snapshot_time          TIMESTAMP,
  hours_since_publish    FLOAT NOT NULL,
  total_nodes            INTEGER DEFAULT 0,  -- Active cities
  total_edges            INTEGER DEFAULT 0,  -- Spread connections
  total_impressions      INTEGER DEFAULT 0,
  total_reach            INTEGER DEFAULT 0,
  total_engagement       INTEGER DEFAULT 0,
  geographic_spread      FLOAT DEFAULT 0.0,  -- Distance covered
  velocity               FLOAT DEFAULT 0.0,  -- Cities/hour
  trending_city          VARCHAR,
  emerging_cities        VARCHAR,             -- JSON list
  graph_density          FLOAT DEFAULT 0.0,
  avg_node_degree        FLOAT DEFAULT 0.0,
  clustering_coefficient FLOAT DEFAULT 0.0
);
```

### Synthetic Data Generation (Gravity Model)
```
11 Cities defined:
  Mumbai    (weight: 1.00, Tier 1)
  Delhi     (weight: 0.95, Tier 1)
  Bangalore (weight: 0.90, Tier 1)
  Hyderabad (weight: 0.85, Tier 1)
  Chennai   (weight: 0.80, Tier 1)
  Pune      (weight: 0.70, Tier 2)
  Gurgaon   (weight: 0.60, Tier 2)
  Ahmedabad (weight: 0.60, Tier 2)
  Noida     (weight: 0.50, Tier 3)
  Dubai     (weight: 0.50, Tier 2)  ← International
  Indore    (weight: 0.40, Tier 3)

Gravity Formula:
  P(spread A→B) = (Weight_A × Weight_B) / Distance(A,B)^1.5

Simulation:
  - Start from random city
  - Each timestep: try to infect neighboring cities based on probability
  - Record: which cities activated, in what order, via which path
  - Generate 1000 cascades

Output: gnn_synthetic_training_data.json
  [
    {
      "campaign_id": "sim_a1b2c3d4",
      "start_city": "Pune",
      "nodes_hit": ["Pune", "Mumbai", "Delhi", "Bangalore"],
      "edges": [
        {"from": "Pune", "to": "Mumbai", "step": 1, "probability": 0.85},
        {"from": "Mumbai", "to": "Delhi", "step": 2, "probability": 0.72},
        {"from": "Mumbai", "to": "Bangalore", "step": 3, "probability": 0.61}
      ],
      "total_steps": 5
    },
    ... (999 more)
  ]
```

### Real Data Collection Flow
```
Post Published to Instagram
    │
    ▼   (Every 30 minutes - automated by scheduler)
    │
    ├── GNNDataCollector.fetch_post_audience_cities(post_id)
    │   → Instagram API: GET /{post_id}/insights?metric=audience_city
    │   → Returns: {"Mumbai": 3200, "Delhi": 2100, ...}
    │
    ├── GNNDataCollector.update_graph_nodes(campaign_id, city_data)
    │   → For each city: CREATE or UPDATE GraphNode
    │   → Track: first_seen, impressions, reach, growth_rate
    │
    ├── GNNDataCollector.detect_spread_edges(campaign_id)
    │   → Sort nodes by first_seen timestamp
    │   → If City B appeared after City A:
    │       → Create GraphEdge(from=A, to=B, time_delta=seconds_between)
    │   → Calculate: weight, confidence, transfer_rate
    │
    └── GNNDataCollector.create_snapshot(campaign_id)
        → Capture: total_nodes, total_edges, velocity, trending_city
        → Store as ViralSpreadSnapshot
        → This becomes one training row for the GNN
```

### What the GNN Will Predict (Once Trained)
```
INPUT: Current graph state at time T
  - Nodes: [Mumbai (3200 views), Pune (1400 views)]
  - Edges: [Pune → Mumbai (1h delta)]
  - Features: growth_rate, engagement_rate, virality_score

OUTPUT: Predicted next state at time T+1
  - Next city to activate: Delhi (85% probability)
  - Estimated impressions in Delhi: 2000
  - Spread velocity: 1.5 cities/hour
  - Final reach estimate: 15,000

BUSINESS USE:
  → "Your post is about to hit Delhi. Delhi audiences respond to
     Authority triggers. Consider boosting with a testimonial."
```

### GNN Training Pipeline Status
| Component | Status | File |
|-----------|--------|------|
| Synthetic training data (1000 cascades) | READY | `generate_synthetic_gnn_data.py` |
| Database schema (nodes, edges, snapshots) | READY | `backend/app/db/gnn_models.py` |
| Real data collector (IG insights) | BUILT | `run_gnn_data_collection.py` |
| Alternative collector (engagement) | BUILT | `engagement_spread_tracker.py` |
| GNN model definition | NOT YET | Need PyTorch Geometric |
| GNN training script | NOT YET | Need training loop |
| Prediction API endpoint | NOT YET | Need FastAPI route |

---

## ALL APIs IN THE SYSTEM

| # | API | Used In | Cost | Status |
|---|-----|---------|------|--------|
| 1 | Azure OpenAI GPT-4o Vision | Phase 1: Image analysis | ~$0.01/img | ACTIVE |
| 2 | Azure OpenAI Embeddings | Phase 1: Vector generation | ~$0.0001/call | ACTIVE |
| 3 | Tavily Search API | Phase 2: Competitor discovery | FREE (1000/mo) | ACTIVE |
| 4 | YouTube Transcript API | Phase 2: Video transcription | FREE (Python lib) | ACTIVE |
| 5 | Jina Reader API | Phase 2: Blog extraction | FREE (no key) | ACTIVE |
| 6 | Azure OpenAI GPT-4o Text | Phase 2+3: Analysis + Generation | ~$0.04-0.06/call | ACTIVE |
| 7 | Brave Search API | Phase 2: Market research (alt) | FREE tier | BUILT |
| 8 | Instagram Graph API (Meta) | Phase 4: Publish posts | FREE | ACTIVE |
| 9 | Instagram Graph API (Meta) | Phase 5: Insights/city data | FREE | ACTIVE |
| 10 | ip-api.com | Phase 5: IP geolocation | FREE (45/min) | ACTIVE |
| 11 | Supabase PostgreSQL + pgvector | Phase 1,4,5,6: All storage | FREE tier | ACTIVE |
| 12 | PyTorch Geometric | Phase 6: GNN model | FREE (local) | NOT YET |

### Total Cost Per Full Run (Image → Published Post → Tracking Started)
```
Phase 1 (Identity):      $0.01  (Vision) + $0.0001 (Embedding)
Phase 2 (Intelligence):  $0.005 (Tavily) + $0.00 (YouTube/Jina) + $0.04 (Analysis)
Phase 3 (Creation):      $0.06  (Content generation)
Phase 4 (Distribution):  $0.00  (Instagram API free)
Phase 5 (Analytics):     $0.00  (All free APIs)
Phase 6 (GNN):           $0.00  (Local computation)
─────────────────────────────────────────
TOTAL:                   ~$0.12 per complete run
```

---

## COMPLETE FILES INDEX

### Phase 1: Identity
| File | Lines | Purpose |
|------|-------|---------|
| `backend/app/agents/vision_dna.py` | 596 | VisionDNAAgent: GPT-4o Vision → Visual DNA + embedding |
| `backend/app/services/identity_vault.py` | 452 | IdentityVault: Supabase storage, similarity search |

### Phase 2: Intelligence
| File | Lines | Purpose |
|------|-------|---------|
| `competitor_analysis.py` | 312 | TavilySearch, ContentExtractor, CompetitorAnalyst |
| `demo_competitor_dna.py` | 140 | End-to-end demo script |

### Phase 3: Content Creation
| File | Lines | Purpose |
|------|-------|---------|
| `backend/app/agents/orchestrator.py` | 1120 | LangGraph state machine (all stages) |
| `backend/app/agents/spatiotemporal.py` | ~500 | Motion scaffold generation |
| `backend/app/agents/neural_render.py` | ~2000 | Video rendering engine |

### Phase 4: Distribution
| File | Lines | Purpose |
|------|-------|---------|
| `backend/app/agents/publish_node.py` | 148 | PublishNode orchestrator stage |
| `backend/app/services/publishing_service.py` | 175 | Instagram/LinkedIn publishing |
| `backend/app/services/tracking/instagram/publisher.py` | ~100 | Meta Graph API calls |
| `backend/app/services/tracking/link_generator.py` | 27 | Campaign ID + tracking URL |

### Phase 5: Analytics & Tracking
| File | Lines | Purpose |
|------|-------|---------|
| `backend/app/api/v1/tracking_endpoint.py` | 110 | FastAPI click tracking endpoint |
| `backend/app/services/analytics_service.py` | 268 | Analytics dashboard, IG insights fetcher |
| `engagement_spread_tracker.py` | 197 | Engagement-based geographic tracking |
| `backend/app/services/tracking/analytics/spike_detector.py` | 40 | Detect engagement spikes per city |
| `backend/app/services/tracking/analytics/spread_graph.py` | 67 | Build spread graph from click data |

### Phase 6: GNN Prediction
| File | Lines | Purpose |
|------|-------|---------|
| `generate_synthetic_gnn_data.py` | 138 | Gravity model synthetic data (1000 cascades) |
| `collect_gnn_training_data.py` | 328 | Instagram insights → graph data collector |
| `run_gnn_data_collection.py` | 447 | Automated 30-min collection cycles |
| `backend/app/db/gnn_models.py` | 172 | GraphNode, GraphEdge, ViralSpreadSnapshot models |

### Support
| File | Lines | Purpose |
|------|-------|---------|
| `backend/app/services/scheduler.py` | ~100 | Scheduled task runner |
| `view_all_logs.py` | ~200 | View all analytics data |
| `view_gnn_data.py` | ~200 | View GNN graph data |

---

## HOW TO IMPROVE FURTHER

### 1. TRAIN THE GNN MODEL (Completes Phase 6)
**What:** Write PyTorch Geometric model + training loop using synthetic data.
**Impact:** Enables real-time viral prediction.
**Effort:** 3-4 days.
```
Step 1: pip install torch torch-geometric
Step 2: Define GCN/GAT model architecture
Step 3: Train on 1000 synthetic cascades
Step 4: Validate on held-out set
Step 5: Create prediction API endpoint
```

### 2. CONTENT ATOMIZER (6x Output)
**What:** One analysis → 6 format-specific outputs (LinkedIn, Instagram, Twitter, Blog, Reel script, Carousel).
**Impact:** 6x content from same cost.
**Effort:** 1 day.

### 3. BRAND VOICE FINGERPRINT
**What:** Store user's writing samples, extract their voice DNA, constrain generation to sound like them.
**Impact:** Content feels authentic, not AI.
**Effort:** 1-2 days.

### 4. WATCHTOWER AGENT (Auto-Monitor)
**What:** Daily scheduler runs Tavily for user's keywords, alerts when new competitor content appears, auto-generates counter-content.
**Impact:** Stay ahead permanently.
**Effort:** 2-3 days.

### 5. FEEDBACK LOOP (Self-Learning)
**What:** After 48h, fetch post metrics. Store what worked. Next generation uses past performance as context.
**Impact:** System gets smarter over time.
**Effort:** 3-4 days.

### 6. GNN → CONTENT BRIDGE
**What:** When GNN predicts "post is spreading to Delhi", auto-generate Delhi-optimized content variant.
**Impact:** Location-targeted content strategy.
**Effort:** 2 days (after GNN is trained).

---

## QUICK COMMANDS

```powershell
# Run competitor DNA analysis (full demo)
$env:PYTHONIOENCODING='utf-8'; python demo_competitor_dna.py

# Generate synthetic GNN training data
$env:PYTHONIOENCODING='utf-8'; python generate_synthetic_gnn_data.py

# Collect real Instagram insights for GNN
$env:PYTHONIOENCODING='utf-8'; python run_gnn_data_collection.py

# Track engagement spread (no clicks needed)
$env:PYTHONIOENCODING='utf-8'; python engagement_spread_tracker.py

# View all analytics and logs
$env:PYTHONIOENCODING='utf-8'; python view_all_logs.py

# View GNN graph data
$env:PYTHONIOENCODING='utf-8'; python view_gnn_data.py
```

---

## THE BIG PICTURE

**What makes Catalyst Nexus different from every other tool:**

```
Generic AI Tool:    Image → AI Caption → Post → Hope for the best
                    (No strategy, no intelligence, no learning)

Catalyst Nexus:     Image → Visual DNA → Competitor Deconstruction
                    → Gap Exploitation → Strategic Content
                    → Publish → Track Geographic Spread
                    → Build Graph → Train GNN → Predict Viral Path
                    → Feed Predictions Back Into Content Strategy
                    → COMPOUND ADVANTAGE OVER TIME

The key insight: We don't just CREATE content.
We CREATE content that STRATEGICALLY OUTRANKS competitors
and then LEARN from how it spreads to get BETTER next time.

This is a CLOSED LOOP. Every post makes the system smarter.
```
