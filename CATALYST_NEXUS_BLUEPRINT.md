# 💎 Catalyst Nexus: Technical Master Blueprint (v1.0)

---

## 1. Project Overview

**Objective:** Build an enterprise-grade AI Video Marketing SaaS capable of generating high-fidelity, brand-consistent video ads at scale using a **"Motion-First" Neural Rendering** pipeline.

---

## 2. Core Architecture: The "Nexus" Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CATALYST NEXUS FLOW                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐     │
│   │  IDENTITY VAULT  │───▶│ TEMPORAL SCAFFOLD │───▶│ HYBRID RENDERING │     │
│   │                  │    │                  │    │                  │     │
│   │ • Geometric Lock │    │ • 4D Depth       │    │ • Serverless GPU │     │
│   │ • Tensor Embed   │    │ • Motion Skeleton│    │ • Sora-2/Veo API │     │
│   │ • pgvector Store │    │ • Zero-shot      │    │ • Hi-Fi Refine   │     │
│   └──────────────────┘    └──────────────────┘    └──────────────────┘     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Identity Vault
Store a mathematical **"Geometric Lock"** (Tensor Embedding) of products in Supabase using `pgvector`.

### 2.2 Temporal Scaffolding
Generate **4D Depth Skeletons** (Motion) before pixels to ensure zero-shot product consistency.

### 2.3 Hybrid Rendering
Use **Serverless GPUs** (SkyReels-V2) for base renders and **Sora-2/Veo APIs** for high-fidelity refinement.

---

## 3. Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Backend** | FastAPI | High-performance async API framework |
| **ORM** | SQLAlchemy 2.0 (Async) | Database operations |
| **Validation** | Pydantic v2 | Data validation & settings |
| **Database** | Supabase (PostgreSQL) | Primary data store |
| **Vector DB** | pgvector | Embedding storage & similarity search |
| **AI Orchestration** | LangGraph | Agentic state machines |
| **LLM** | Azure OpenAI (GPT-4o) | Vision analysis & content generation |
| **Video Gen** | Sora-2, SkyReels-V2 | Neural video rendering |
| **Search** | Brave Search API | Market research |
| **Image Gen** | ByteZ API | Image generation |
| **Publishing** | Meta/LinkedIn APIs | Social media distribution |

---

## 4. Directory Structure

```
catalyst-nexus-core/
├── .env                          # Environment variables
├── CATALYST_NEXUS_BLUEPRINT.md   # This file
├── requirements.txt              # Python dependencies
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI entry point
│   │   │
│   │   ├── api/v1/               # API Routes
│   │   │   ├── auth.py           # Authentication endpoints
│   │   │   ├── projects.py       # Project management
│   │   │   ├── vault.py          # Identity Vault operations
│   │   │   └── jobs.py           # AI generation jobs
│   │   │
│   │   ├── agents/               # AI Agent Logic
│   │   │   ├── vision_dna.py     # Identity extraction (GPT-4o Vision)
│   │   │   ├── spatiotemporal.py # Motion scaffolding
│   │   │   ├── neural_render.py  # Hybrid rendering pipeline
│   │   │   └── orchestrator.py   # LangGraph state machine
│   │   │
│   │   ├── core/                 # Core Business Logic
│   │   │   ├── config.py         # Pydantic Settings
│   │   │   ├── security.py       # JWT & Auth logic
│   │   │   └── engine.py         # Task routing
│   │   │
│   │   ├── db/                   # Database Layer
│   │   │   ├── base.py           # SQLAlchemy session setup
│   │   │   ├── models.py         # ORM models (with pgvector)
│   │   │   └── schemas.py        # Pydantic schemas
│   │   │
│   │   └── utils/                # Utilities
│   │       ├── video_utils.py    # Video processing
│   │       └── storage.py        # Cloud storage helpers
│   │
│   ├── tests/                    # Automated Tests
│   │   ├── conftest.py           # Pytest fixtures
│   │   ├── test_api.py           # API endpoint tests
│   │   ├── test_vault.py         # Identity Vault tests
│   │   └── test_agents.py        # Agent logic tests
│   │
│   └── scripts/                  # Management Scripts
│       ├── init_db.py            # Database initialization
│       └── seed_data.py          # Sample data seeding
│
└── infrastructure/               # Deployment
    ├── docker/
    └── azure/
```

---

## 5. Development Roadmap for Co-pilot

### Phase A: The Foundation ✅ (Complete)

- [x] Implement `core/config.py` using Pydantic Settings
- [x] Implement `db/models.py` with `ProductEmbedding` table featuring `vector(1536)`
- [x] Setup `db/base.py` session management with `get_db` dependency
- [x] Initialize database tables in Supabase

### Phase B: Identity Intelligence ✅ (Complete)

- [x] Build `agents/vision_dna.py`:
  - GPT-4o-Vision integration for material/lighting/structure extraction
  - OpenAI Embeddings for 1536-dim "Geometric Lock" vector
  - Dataclasses: `MaterialProperties`, `LightingConditions`, `StructuralAnalysis`, `VisualDNA`
  - Methods: `extract_product_identity()`, `compare_identities()`, `merge_identities()`
