# TRACE-NET

## Explanable Criminal Network & Investigation Intelligence Platform

> **SIH26189 — AI-Powered Criminal Network Analysis System**
> Ministry of Home Affairs | Theme: Blockchain & Cybersecurity | Type: Software

---

## Project Overview

TRACE-NET is a decision-support and intelligence-analysis system that helps authorized investigators analyze fragmented investigation data, construct interactive criminal-network graphs, surface influential entities, detect suspicious patterns, and present explainable intelligence.

**Important:** This is a decision-support system, not an autonomous system. Every risk score, correlation, and recommendation is a **potential lead requiring human verification**.

---

## Features

- 🔐 **Role-Based Authentication** — Admin, Investigator, Analyst roles with JWT tokens
- 📁 **Case Management** — Create, manage, and track investigation cases
- 📎 **Evidence Management** — Upload files with SHA-256 integrity verification
- 🔍 **Entity Extraction** — Rule-based + NLP extraction from text (phones, emails, IPs, UPIs, vehicles)
- 🧩 **Entity Resolution** — Intelligent deduplication and normalization
- 🔗 **Relationship Engine** — Automatic relationship discovery from evidence
- 📊 **Interactive Network Graph** — Cytoscape.js visualization with centrality analysis
- 🔀 **Cross-Case Correlation** — Weighted scoring across cases
- ⚡ **Suspicious Pattern Detection** — Bridge entities, fan-out, burst activity, multi-case identifiers
- 📈 **Explainable Lead Scoring** — Transparent factors and supporting evidence
- ⏱️ **Timeline Analysis** — Chronological event view
- 📋 **Report Generation** — JSON reports distinguishing facts from inferences
- 🛡️ **Audit Trail** — Complete audit logging of all actions
- 🔎 **Global Search** — Search across cases, entities, and evidence

---

## Architecture

```
TRACE-NET
    |
+---+---+---+
|       |       |
Frontend Backend Storage
|       |       |
React  FastAPI  Files
|       |
|  Service Layer
|       |
+---+---+
|       |       |
NLP    Graph   Scoring
|       |       |
+---+---+       |
|          PostgreSQL
|
Cytoscape.js
```

---

## Tech Stack

### Frontend
- React 18 + TypeScript + Vite
- Tailwind CSS
- React Router v6
- TanStack Query
- Cytoscape.js (network visualization)
- Recharts (analytics charts)

### Backend
- Python 3.12+ / FastAPI
- SQLAlchemy 2.x (async)
- PostgreSQL 16
- NetworkX (graph analysis)
- Alembic (migrations)
- pytest + httpx

### Infrastructure
- Docker + Docker Compose
- Nginx (frontend serving)

---

## Prerequisites

- Docker and Docker Compose
- Node.js 20+ (for local frontend dev)
- Python 3.12+ (for local backend dev)

---

## Quick Start (Docker)

```bash
# 1. Clone the repository
git clone <repo-url>
cd trace-net

# 2. Copy environment file
cp .env.example .env

# 3. Start all services
docker compose up -d

# 4. Wait for backend to be healthy, then run migrations
docker compose exec backend alembic upgrade head

# 5. Seed demo data
docker compose exec backend python -m app.seed

# 6. Access the application
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000/api/docs
```

---

## Demo Accounts

| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | ADMIN |
| investigator | investigator123 | INVESTIGATOR |
| analyst | analyst123 | ANALYST |

> ⚠️ These are demo credentials only. Do not use in production.

---

## Local Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server runs on port 5173 and proxies API calls to port 8000.

---

## Database Migrations

```bash
# Create a new migration
docker compose exec backend alembic revision --autogenerate -m "description"

# Apply migrations
docker compose exec backend alembic upgrade head

# Rollback
docker compose exec backend alembic downgrade -1
```

---

## Seed Data

The seed script creates synthetic demo data:
- 3 users (admin, investigator, analyst)
- 15 cases across different crime categories
- 44 entities (persons, phones, emails, IPs, UPI IDs, bank accounts, vehicles, locations, organizations)
- 59 relationships forming multiple clusters
- 18 evidence items with SHA-256 integrity hashes
- 12 cross-case leads
- Bridge entity connecting clusters
- Fan-out pattern (one entity connecting to many phones)
- TN-2026-0002 is a fully connected graph (12 nodes, 19 edges, 1 component)

