"""Idempotent seed script for synthetic demo data — Phase 2.

Creates demo users, cases, evidence, entities, relationships, and leads.
All data is entirely synthetic — no real personal data is used.
Running twice will not create uncontrolled duplicates.
"""

import asyncio
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.security import hash_password
from app.core.settings import get_settings
from app.db.session import async_session_factory, engine, Base
from app.models.user import User, UserRole
from app.models.case import Case, CaseStatus, CasePriority
from app.models.evidence import Evidence, EvidenceType
from app.models.entity import Entity, EntityType, CaseEntity
from app.models.entity_mention import EntityMention, ExtractionMethod
from app.models.relationship import Relationship, RelationshipType
from app.models.lead import Lead, LeadStatus, LeadPriority
from app.models.audit import AuditLog
from app.models.login_otp import LoginOTP  # noqa: F401 — ensure table is registered
from app.models.email_verification import EmailVerificationToken  # noqa: F401

settings = get_settings()

# --- Users ---
# Passwords are read from environment variables (ADMIN_PASSWORD, etc.)
# In production, these MUST be set via Render environment variables.
# The defaults in settings.py are for local development only.

import warnings as _warnings
_weak_passwords = {"admin123", "investigator123", "analyst123"}
if settings.ADMIN_PASSWORD in _weak_passwords:
    _warnings.warn(
        "ADMIN_PASSWORD is a weak default. "
        "Set a strong ADMIN_PASSWORD via environment variable for production.",
        stacklevel=1,
    )

DEMO_USERS = [
    {"username": settings.ADMIN_USERNAME, "email": "admin@trace-net-demo.local", "password": settings.ADMIN_PASSWORD, "full_name": "Rajdip Routh", "role": UserRole.ADMIN},
    {"username": settings.INVESTIGATOR_USERNAME, "email": "investigator@trace-net-demo.local", "password": settings.INVESTIGATOR_PASSWORD, "full_name": "Rajdip Routh", "role": UserRole.INVESTIGATOR},
    {"username": settings.ANALYST_USERNAME, "email": "analyst@trace-net-demo.local", "password": settings.ANALYST_PASSWORD, "full_name": "Rajdip Routh", "role": UserRole.ANALYST},
]

