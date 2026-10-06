# APEX LINK

Apex Link is a data analysis and relationship-mapping platform for exploring connected information across cases, entities, and evidence. It helps teams review data, identify patterns, and explain findings through an interactive graph and structured reporting workflow.

## Overview

This project combines a React frontend with a FastAPI backend to provide:

- case and evidence management
- entity extraction and normalization
- relationship discovery
- interactive network visualization
- cross-case correlation
- explainable lead scoring
- audit-friendly reporting
- role-based access control

## Features

| Feature | Description |
|---------|-------------|
| Authentication | Login flow with challenge-response verification, role-based access, and email verification |
| Case Management | Create and manage records with status, priority, category, and location |
| Evidence Handling | Upload files and track metadata, verification state, and audit history |
| Entity Extraction | Identify common entity types such as people, emails, phones, IPs, accounts, vehicles, and organizations |
| Relationship Mapping | Build links between records and visualize patterns in a graph |
| Network Analysis | Explore connected nodes, influence, communities, and shortest paths |
| Cross-Case Insights | Find shared identifiers and compare patterns across multiple data sets |
| Explainability | Show supporting evidence behind scores and recommendations |
| Reporting | Export structured JSON/PDF reports for review |
| Search | Search across cases, entities, and evidence records |

## Tech Stack

### Frontend
- React 18
- TypeScript
- Vite
- Tailwind CSS
- Cytoscape.js
- Recharts
- React Router

### Backend
- Python 3.12+
- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic
- NetworkX
- pytest

### Infrastructure
- Docker
- Docker Compose
- Render
- Supabase

## Project Structure

```text
backend/
  app/
  tests/
  alembic/
frontend/
  src/
  public/
  package.json
README.md
DEPLOYMENT.md
```

## Quick Start

### Docker

```bash
git clone <repository-url>
cd trace-net
docker compose up -d
```

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Demo Accounts

| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin123` | Admin |
| `investigator` | `investigator123` | Investigator |
| `analyst` | `analyst123` | Analyst |

> These demo credentials are intended for local testing and demonstration only.

## Development Notes

- This project is built as a prototype and demo-ready application.
- Data is synthetic by default and not intended for production data handling without review.
- See [DEPLOYMENT.md](DEPLOYMENT.md) for deployment setup and environment notes.

## Testing

```bash
# Backend
cd backend && python -m pytest tests/ -v

# Frontend
cd frontend && npx vitest run

# TypeScript check
cd frontend && npx tsc --noEmit

# Production build
cd frontend && npm run build
```

## License

This project is licensed under the MIT License.

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

> APEX LINK is an investigative decision-support platform. Analytical scores, graph prominence, correlations, and detected patterns are potential leads generated from available data. They do not establish criminal responsibility and must be independently reviewed by an authorized investigator.

**This prototype operates on synthetic/demo data. Real-world deployment would require approved government datasets, privacy controls, legal authorization, security accreditation, data-quality validation, and integration with authorized systems.**