All data is entirely synthetic — no real personal data is used.

---

## API Documentation

FastAPI auto-generates API documentation:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/auth/login | Authenticate |
| GET | /api/v1/auth/me | Current user info |
| GET | /api/v1/dashboard | Dashboard statistics |
| POST | /api/v1/cases | Create case |
| GET | /api/v1/cases | List cases |
| POST | /api/v1/cases/{id}/evidence | Upload evidence |
| GET | /api/v1/cases/{id}/relationships/graph | Get network graph |
| POST | /api/v1/cases/{id}/analysis/run | Run full analysis |
| GET | /api/v1/cases/{id}/analysis/key-entities | Key entity analysis |
| GET | /api/v1/cases/{id}/analysis/patterns | Suspicious patterns |
| POST | /api/v1/cases/{id}/correlations | Cross-case correlation |
| GET | /api/v1/leads | List leads |
| POST | /api/v1/reports/case/{id} | Generate report |
| GET | /api/v1/search | Global search |

---

## Testing

```bash
# Backend tests
cd backend
pytest -v

# Frontend build check
cd frontend
npm run build
```

---

## Demo Workflow

1. **Login** with demo credentials (challenge-response verification)
2. **Dashboard** shows live statistics: 15 cases, 44 entities, 59 relationships, 12 leads
3. **Open TN-2026-0002** — Suspicious Fund Transfers (money laundering, CRITICAL priority)
4. **View Evidence** — Evidence items with SHA-256 integrity hashes
5. **Network Graph** — Shape-encoded nodes (circles=person, diamonds=phone, stars=UPI, etc.) with centrality metrics. TN-2026-0002 shows a fully connected 12-node graph
6. **Click a Node** — See entity details, degree, betweenness centrality, confidence score
7. **Cross-Case Intelligence** — Explain Connection shows why two cases are correlated
8. **Network Path Finder** — Find shortest path between any two entities across the network
9. **Cross-Case Timeline** — Chronological event view across multiple cases
10. **Review Leads** — Score, priority, explanation, and supporting evidence for each lead
11. **Generate Report** — JSON report with fact/inference distinction

> **Recommended demo case:** TN-2026-0002 (Suspicious Fund Transfers — Bandra Cluster) has a fully connected graph with 12 entities and 19 relationships, making it ideal for the network visualization and path-finder demos.

---

## Security Considerations

- Passwords are hashed with bcrypt
- JWT tokens with expiration
- Role-based access control on backend
- File type and size validation
- SHA-256 evidence integrity verification
- Audit logging of all important actions
- No secrets in source code
- CORS configured for development

---

## Limitations

- This prototype operates on synthetic/demo data
- Real-world deployment would require approved government datasets, privacy controls, legal authorization, security accreditation, data-quality validation, and integration with authorized systems
- Entity extraction uses rule-based methods; production would benefit from trained NLP models
- Graph analysis is designed for demo-scale data (hundreds of entities)
- AI features are optional and use MockProvider by default

---

## Free Public Deployment

TRACE-NET can be deployed for free using:

- **Render Free Static Site** (frontend)
- **Render Free Web Service** (FastAPI backend)
- **Supabase Free PostgreSQL** (database)

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete step-by-step instructions.

**Free-tier limitations:**
- Render services spin down after 15 minutes of inactivity (cold start takes ~30-60s)
- Render free tier cannot send outbound SMTP email
- Supabase free tier provides 500 MB database and pauses after 7 days of inactivity
- Local file storage is ephemeral on Render (evidence uploads not durable)

> The public deployment is intended for hackathon demonstration and educational use.

---

## Responsible Use Disclaimer

> TRACE-NET is an investigative decision-support platform. Analytical scores, graph prominence, correlations, and detected patterns are potential leads generated from available data. They do not establish criminal responsibility and must be independently reviewed by an authorized investigator.

---

## Future Enhancements

- Production NLP models (spaCy, BERT) for entity extraction
- S3-compatible storage (MinIO) integration
- AI-powered narrative generation (OpenAI integration)
- Real-time WebSocket updates
- PDF report generation
- Advanced community detection algorithms
- Temporal graph analysis
- Multi-tenancy support
- Integration with authorized government databases

---

**This prototype operates on synthetic/demo data. Real-world deployment would require approved government datasets, privacy controls, legal authorization, security accreditation, data-quality validation, and integration with authorized systems.**
