# TRACE-NET

## Explainable Criminal Network & Investigation Intelligence Platform

> **SIH26189 — AI-Powered Criminal Network Analysis System**
> Ministry of Home Affairs · Theme: Blockchain & Cybersecurity · Type: Software

---

## Problem

Law-enforcement investigations produce fragmented data across FIRs, call records, financial transactions, surveillance notes, and criminal-history records. Investigators must manually connect these fragments to identify relationships, detect patterns, and build actionable intelligence. This process is slow, error-prone, and difficult to explain to courts or oversight bodies.

**The challenge:** Build a system that analyzes fragmented investigation information to identify relationships, construct an interactive criminal-network graph, surface influential entities, detect suspicious patterns, and present explainable intelligence to an investigator.

## What TRACE-NET Does

TRACE-NET is a **decision-support and intelligence-analysis system**. It helps authorized investigators analyze fragmented data, construct interactive criminal-network graphs, surface influential entities, detect suspicious patterns, and present explainable intelligence.

**Important:** Every risk score, correlation, and recommendation is a **potential lead requiring human verification**. TRACE-NET does not declare anyone a criminal.

### Working Features (Demoable Today)

| Feature | What It Does |
|---------|-------------|
| 🔐 **Challenge-Response Authentication** | JWT-based login with math-challenge verification, RBAC (Admin/Investigator/Analyst), rate limiting, email verification |
| 📁 **Case Management** | Create, track, and manage investigation cases with status, priority, category, and location |
| 📎 **Evidence Management** | Upload evidence files with SHA-256 integrity verification and chain-of-custody audit trail |
| 🔍 **Entity Extraction** | Rule-based extraction of 9+ entity types: persons, phones, emails, IPs, UPI IDs, bank accounts, vehicles, devices, locations, organizations |
| 🧩 **Entity Resolution** | Intelligent deduplication — deterministic matching for identifiers, similarity scoring for person names |
| 🔗 **Relationship Discovery** | Automatic relationship generation from evidence co-occurrence with confidence scoring |
| 📊 **Interactive Network Graph** | Cytoscape.js visualization with centrality analysis, community detection, and bridge identification. Shape+color encoding for colorblind accessibility |
| 🔀 **Cross-Case Correlation** | Weighted multi-factor correlation across cases using shared identifiers |
| ⚡ **Pattern Detection** | Bridge entities, fan-in/fan-out patterns, burst activity, multi-case identifiers — each with explanation |
| 📈 **Explainable Lead Scoring** | Transparent scoring with supporting evidence, priority ranking, and review workflow |
| 🗺️ **Network Path Finder** | Find shortest evidence-backed path between any two entities across the network |
| 💡 **Explain Connection** | Structured reasoning for why two cases are analytically connected |
| 📅 **Cross-Case Timeline** | Chronological event view across multiple authorized cases |
| 📋 **Report Generation** | JSON and PDF reports distinguishing observed facts from algorithmic inferences |
| 🛡️ **Audit Trail** | Complete audit logging of all actions |
| 🔎 **Global Search** | Search across cases, entities, and evidence |

### Verified Test Baseline

| Test Suite | Count | Status |
|-----------|-------|--------|
| Backend (pytest) | 235 | ✅ All passing |
| Frontend (vitest) | 24 | ✅ All passing |
| TypeScript | — | ✅ Clean |
| Production build | — | ✅ Passing |

### Demo Data

The seed script creates a complete synthetic investigation dataset:
- **15 cases** across fraud, cybercrime, drug trafficking, and financial crime categories
- **42 entities** (persons, phones, emails, IPs, UPI IDs, bank accounts, vehicles, locations, organizations) linked across cases
- **59 relationships** forming multiple clusters with bridge entities
- **18 evidence items** with SHA-256 integrity hashes
- **12 cross-case leads** with explainable scoring

**All data is entirely synthetic. No real personal data is used.**

> **Recommended demo case:** TN-2026-0002 (Suspicious Fund Transfers — Bandra Cluster) has a fully connected graph with 12 entities and 19 relationships.

---

## Tech Stack

### Frontend
- React 18 + TypeScript + Vite
- Tailwind CSS (Investigation Workstation design system)
- React Router v6 + TanStack Query
- Cytoscape.js (network visualization)
- Recharts (analytics charts)
- Lucide React (icons)

