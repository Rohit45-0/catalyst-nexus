# 🚀 Catalyst Nexus Core

**AI-Powered Video Generation & Identity Management Platform**

Catalyst Nexus is an advanced backend system that orchestrates AI agents for video generation, identity extraction, and neural rendering. Built with FastAPI and powered by LangGraph for intelligent task orchestration.

---

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [API Documentation](#-api-documentation)
- [Configuration](#-configuration)
- [Development](#-development)
- [Roadmap](#-roadmap)

---

## ✨ Features

### Core Capabilities
- **Vision DNA Agent**: Extract and preserve identity features from images/videos
- **Spatiotemporal Engine**: Motion scaffolding and temporal consistency control
- **Neural Renderer**: Hybrid API/local rendering with quality optimization
- **Orchestrator**: LangGraph-powered state machine for complex workflows

### Platform Features
- 🔐 JWT-based authentication with role management
- 📁 Project & asset management system
- 🗄️ Identity Vault for persistent character storage
- ⚡ Async job processing with real-time status updates
- ☁️ Multi-cloud storage support (S3, Supabase)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Gateway (FastAPI)                     │
├─────────────────────────────────────────────────────────────────┤
│  Auth  │  Projects  │  Jobs  │  Vault  │  Webhooks              │
├─────────────────────────────────────────────────────────────────┤
│                     Core Engine (Routing)                        │
├─────────────────────────────────────────────────────────────────┤
│                    🧠 AI Agent Layer                             │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │Vision DNA│  │Spatiotemporal│  │Neural Render │               │
│  └──────────┘  └──────────────┘  └──────────────┘               │
│                    ↑                                             │
│              ┌─────┴─────┐                                       │
│              │Orchestrator│ (LangGraph State Machine)            │
│              └───────────┘                                       │
├─────────────────────────────────────────────────────────────────┤
│  PostgreSQL  │  Redis Cache  │  S3/Supabase Storage             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker (optional)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/catalyst-nexus-core.git
cd catalyst-nexus-core

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run database migrations
python -m scripts.migrate

# Start the server
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker Deployment

```bash
docker-compose up -d
```

---

## 📚 API Documentation

Once running, access the interactive API docs:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | User registration |
| POST | `/api/v1/auth/login` | JWT authentication |
| GET | `/api/v1/projects` | List user projects |
| POST | `/api/v1/jobs/generate` | Trigger AI generation |
| GET | `/api/v1/vault/identities` | List stored identities |

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `SECRET_KEY` | JWT signing key | Required |
| `OPENAI_API_KEY` | OpenAI API key for agents | Required |
| `AWS_S3_BUCKET` | S3 bucket for storage | Optional |

See `.env.example` for complete list.

---

## 🛠️ Development

### Project Structure

```
catalyst-nexus-core/
├── backend/
│   ├── app/
│   │   ├── api/v1/        # REST endpoints
│   │   ├── agents/        # AI agent modules
│   │   ├── core/          # Business logic
│   │   ├── db/            # Data layer
│   │   └── utils/         # Helpers
│   ├── tests/             # Pytest suite
│   └── scripts/           # Management scripts
└── infrastructure/        # Deployment configs
```

### Running Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=backend --cov-report=html

# Specific test file
pytest backend/tests/test_auth.py -v
```

### Code Quality

```bash
# Linting
ruff check .

# Formatting
black .

# Type checking
mypy backend/
```

---

## 🗺️ Roadmap

### Phase 1: Foundation (Current)
- [x] FastAPI backend structure
- [x] Authentication system
- [x] Database models
- [ ] Basic agent framework

### Phase 2: AI Agents
- [ ] Vision DNA implementation
- [ ] Spatiotemporal engine
- [ ] Neural renderer integration
- [ ] LangGraph orchestrator

### Phase 3: Scale
- [ ] Distributed job processing
- [ ] Multi-region deployment
- [ ] Advanced caching layer
- [ ] Real-time WebSocket updates

### Phase 4: Enterprise
- [ ] Team collaboration features
- [ ] Advanced analytics
- [ ] Custom model fine-tuning
- [ ] On-premise deployment option

---

## 📄 License

Copyright © 2026 Catalyst Nexus. All rights reserved.

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

**Built with ❤️ using FastAPI, LangGraph, and cutting-edge AI**