# --- Cases ---
DEMO_CASES = [
    {"case_number": "TN-2026-0001", "title": "Cyber Fraud Ring — Andheri Operations", "description": "Multiple reports of online financial fraud originating from Andheri West area. Victims report unauthorized UPI transactions.", "category": "CYBER_FRAUD", "priority": CasePriority.HIGH, "status": CaseStatus.ANALYSIS, "incident_date": datetime(2026, 1, 15, tzinfo=timezone.utc), "location": "Andheri West, Mumbai"},
    {"case_number": "TN-2026-0002", "title": "Suspicious Fund Transfers — Bandra Cluster", "description": "Pattern of suspicious fund transfers through multiple accounts linked to Bandra East.", "category": "MONEY_LAUNDERING", "priority": CasePriority.CRITICAL, "status": CaseStatus.ANALYSIS, "incident_date": datetime(2026, 2, 3, tzinfo=timezone.utc), "location": "Bandra East, Mumbai"},
    {"case_number": "TN-2026-0003", "title": "Drug Trafficking Intelligence — Delhi Network", "description": "Intelligence report indicating a drug distribution network operating from Connaught Place.", "category": "DRUG_TRAFFICKING", "priority": CasePriority.HIGH, "status": CaseStatus.UNDER_REVIEW, "incident_date": datetime(2026, 2, 20, tzinfo=timezone.utc), "location": "Connaught Place, Delhi"},
    {"case_number": "TN-2026-0004", "title": "Phishing Campaign — Banking Credentials", "description": "Coordinated phishing campaign targeting banking customers via SMS and email.", "category": "CYBER_FRAUD", "priority": CasePriority.HIGH, "status": CaseStatus.OPEN, "incident_date": datetime(2026, 3, 1, tzinfo=timezone.utc), "location": "Mumbai"},
    {"case_number": "TN-2026-0005", "title": "Identity Theft Ring — Maharashtra", "description": "Multiple identity theft reports linked to a common set of identifiers.", "category": "IDENTITY_THEFT", "priority": CasePriority.MEDIUM, "status": CaseStatus.OPEN, "incident_date": datetime(2026, 3, 10, tzinfo=timezone.utc), "location": "Pune, Maharashtra"},
    {"case_number": "TN-2026-0006", "title": "Counterfeit Currency — Gurgaon", "description": "Reports of counterfeit currency circulating in Gurgaon markets.", "category": "COUNTERFEIT", "priority": CasePriority.MEDIUM, "status": CaseStatus.OPEN, "incident_date": datetime(2026, 3, 15, tzinfo=timezone.utc), "location": "Gurgaon, Haryana"},
    {"case_number": "TN-2026-0007", "title": "Vehicle Theft Network — South Delhi", "description": "Organized vehicle theft ring operating across South Delhi.", "category": "VEHICLE_THEFT", "priority": CasePriority.MEDIUM, "status": CaseStatus.OPEN, "incident_date": datetime(2026, 3, 20, tzinfo=timezone.utc), "location": "South Delhi"},
    {"case_number": "TN-2026-0008", "title": "Extortion Calls — Bandra", "description": "Series of extortion calls targeting local business owners in Bandra.", "category": "EXTORTION", "priority": CasePriority.HIGH, "status": CaseStatus.OPEN, "incident_date": datetime(2026, 4, 1, tzinfo=timezone.utc), "location": "Bandra, Mumbai"},
    {"case_number": "TN-2026-0009", "title": "Data Breach — QuickTrade Solutions", "description": "Suspected data breach at QuickTrade Solutions exposing customer information.", "category": "CYBER_FRAUD", "priority": CasePriority.CRITICAL, "status": CaseStatus.ANALYSIS, "incident_date": datetime(2026, 4, 5, tzinfo=timezone.utc), "location": "Mumbai"},
    {"case_number": "TN-2026-0010", "title": "Wire Fraud — International Pattern", "description": "Wire fraud pattern involving international money transfers.", "category": "WIRE_FRAUD", "priority": CasePriority.HIGH, "status": CaseStatus.OPEN, "incident_date": datetime(2026, 4, 10, tzinfo=timezone.utc), "location": "Mumbai"},
    {"case_number": "TN-2026-0011", "title": "Loan Shark Operations — Pune", "description": "Illegal lending operations with predatory practices.", "category": "FINANCIAL_CRIME", "priority": CasePriority.LOW, "status": CaseStatus.OPEN, "incident_date": datetime(2026, 4, 15, tzinfo=timezone.utc), "location": "Pune, Maharashtra"},
    {"case_number": "TN-2026-0012", "title": "SIM Swap Fraud — Delhi", "description": "Series of SIM swap attacks leading to unauthorized fund transfers.", "category": "CYBER_FRAUD", "priority": CasePriority.HIGH, "status": CaseStatus.OPEN, "incident_date": datetime(2026, 4, 20, tzinfo=timezone.utc), "location": "Delhi"},
    {"case_number": "TN-2026-0013", "title": "Cryptocurrency Scam — Gurgaon", "description": "Fraudulent cryptocurrency investment scheme targeting retail investors.", "category": "CYBER_FRAUD", "priority": CasePriority.MEDIUM, "status": CaseStatus.OPEN, "incident_date": datetime(2026, 5, 1, tzinfo=timezone.utc), "location": "Gurgaon, Haryana"},
    {"case_number": "TN-2026-0014", "title": "Illegal Gambling Ring — Mumbai", "description": "Online gambling operation using proxy servers.", "category": "ILLEGAL_GAMBLING", "priority": CasePriority.LOW, "status": CaseStatus.OPEN, "incident_date": datetime(2026, 5, 5, tzinfo=timezone.utc), "location": "Mumbai"},
    {"case_number": "TN-2026-0015", "title": "Human Trafficking Intelligence — Border Route", "description": "Intelligence report about a suspected human trafficking operation.", "category": "HUMAN_TRAFFICKING", "priority": CasePriority.CRITICAL, "status": CaseStatus.UNDER_REVIEW, "incident_date": datetime(2026, 5, 10, tzinfo=timezone.utc), "location": "Rajasthan Border"},
]

# --- Entities ---
# Cluster A: Cyber fraud (cases 0001, 0004, 0005, 0011)
# Cluster B: Money laundering (cases 0002, 0009, 0010)
# Cluster C: Drug trafficking (cases 0003, 0006, 0007, 0014, 0015)
# Bridge: PHONE 7654321098 connects A↔B, EMAIL-B connects B↔C

