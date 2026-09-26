# APEX LINK — Executive Summary

**Explainable Criminal Network & Investigation Intelligence Platform**
SIH26189 · Ministry of Home Affairs · Blockchain & Cybersecurity

---

## The Problem

Indian law-enforcement investigations produce fragmented data across FIRs, call records (CDRs), financial transactions, surveillance notes, and criminal-history records. Investigators spend weeks manually cross-referencing these fragments to identify connections between suspects, accounts, devices, and cases. The process is slow, difficult to audit, and impossible to explain to courts in structured terms.

## The Solution

APEX LINK is a **decision-support system** that ingests fragmented investigation data, extracts entities and relationships, constructs interactive criminal-network graphs, detects suspicious patterns, and presents explainable intelligence — with every analytical output clearly marked as a **potential lead requiring human verification**.

It is not an autonomous system. It does not declare anyone a criminal. It makes the investigator faster and the analysis auditable.

## What's Working Today

| Capability | Implementation |
|-----------|---------------|
| **Entity Extraction** | 9+ entity types from text (phones, emails, IPs, UPI IDs, bank accounts, vehicles, locations, organizations) |
| **Entity Resolution** | Deduplication via exact match + name similarity scoring |
| **Network Graph** | Interactive Cytoscape.js visualization with centrality, community detection, bridge identification |
| **Cross-Case Correlation** | Weighted multi-factor scoring across cases using shared identifiers |
| **Pattern Detection** | Bridge entities, fan-out/fan-in, burst activity, multi-case identifiers — each with explanation |
| **Explainable Leads** | Transparent scoring with supporting evidence, priority ranking, review workflow |
| **Path Finder** | Shortest evidence-backed path between any two entities across the network |
| **Connection Explainer** | Structured reasoning for why two cases are connected |
| **Cross-Case Timeline** | Chronological event view across authorized cases |
| **Reporting** | JSON and PDF reports distinguishing observed facts from algorithmic inferences |
| **Security** | JWT auth, bcrypt, RBAC, rate limiting, case-level authorization, audit trail |

**Test baseline:** 235 backend tests ✅ · 24 frontend tests ✅ · TypeScript clean ✅ · Production build passing ✅

## Tech Stack

React 18 + TypeScript · FastAPI + Python 3.12 · PostgreSQL · NetworkX · Cytoscape.js · Docker

## Responsible AI & Design Principles

1. **Explainability over prediction** — Every score includes its contributing factors and supporting evidence. No black-box decisions.
2. **Human-in-the-loop** — All outputs are "potential leads requiring human verification." The system assists investigators; it does not replace their judgment.
3. **Synthetic data only** — The demo operates entirely on synthetic investigation data. No real personal data is used.
4. **Algorithmic transparency** — Algorithm version is tracked. Scoring weights are documented. Reports distinguish "OBSERVED_FACT" from "ALGORITHMIC_INFERENCE."

## Architecture Readiness

APEX LINK is Phase 1 of a deliberately-scoped implementation of the NEXUS system architecture. Each subsystem has clean interfaces designed for upgrade:

- Rule-based extraction → NLP models (spaCy/BERT) plug into the same API
- NetworkX graph → Neo4j or distributed graph if scale requires
- JWT auth → mTLS + device binding for production
- Application audit log → Blockchain-anchored hash chain (designed, not built)

## Deployment

**Live demo:** https://apex-link-frontend.onrender.com. The free-tier web service may take 30–60 seconds to wake after inactivity. Its free PostgreSQL database expires after 30 days unless upgraded, so seeded demo data is temporary.

## Demo Path (60 Seconds)

Open the live demo at https://apex-link-frontend.onrender.com. Free-tier wake-up may take 30–60 seconds after inactivity; the free PostgreSQL database expires after 30 days unless upgraded.

```
Login (challenge-response)
  → Dashboard (live stats)
    → Open Case AL-2026-0002 (CRITICAL)
      → Evidence (SHA-256 verified)
        → Network Graph (13 nodes, 20 edges, 1 component)
          → Click Node (centrality, confidence)
            → Explain Connection (structured reasoning)
              → Path Finder (shortest path)
                → Lead Review (score, explanation)
                  → Generate Report (JSON/PDF)
```

---

**Repository:** https://github.com/rdr-cyber/apex-link
**License:** MIT
**Status:** Working prototype · Synthetic data only · All analytical outputs require human verification