- [x] Create `api/v1/vault.py`:
  - `POST /vault/products` - Extract & store product identity
  - `GET /vault/products/{id}` - Retrieve product by ID
  - `GET /vault/products/{project_id}/versions` - Get all versions
  - `POST /vault/products/search` - Vector similarity search (pgvector)
  - `DELETE /vault/products/{id}` - Soft/hard delete
  - `PATCH /vault/products/{id}/activate` - Reactivate deleted
  - `GET /vault/health` - Health check
- [x] Create test suites:
  - `tests/test_vision_dna.py` - Agent unit tests
  - `tests/test_vault.py` - API endpoint tests

### Phase C: Agentic Orchestration ✅ (Complete)

- [x] Build the LangGraph state machine in `agents/orchestrator.py`
- [x] Implement the full pipeline:
  ```
  Research → Content → Motion → Render → Finalize
  ```
- [x] State management with `NexusState` TypedDict
- [x] Node implementations:
  - `ResearchNode` - Market analysis with Brave Search API
  - `ContentNode` - VisionDNA extraction + GPT-4o script generation
  - `MotionNode` - 4D motion scaffold creation
  - `RenderNode` - Hybrid neural rendering settings
  - `FinalizeNode` - Job completion and cleanup
- [x] Dynamic routing based on workflow type
- [x] Checkpoint/resume with `MemorySaver`
- [x] Error handling and retry logic
- [x] Progress tracking with stage messages
- [x] Job management: `run()`, `get_status()`, `list_jobs()`, `cancel_job()`
- [x] Create test suite: `tests/test_orchestrator.py`

### Phase D: Rendering Pipeline

- [ ] Integrate SkyReels-V2 for base renders
- [ ] Implement Sora-2/Veo API connectors
- [ ] Build quality assessment & refinement loop

### Phase E: Publishing & Distribution

- [ ] LinkedIn API integration
- [ ] Meta (Facebook/Instagram) API integration
- [ ] Automated scheduling & analytics

---

## 6. Key Database Models

### ProductEmbedding (Identity Vault)

```python
class ProductEmbedding(Base):
    __tablename__ = "product_embeddings"
    
    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    version: Mapped[int] = mapped_column(Integer, default=1)
    
    # The Geometric Lock - 1536-dim vector from OpenAI
    embedding: Mapped[Vector] = mapped_column(Vector(1536))
    
    # Material & Lighting extracted by GPT-4o-Vision
    material_properties: Mapped[dict] = mapped_column(JSON)
    lighting_conditions: Mapped[dict] = mapped_column(JSON)
    
    # Metadata
    source_images: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime]
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
```

---

## 7. Testing Instructions

### Unit Tests
- Generate Pytest suites for every API endpoint
- Mock all external AI API calls to ensure database logic is tested without consuming credits

### Integration Tests
- Test complete flows with test database
- Verify vector similarity search accuracy

### Example Test Structure
```python
# tests/test_vault.py
@pytest.mark.asyncio
async def test_store_product_embedding(client, mock_openai):
    """Test storing a product's geometric lock."""
    mock_openai.return_value = [0.1] * 1536  # Mock embedding
    
    response = await client.post("/api/v1/vault/products", json={
        "name": "Test Product",
        "images": ["https://example.com/image.jpg"]
    })
    
    assert response.status_code == 201
    assert "embedding_id" in response.json()
```

---

## 8. How to Use This Blueprint with Co-pilot

### Initial Context
```
I am building Catalyst Nexus based on this blueprint. 
Start by implementing the backend/app/db/models.py and 
backend/app/db/base.py as defined.
```

### Iterative Build
```
Now that the database is ready, write the VisionDNAAgent 
in backend/app/agents/vision_dna.py to handle the identity extraction.
```

### Testing
```
Write a pytest file in backend/tests/ to verify this logic works.
```

---

## 9. API Reference

### Identity Vault Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/vault/products` | Create product embedding |
| `GET` | `/api/v1/vault/products/{id}` | Get product by ID |
| `GET` | `/api/v1/vault/products/{id}/versions` | Get all versions |
| `POST` | `/api/v1/vault/products/search` | Vector similarity search |

### Job Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/jobs/generate` | Start generation job |
| `GET` | `/api/v1/jobs/{id}` | Get job status |
| `GET` | `/api/v1/jobs/{id}/result` | Get completed result |

---

## 10. Environment Variables Required

```env
# Database
DATABASE_URL=postgresql://...

# Azure OpenAI
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=...
AZURE_DEPLOYMENT_NAME=gpt-4o

# Security
SECRET_KEY=...

# External APIs (Phase D+)
SORA_API_KEY=...
SKIREELS_API_KEY=...
BRAVE_API_KEY=...
BYTEZ_API_KEY=...
```

---

**Built for Scale. Engineered for Excellence. Ready to Crush It! 🚀**