DEMO_ENTITIES = [
    # --- Cluster A entities ---
    {"entity_type": "PERSON", "canonical": "Vikram Patel", "display": "Vikram Patel", "normalized": "vikram patel"},
    {"entity_type": "PHONE", "canonical": "+91 98765 43210", "display": "9876543210", "normalized": "9876543210"},
    {"entity_type": "EMAIL", "canonical": "vikram.p@demo-mail.com", "display": "vikram.p@demo-mail.com", "normalized": "vikram.p@demo-mail.com"},
    {"entity_type": "UPI_ID", "canonical": "vikram.p@upibank", "display": "vikram.p@upibank", "normalized": "vikram.p@upibank"},
    {"entity_type": "IP_ADDRESS", "canonical": "192.168.1.105", "display": "192.168.1.105", "normalized": "192.168.1.105"},
    {"entity_type": "PHONE", "canonical": "+91 87654 32109", "display": "8765432109", "normalized": "8765432109"},
    {"entity_type": "PERSON", "canonical": "Anita Desai", "display": "Anita Desai", "normalized": "anita desai"},
    {"entity_type": "EMAIL", "canonical": "anita.d@demo-mail.com", "display": "anita.d@demo-mail.com", "normalized": "anita.d@demo-mail.com"},
    {"entity_type": "VEHICLE", "canonical": "MH 12 AB 1234", "display": "MH12AB1234", "normalized": "MH12AB1234"},
    {"entity_type": "LOCATION", "canonical": "Andheri West, Mumbai", "display": "Andheri West, Mumbai", "normalized": "andheri west mumbai"},

    # --- Bridge entities (connect clusters) ---
    {"entity_type": "PHONE", "canonical": "+91 76543 21098", "display": "7654321098", "normalized": "7654321098"},  # idx 10: bridge A↔B
    {"entity_type": "UPI_ID", "canonical": "sunil.m@upibank", "display": "sunil.m@upibank", "normalized": "sunil.m@upibank"},  # idx 11: bridge A↔B

    # --- Cluster B entities ---
    {"entity_type": "PERSON", "canonical": "Meera Joshi", "display": "Meera Joshi", "normalized": "meera joshi"},
    {"entity_type": "PHONE", "canonical": "+91 65432 10987", "display": "6543210987", "normalized": "6543210987"},
    {"entity_type": "EMAIL", "canonical": "meera.j@demo-mail.com", "display": "meera.j@demo-mail.com", "normalized": "meera.j@demo-mail.com"},
    {"entity_type": "BANK_ACCOUNT", "canonical": "HDFC-1234567890", "display": "HDFC-1234567890", "normalized": "hdfc-1234567890"},
    {"entity_type": "IP_ADDRESS", "canonical": "10.0.0.55", "display": "10.0.0.55", "normalized": "10.0.0.55"},
    {"entity_type": "PHONE", "canonical": "+91 54321 09876", "display": "5432109876", "normalized": "5432109876"},
    {"entity_type": "PERSON", "canonical": "Suresh Nair", "display": "Suresh Nair", "normalized": "suresh nair"},
    {"entity_type": "EMAIL", "canonical": "suresh.n@demo-mail.com", "display": "suresh.n@demo-mail.com", "normalized": "suresh.n@demo-mail.com"},
    {"entity_type": "ORGANIZATION", "canonical": "QuickTrade Solutions", "display": "QuickTrade Solutions", "normalized": "quicktrade solutions"},
    {"entity_type": "LOCATION", "canonical": "Bandra East, Mumbai", "display": "Bandra East, Mumbai", "normalized": "bandra east mumbai"},

    # --- Cluster C entities ---
    {"entity_type": "PERSON", "canonical": "Ravi Gupta", "display": "Ravi Gupta", "normalized": "ravi gupta"},
    {"entity_type": "PHONE", "canonical": "+91 43210 98765", "display": "4321098765", "normalized": "4321098765"},
    {"entity_type": "EMAIL", "canonical": "ravi.g@demo-mail.com", "display": "ravi.g@demo-mail.com", "normalized": "ravi.g@demo-mail.com"},
    {"entity_type": "VEHICLE", "canonical": "DL 03 CD 5678", "display": "DL03CD5678", "normalized": "DL03CD5678"},
    {"entity_type": "LOCATION", "canonical": "Connaught Place, Delhi", "display": "Connaught Place, Delhi", "normalized": "connaught place delhi"},
    {"entity_type": "PHONE", "canonical": "+91 32109 87654", "display": "3210987654", "normalized": "3210987654"},
    {"entity_type": "PERSON", "canonical": "Deepa Menon", "display": "Deepa Menon", "normalized": "deepa menon"},
    {"entity_type": "EMAIL", "canonical": "deepa.m@demo-mail.com", "display": "deepa.m@demo-mail.com", "normalized": "deepa.m@demo-mail.com"},
    {"entity_type": "ORGANIZATION", "canonical": "Metro Logistics Pvt Ltd", "display": "Metro Logistics Pvt Ltd", "normalized": "metro logistics pvt ltd"},
    {"entity_type": "IP_ADDRESS", "canonical": "172.16.0.99", "display": "172.16.0.99", "normalized": "172.16.0.99"},

    # --- Fan-out entity ---
    {"entity_type": "PERSON", "canonical": "Amit Verma", "display": "Amit Verma", "normalized": "amit verma"},  # idx 32
]