### Backend
- Python 3.12+ / FastAPI
- SQLAlchemy 2.x (async) + PostgreSQL 16
- NetworkX (graph analysis)
- Alembic (migrations)
- ReportLab (PDF generation)
- pytest + httpx (testing)

### Infrastructure
- Docker + Docker Compose
- Render (free-tier deployment)
- Supabase (free-tier PostgreSQL)

---

## Quick Start

### Docker (Recommended)
```bash
git clone https://github.com/rdr-cyber/trace-net.git
cd trace-net
cp .env.example .env
docker compose up -d
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.seed
# Frontend: http://localhost:5173
# API docs: http://localhost:8000/api/docs
```

### Local Development
```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

### Demo Accounts

| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin123` | Admin |
| `investigator` | `investigator123` | Investigator |
| `analyst` | `analyst123` | Analyst |

> ⚠️ Demo credentials only. Do not use in production.

---

## Responsible Use & Current Limitations

### What TRACE-NET Is
- A **working prototype** demonstrating criminal-network analysis concepts
- A **decision-support tool** — all outputs are potential leads requiring human verification
- A **Phase 1 implementation** of the broader NEXUS system architecture (see `docs/NEXUS_VS_TRACE-NET.md`)

### What TRACE-NET Is Not
- It is **not** a production law-enforcement system
- It does **not** make accusations or declare guilt
- It does **not** integrate with real government databases
- It does **not** use real investigation data

### Known Limitations
- Entity extraction uses rule-based methods; production would benefit from trained NLP models (spaCy, BERT)
- Graph analysis is designed for demo-scale data (hundreds of entities)
- Evidence storage on free-tier hosting is ephemeral (metadata persists, binary files do not)
- Docker/PostgreSQL runtime verification deferred (Docker unavailable in current dev environment)
- AI features are optional and use MockProvider by default

### Deployment
See [DEPLOYMENT.md](DEPLOYMENT.md) for free public deployment using Render + Supabase.

### Future Roadmap
See [docs/NEXUS_VS_TRACE-NET.md](docs/NEXUS_VS_TRACE-NET.md) for the full NEXUS system vision and TRACE-NET's phased implementation plan.

---

## Architecture

```
Browser
  ↓
Render Static Site (React Frontend)
  ↓  HTTPS API calls
Render Web Service (FastAPI Backend)
  ↓  PostgreSQL (SSL)
Supabase Free PostgreSQL
```

---

## API Documentation

FastAPI auto-generates API documentation:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Testing

```bash
# Backend (235 tests)
cd backend && python -m pytest tests/ -v

# Frontend (24 tests)
cd frontend && npx vitest run

# TypeScript check
cd frontend && npx tsc --noEmit

# Production build
cd frontend && npm run build
```

---

## Demo Workflow (5-Minute Script)

1. **Login** → Challenge-response verification
2. **Dashboard** → Live statistics: 15 cases, 42 entities, 59 relationships, 12 leads
3. **Open TN-2026-0002** → Suspicious Fund Transfers (CRITICAL priority)
4. **Evidence** → Items with SHA-256 integrity hashes
5. **Network Graph** → 12 shape-encoded nodes, 19 edges, 1 component — fully connected
6. **Click Node** → Entity details, centrality metrics, confidence score
7. **Cross-Case Intelligence** → Explain Connection with structured reasoning
8. **Network Path Finder** → Shortest path between entities
9. **Cross-Case Timeline** → Chronological events across cases
10. **Pattern Detection** → Bridge entity, fan-out, burst activity
11. **Lead Review** → Score, explanation, supporting evidence
12. **Generate Report** → JSON/PDF with fact/inference distinction

---

## Security

- Passwords hashed with bcrypt
- JWT tokens with expiration
- Role-based access control (Admin, Investigator, Analyst)
- Case-level authorization
- Rate limiting (5 login/minute, 3 verification/15 minutes)
- Production rejects weak JWT secrets and console email provider
- CORS restricted to configured origins
- SHA-256 evidence integrity verification
- Audit logging of all important actions
- No secrets in source code

---

## License

[MIT](LICENSE)

---

## Disclaimer

> TRACE-NET is an investigative decision-support platform. Analytical scores, graph prominence, correlations, and detected patterns are potential leads generated from available data. They do not establish criminal responsibility and must be independently reviewed by an authorized investigator.

**This prototype operates on synthetic/demo data. Real-world deployment would require approved government datasets, privacy controls, legal authorization, security accreditation, data-quality validation, and integration with authorized systems.**
