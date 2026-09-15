# TRACE-NET Preview

## How to reproduce artifacts

1. `cd trace-net/frontend && npm install` (installs node_modules)
2. Copy `trace-net/backend/.env` from main checkout if missing

## How to run the servers

### Backend (port 8000)

```powershell
cd trace-net\backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend (port 5173)

```powershell
cd trace-net\frontend
npm run dev
```

The frontend proxies `/api/*` to `localhost:8000` via Vite config.

## Ports

- Backend: 8000
- Frontend: 5173