# Fan-out phones (Amit connects to many)
for i, num in enumerate(["1234567890", "2345678901", "3456789012", "4567890123", "5678901234", "6789012345", "7890123456", "8901234567", "9012345678"]):
    DEMO_ENTITIES.append({"entity_type": "PHONE", "canonical": f"+91 {num[:5]} {num[5:]}", "display": num, "normalized": num})

DEMO_ENTITIES.append({"entity_type": "LOCATION", "canonical": "Cyber Hub, Gurgaon", "display": "Cyber Hub, Gurgaon", "normalized": "cyber hub gurgaon"})
DEMO_ENTITIES.append({"entity_type": "ORGANIZATION", "canonical": "Digital Pay Solutions", "display": "Digital Pay Solutions", "normalized": "digital pay solutions"})

# --- Evidence text content ---
EVIDENCE_TEXTS = [
    "Contact Vikram Patel at +91 98765 43210 or vikram.p@demo-mail.com. UPI: vikram.p@upibank. IP logged: 192.168.1.105. Vehicle MH 12 AB 1234 spotted near Andheri West.",
    "Call records show frequent communication between 9876543210 and 8765432109. Anita Desai (anita.d@demo-mail.com) was also contacted. Amounts of ₹50,000 and ₹75,000 transferred via UPI.",
    "Fund transfers traced from vikram.p@upibank to sunil.m@upibank. Amount: ₹2,50,000. Meera Joshi (meera.j@demo-mail.com) linked via Bank Account HDFC-1234567890. IP 10.0.0.55 involved.",
    "Suresh Nair (suresh.n@demo-mail.com) connected to QuickTrade Solutions. Phone 6543210987 and 5432109876 both active in Bandra East transactions.",
    "Ravi Gupta (ravi.g@demo-mail.com) linked to vehicle DL 03 CD 5678 operating from Connaught Place, Delhi. Phone 4321098765 and 3210987654 detected.",
    "Deepa Menon (deepa.m@demo-mail.com) connected to Metro Logistics Pvt Ltd. IP 172.16.0.99 used for communications.",
    "Phishing messages traced to phone 7654321098 (same as bridge entity). UPI sunil.m@upibank used in multiple fraud transactions. Emails sent from vikram.p@demo-mail.com.",
    "Identity theft reports linked to phone 9876543210 and email vikram.p@demo-mail.com. IP 192.168.1.105 used in several unauthorized access attempts.",
    "Counterfeit currency distribution traced through QuickTrade Solutions network. Contact: 6543210987. Location: Cyber Hub, Gurgaon.",
    "Vehicle theft reports. Contact numbers 4321098765 and 3210987654. Organization: Metro Logistics Pvt Ltd suspected of transport.",
    "Extortion calls from 6543210987 to multiple business owners. Ravi Gupta identified as potential caller. IP 10.0.0.55 used.",
    "Data breach at QuickTrade Solutions. Suresh Nair (suresh.n@demo-mail.com) had admin access. IP 10.0.0.55 used for unauthorized data export.",
    "Wire fraud pattern. Phone 7654321098 and UPI sunil.m@upibank linked to international transfers. Connected to Meera Joshi via HDFC-1234567890.",
    "Loan shark operations. Phone 5432109876 and email meera.j@demo-mail.com linked. Amounts of ₹5,00,000 traced.",
    "SIM swap attacks. Phone 7654321098 targeted. Linked to vikram.p@upibank UPI. IP 192.168.1.105 used.",
    "Crypto scam. Phone 6543210987 and 5432109876 used. QuickTrade Solutions entity connected. Amount ₹10,00,000.",
    "Online gambling. IP 172.16.0.99 used as proxy server. Phone 3210987654 connected.",
    "Trafficking intelligence. Phone 4321098765 and 3210987654 detected along route. Vehicle DL 03 CD 5678 flagged. Deepa Menon person of interest.",
]

