# TRACE-NET — Free Public Deployment Guide

> **TRACE-NET is a prototype intended for demonstration and educational use.**
> The public deployment uses synthetic data and free-tier infrastructure.
> It is not a production law-enforcement system.

## Architecture

```
Browser
  ↓
Render Static Site (Frontend)
  ↓  HTTPS API calls
Render Web Service (FastAPI Backend)
  ↓  PostgreSQL (SSL)
Supabase Free PostgreSQL
```

## Prerequisites

- [GitHub](https://github.com) account
- [Render](https://render.com) account (free tier)
- [Supabase](https://supabase.com) account (free tier)

---

## Step 1: Push to GitHub

```bash
cd trace-net
git init
git add .
git commit -m "TRACE-NET release candidate"
git remote add origin https://github.com/<your-username>/trace-net.git
git push -u origin main
```

---

## Step 2: Create Supabase Project

1. Go to https://supabase.com → Sign in → **New Project**
2. Project name: `trace-net`
3. Set a strong database password (save it)
4. Wait for project to initialize
5. Go to **Settings → Database → Connection string → URI**
6. Copy the URI — it looks like:
   ```
   postgresql://postgres.PROJECT_REF:PASSWORD@aws-0-REGION.pooler.supabase.com:6543/postgres
   ```
7. Create **two** connection strings:
   - **Async (runtime):** replace `postgresql://` with `postgresql+asyncpg://` → this is `DATABASE_URL`
   - **Sync (migrations):** replace `postgresql://` with `postgresql+psycopg2://` → this is `DATABASE_URL_SYNC`

### SSL

Supabase enforces SSL. If your connection string doesn't include `sslmode=require`, append `?sslmode=require`.

---

## Step 3: Create Render Backend

1. Go to https://dashboard.render.com → **New** → **Web Service**
2. Connect your GitHub repo
3. Configure:

| Field | Value |
|-------|-------|
| **Name** | `trace-net-backend` |
| **Runtime** | Python |
| **Plan** | Free |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Health Check Path** | `/api/health` |

4. Add **Environment Variables** (set these in the Render dashboard):

| Variable | Value | Notes |
|----------|-------|-------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Supabase async URI |
| `DATABASE_URL_SYNC` | `postgresql+psycopg2://...` | Supabase sync URI |
| `SECRET_KEY` | `<generate with openssl rand -hex 32>` | **Must be strong** |
| `DEBUG` | `false` | |
| `EMAIL_PROVIDER` | `demo` | Logs tokens server-side, safe for demo |
| `STORAGE_MODE` | `local` | Evidence metadata retained, binary ephemeral |
| `LOCAL_STORAGE_PATH` | `./storage/evidence` | |
| `CORS_ORIGINS` | *(leave empty for now)* | Set after frontend URL is known |
| `FRONTEND_BASE_URL` | *(leave empty for now)* | Set after frontend URL is known |
| `ADMIN_PASSWORD` | *(choose strong password)* | **Do not use defaults** |
| `INVESTIGATOR_PASSWORD` | *(choose strong password)* | |
| `ANALYST_PASSWORD` | *(choose strong password)* | |

5. Deploy. Note the backend URL: `https://trace-net-backend.onrender.com`

---

## Step 4: Run Migrations & Seed Data

After the backend deploys successfully:

1. Render Dashboard → your backend service → **Shell**
2. Run:

```bash
# Create all tables via Alembic
alembic upgrade head

# Seed synthetic demo data (idempotent — safe to run once)
python -m app.seed
```

3. Verify:

```bash
curl https://trace-net-backend.onrender.com/api/health
# Expected: {"status":"healthy","app":"TRACE-NET","version":"0.1.0"}

curl https://trace-net-backend.onrender.com/api/ready
# Expected: {"status":"ready","database":"connected"}
```

---

## Step 5: Create Render Frontend

1. Render Dashboard → **New** → **Static Site**
2. Connect the same GitHub repo
3. Configure:

| Field | Value |
|-------|-------|
| **Name** | `trace-net-frontend` |
| **Plan** | Free |
| **Build Command** | `cd frontend && npm ci && npm run build` |
| **Publish Directory** | `frontend/dist` |

4. Add **Environment Variable**:

| Variable | Value |
|----------|-------|
| `VITE_API_BASE_URL` | `https://trace-net-backend.onrender.com` |

> **Important:** `VITE_API_BASE_URL` is set at **build time**.
> If you change it, trigger a new deploy.

5. Deploy. Note the frontend URL: `https://trace-net-frontend.onrender.com`

---

## Step 6: Wire CORS

Go back to the **backend** service → **Environment** and update:

| Variable | Value |
|----------|-------|
| `CORS_ORIGINS` | `https://trace-net-frontend.onrender.com` |
| `FRONTEND_BASE_URL` | `https://trace-net-frontend.onrender.com` |

Trigger a **redeploy** of the backend service.

---

## Step 7: SPA Routing (if needed)

If deep links (`/login`, `/cases`, `/intelligence`, etc.) return 404 on browser refresh:

1. Frontend service → **Settings** → **Redirects/Rewrites**
2. Add rule:
   - **Source:** `/*`
   - **Destination:** `/index.html`
   - **Type:** Rewrite

---

## Step 8: Verify Deployment

### Health Check

```bash
curl https://trace-net-backend.onrender.com/api/health
# Expected: {"status":"healthy","app":"TRACE-NET","version":"0.1.0"}
```

### Readiness Check

```bash
curl https://trace-net-backend.onrender.com/api/ready
# Expected: {"status":"ready","database":"connected"}
```

### Frontend

Open `https://trace-net-frontend.onrender.com` in a browser.

> **Note:** Free-tier Render services spin down after 15 minutes of inactivity.
> The first request may take 30-60 seconds as the service wakes up.

---

## Demo Accounts

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | Set via `ADMIN_PASSWORD` env var |
| Investigator | `investigator` | Set via `INVESTIGATOR_PASSWORD` env var |
| Analyst | `analyst` | Set via `ANALYST_PASSWORD` env var |

All demo accounts are **pre-verified** (email_verified=true) and use the **challenge-response** login.

> Credentials are supplied through Render environment variables.
> They are NOT published in source code or documentation.

---

## Evidence Storage

On Render free tier, the local filesystem is **ephemeral** (files lost on restart).

In `STORAGE_MODE=local` (default):
- Evidence files are saved to local disk during the session
- Files are lost when the service restarts or redeploys
- Evidence **metadata** (number, type, hash, description) persists in the database
- Integrity verification returns `METADATA_ONLY` status for evidence without local files

For persistent evidence storage in production, configure:
- S3-compatible storage (e.g., AWS S3, MinIO, Backblaze B2)
- Or Supabase Storage
- Set `STORAGE_MODE=s3` and configure `S3_*` environment variables

---

## Free-Tier Limitations

### Render Free Web Service

- **Spin-down:** After 15 minutes without traffic, the service stops
- **Cold start:** First request after spin-down takes 30-60 seconds
- **Ephemeral filesystem:** Local files lost on restart
- **100 GB bandwidth/month**

### Supabase Free Plan

- **500 MB database** storage
- **1 GB file storage** (if Supabase Storage is configured)
- **Pause after 7 days of inactivity**
- **50,000 monthly active users** on Auth

> These limitations are sufficient for hackathon demonstration and educational use.

---

## Environment Variables Reference

### Backend

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | (dev default) | PostgreSQL async connection string |
| `DATABASE_URL_SYNC` | Yes | (dev default) | PostgreSQL sync connection string (for Alembic) |
| `SECRET_KEY` | Yes (prod) | `CHANGE_ME_BEFORE_PRODUCTION` | JWT signing secret — **must be changed** |
| `DEBUG` | No | `false` | Enable debug mode |
| `PORT` | No | `8000` | Server port (Render sets automatically) |
| `EMAIL_PROVIDER` | No | `console` | `console` (dev), `demo` (public demo), `smtp` (production) |
| `CORS_ORIGINS` | Yes | localhost | Comma-separated allowed origins |
| `FRONTEND_BASE_URL` | Yes | `http://localhost:5173` | Used for verification emails |
| `STORAGE_MODE` | No | `local` | `local` or `s3` |
| `ADMIN_PASSWORD` | No | `admin123` | Demo admin password |
| `INVESTIGATOR_PASSWORD` | No | `investigator123` | Demo investigator password |
| `ANALYST_PASSWORD` | No | `analyst123` | Demo analyst password |
| `DB_POOL_SIZE` | No | `5` | SQLAlchemy connection pool size |
| `DB_MAX_OVERFLOW` | No | `10` | Max overflow connections |
| `DB_POOL_RECYCLE` | No | `300` | Connection recycle time (seconds) |

### Frontend

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_API_BASE_URL` | Yes (prod) | (empty = proxy) | Backend API base URL |

> `VITE_*` variables are embedded in the frontend build at build time.
> Never put secrets (database URLs, API keys, JWT secrets) in `VITE_*` variables.

---

## Security

### What Is Protected

- JWT authentication for all case/entity/lead/graph endpoints
- Rate limiting: 5 login/minute, 3 verification/15 minutes
- Passwords hashed with bcrypt
- Production rejects weak JWT secrets
- Production rejects `EMAIL_PROVIDER=console`
- CORS restricted to configured origins
- No stack traces in production error responses
- No database credentials, JWT secrets, or API keys exposed to frontend
- Verification tokens: only hashes stored, raw tokens never logged or returned in API responses
- DemoEmailProvider never exposes raw tokens

### What to Change for Real Deployment

- Set strong `SECRET_KEY`
- Change all demo passwords
- Set `EMAIL_PROVIDER=smtp` with real SMTP credentials
- Configure `CORS_ORIGINS` to your exact frontend URL
- Remove or restrict API docs (`/api/docs`) if desired

---

## Troubleshooting

### Backend won't start

- Check Render logs for startup errors
- Verify `DATABASE_URL` uses the correct driver (`asyncpg` for async)
- Verify `SECRET_KEY` is set and not the default placeholder
- Run `alembic upgrade head` to ensure database schema is current

### Frontend shows "Unable to connect"

- Verify `VITE_API_BASE_URL` is set correctly at build time
- Check that the backend service is running (not spun down)
- Check CORS settings match the frontend URL exactly

### Database connection refused

- Ensure Supabase project is not paused (free tier pauses after 7 days)
- Verify the connection string includes `sslmode=require`
- Check `DATABASE_URL_SYNC` for Alembic migrations

### Cold start takes long

- Expected on Render free tier (30-60 seconds)
- First request triggers the service to wake up
- Subsequent requests are fast until the 15-minute idle timeout

---

## Local Development

```bash
# Backend
cd backend
cp ../.env.example .env
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm ci
npm run dev
```

### Run Tests

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

## Disclaimer

TRACE-NET is a decision-support and intelligence-analysis prototype.
Every risk score, correlation, and recommendation must be independently
reviewed by a qualified investigator. The system does not declare anyone
a criminal. Network paths describe graph connectivity, not legal responsibility.
Temporal proximity does not establish causality. Graph centrality does not
establish criminality.