# Entity-to-case mapping (which entities appear in which cases, 0-indexed)
ENTITY_CASE_MAP = {
    0: [0, 3, 4, 11],     # Vikram Patel
    1: [0, 4, 11],         # Phone 9876543210
    2: [0, 4],             # Email vikram.p
    3: [0, 3],             # UPI vikram.p
    4: [0, 4, 8],          # IP 192.168.1.105
    5: [0, 3],             # Phone 8765432109
    6: [0],                # Anita Desai
    7: [0],                # Email anita.d
    8: [0],                # Vehicle MH12AB1234
    9: [0],                # Location Andheri
    10: [1, 3, 7, 9],     # BRIDGE: Phone 7654321098
    11: [1, 3, 9],        # BRIDGE: UPI sunil.m
    12: [1, 8, 10],       # Meera Joshi
    13: [1],               # Phone 6543210987
    14: [1, 8, 10],       # Email meera.j
    15: [1, 9],            # Bank HDFC
    16: [1],               # IP 10.0.0.55
    17: [1],               # Phone 5432109876
    18: [1, 12],           # Suresh Nair
    19: [1, 8],            # Email suresh.n
    20: [1, 5, 6, 8, 12], # QuickTrade Solutions
    21: [1],               # Location Bandra East
    22: [2, 6, 7, 14],    # Ravi Gupta
    23: [2, 6, 14],       # Phone 4321098765
    24: [2, 14],           # Email ravi.g
    25: [2, 14],           # Vehicle DL03CD5678
    26: [2],               # Location Connaught Place
    27: [2, 6],            # Phone 3210987654
    28: [2, 14],           # Deepa Menon
    29: [2, 14],           # Email deepa.m
    30: [2, 6, 7],         # Metro Logistics
    31: [2],               # IP 172.16.0.99
    32: [12],              # Amit Verma (fan-out)
}

# Add fan-out phones to case 12
for i in range(9):
    ENTITY_CASE_MAP[33 + i] = [12]


async def seed():
    """Run the seed script idempotently.

    IMPORTANT: This script does NOT create tables.
    Run 'alembic upgrade head' first to create/migrate the schema.
    This script only inserts demo data if the users table is empty.
    """
    async with async_session_factory() as db:

        from sqlalchemy import select
        existing = await db.execute(select(User).limit(1))
        if existing.scalar_one_or_none() is not None:
            print("Seed data already exists. Skipping.")
            return

        print("Seeding Phase 2 demo data...")

        # Create users (demo users are pre-verified)
        users = []
        for u in DEMO_USERS:
            user = User(
                username=u["username"], email=u["email"],
                password_hash=hash_password(u["password"]),
                full_name=u["full_name"], role=u["role"],
                email_verified=True,
                email_verified_at=datetime.now(timezone.utc),
            )
            db.add(user)
            users.append(user)
        await db.flush()
        print(f"  Created {len(users)} users (demo accounts pre-verified)")

        # Create cases
        cases = []
        for c in DEMO_CASES:
            case = Case(
                case_number=c["case_number"], title=c["title"],
                description=c["description"], category=c["category"],
                priority=c["priority"], status=c["status"],
                incident_date=c["incident_date"], location=c["location"],
                created_by=users[1].id,
            )
            db.add(case)
            cases.append(case)
        await db.flush()
        print(f"  Created {len(cases)} cases")

        # Create entities
        entities = []
        for e in DEMO_ENTITIES:
            entity = Entity(
                entity_type=e["entity_type"], canonical_value=e["canonical"],
                display_value=e["display"], normalized_value=e["normalized"],
                confidence=0.95,
            )
            db.add(entity)
            entities.append(entity)
        await db.flush()
        print(f"  Created {len(entities)} entities")

        # Create evidence and link entities
        storage_base = Path(settings.LOCAL_STORAGE_PATH)
        evidence_list = []
        for i, text in enumerate(EVIDENCE_TEXTS):
            case_idx = min(i // 2, len(cases) - 1)
            case = cases[case_idx]

            ev_dir = storage_base / str(case.id) / "demo"
            ev_dir.mkdir(parents=True, exist_ok=True)
            safe_name = f"demo_evidence_{i:03d}.txt"
            ev_path = ev_dir / safe_name
            with open(ev_path, "w", encoding="utf-8") as f:
                f.write(text)

            sha256 = hashlib.sha256(text.encode()).hexdigest()

            ev = Evidence(
                case_id=case.id, evidence_number=f"EV-{i + 1:05d}",
                evidence_type=EvidenceType.SURVEILLANCE_NOTE if i % 2 == 0 else EvidenceType.CDR,
                filename=safe_name, mime_type="text/plain",
                size_bytes=len(text.encode()), storage_path=str(ev_path),
                sha256_hash=sha256,
                description=f"Demo evidence for {case.case_number}",
                source="synthetic_demo", collected_by="Demo System",
                collected_at=case.incident_date + timedelta(days=i),
            )
            db.add(ev)
            evidence_list.append(ev)
        await db.flush()
        print(f"  Created {len(evidence_list)} evidence records")

        # Create CaseEntity links
        ce_count = 0
        for entity_idx, case_indices in ENTITY_CASE_MAP.items():
            if entity_idx >= len(entities):
                continue
            entity = entities[entity_idx]
            for case_idx in case_indices:
                if case_idx >= len(cases):
                    continue
                ce = CaseEntity(
                    case_id=cases[case_idx].id, entity_id=entity.id,
                    confidence=0.9, mention_text=entity.display_value,
                )
                db.add(ce)
                ce_count += 1
        await db.flush()
        print(f"  Created {ce_count} case-entity links")

        # Create entity mentions
        mention_count = 0
        for entity_idx, case_indices in ENTITY_CASE_MAP.items():
            if entity_idx >= len(entities):
                continue
            entity = entities[entity_idx]
            for case_idx in case_indices:
                if case_idx >= len(evidence_list):
                    continue
                ev = evidence_list[case_idx]
                et_val = entity.entity_type.value if hasattr(entity.entity_type, 'value') else entity.entity_type
                mention = EntityMention(
                    evidence_id=ev.id, entity_type=et_val,
                    raw_text=entity.canonical_value,
                    normalized_value=entity.normalized_value,
                    confidence=0.9,
                    extraction_method=ExtractionMethod.IMPORT.value,
                )
                db.add(mention)
                mention_count += 1
        await db.flush()
        print(f"  Created {mention_count} entity mentions")

        # Create relationships
        rel_count = 0
        relationship_defs = [
            (0, 1, "OWNS_PHONE", "Vikram owns phone 9876543210"),
            (0, 2, "USES_EMAIL", "Vikram uses email vikram.p@demo-mail.com"),
            (0, 3, "USES_UPI", "Vikram uses UPI vikram.p@upibank"),
            (0, 4, "ASSOCIATED_WITH_IP", "Vikram associated with IP 192.168.1.105"),
            (6, 5, "OWNS_PHONE", "Anita owns phone 8765432109"),
            (6, 7, "USES_EMAIL", "Anita uses email anita.d@demo-mail.com"),
            (0, 8, "LOCATED_AT", "Vikram located at Andheri"),
            (12, 13, "OWNS_PHONE", "Meera owns phone 6543210987"),
            (12, 14, "USES_EMAIL", "Meera uses email meera.j@demo-mail.com"),
            (12, 15, "USES_UPI", "Meera linked to HDFC account"),
            (12, 16, "ASSOCIATED_WITH_IP", "Meera associated with IP 10.0.0.55"),
            (18, 17, "OWNS_PHONE", "Suresh owns phone 5432109876"),
            (18, 19, "USES_EMAIL", "Suresh uses email suresh.n@demo-mail.com"),
            (18, 20, "MEMBER_OF", "Suresh member of QuickTrade Solutions"),
            (22, 23, "OWNS_PHONE", "Ravi owns phone 4321098765"),
            (22, 24, "USES_EMAIL", "Ravi uses email ravi.g@demo-mail.com"),
            (22, 25, "LOCATED_AT", "Ravi operates vehicle DL03CD5678"),
            (28, 27, "OWNS_PHONE", "Deepa owns phone 3210987654"),
            (28, 29, "USES_EMAIL", "Deepa uses email deepa.m@demo-mail.com"),
            (28, 30, "MEMBER_OF", "Deepa linked to Metro Logistics"),
            (32, 33, "OWNS_PHONE", ""),
        ]
        for i in range(9):
            relationship_defs.append((32, 33 + i, "OWNS_PHONE", ""))

        for src_idx, tgt_idx, rel_type, desc in relationship_defs:
            if src_idx >= len(entities) or tgt_idx >= len(entities):
                continue
            src_cases = set()
            for ei, cis in ENTITY_CASE_MAP.items():
                if ei == src_idx:
                    src_cases = set(cis)
                    break
            tgt_cases = set()
            for ei, cis in ENTITY_CASE_MAP.items():
                if ei == tgt_idx:
                    tgt_cases = set(cis)
                    break
            shared = src_cases & tgt_cases
            case_id = cases[list(shared)[0]].id if shared else cases[0].id

            rel = Relationship(
                source_entity_id=entities[src_idx].id,
                target_entity_id=entities[tgt_idx].id,
                relationship_type=rel_type, confidence=0.9,
                case_id=case_id, description=desc,
            )
            db.add(rel)
            rel_count += 1
        await db.flush()
        print(f"  Created {rel_count} relationships")

        # Create leads
        lead_defs = [
            (0, 1, "CROSS_CASE_CORRELATION", 85, "CRITICAL", "Same phone and UPI appear in Case 0001 and Case 0002"),
            (0, 3, "CROSS_CASE_CORRELATION", 72, "HIGH", "Same phone 7654321098 appears in phishing case"),
            (1, 8, "CROSS_CASE_CORRELATION", 65, "HIGH", "QuickTrade Solutions entity links money laundering to data breach"),
            (2, 6, "CROSS_CASE_CORRELATION", 78, "HIGH", "Same phone numbers active in drug trafficking and extortion"),
            (0, 4, "CROSS_CASE_CORRELATION", 55, "MEDIUM", "Common identifiers between cyber fraud and identity theft"),
            (1, 9, "CROSS_CASE_CORRELATION", 62, "HIGH", "UPI and bank account linked in wire fraud pattern"),
            (2, 14, "CROSS_CASE_CORRELATION", 70, "HIGH", "Multiple shared entities between drug trafficking and trafficking intel"),
            (5, 12, "CROSS_CASE_CORRELATION", 45, "MEDIUM", "Location and organization overlap with crypto scam"),
            (3, 11, "CROSS_CASE_CORRELATION", 58, "MEDIUM", "Bridge phone links phishing to SIM swap fraud"),
            (1, 10, "CROSS_CASE_CORRELATION", 48, "MEDIUM", "Financial crime indicators overlap with money laundering"),
            (7, 8, "CROSS_CASE_CORRELATION", 52, "MEDIUM", "Common IP address between vehicle theft and data breach"),
            (0, 13, "CROSS_CASE_CORRELATION", 40, "LOW", "Weak correlation via shared phone patterns"),
        ]

        for case_idx, related_idx, lead_type, score, priority_str, explanation in lead_defs:
            if case_idx >= len(cases) or related_idx >= len(cases):
                continue
            lead = Lead(
                case_id=cases[case_idx].id, related_case_id=cases[related_idx].id,
                lead_type=lead_type, score=score,
                priority=LeadPriority(priority_str), explanation=explanation,
                status=LeadStatus.NEW,
                factors=json.dumps([{"reason": explanation, "weight": score}]),
            )
            db.add(lead)
        await db.flush()
        print("  Created demo leads")

        # Audit logs
        for user in users:
            log = AuditLog(
                user_id=user.id, action="SEED_COMPLETE",
                resource_type="SYSTEM",
                details=f"Phase 2 demo data seeded for user {user.username}",
            )
            db.add(log)
        await db.flush()
        print("  Created audit logs")

        await db.commit()
        print("Phase 2 seed complete!")


def run_seed():
    asyncio.run(seed())


if __name__ == "__main__":
    run_seed()
