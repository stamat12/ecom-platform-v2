# ecom-platform-v2 Startup Instructions

This file is the single startup runbook for local development.

## Prerequisites

- Python 3.10+
- Node.js 18+
- npm

## 1) Backend Startup

From project root:

```bash
cd backend
python -m venv .venv
```

Activate environment:

Windows PowerShell:

```bash
.\.venv\Scripts\Activate.ps1
```

Windows CMD:

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

If `requirements.txt` is missing/outdated, install minimum runtime packages:

```bash
pip install fastapi uvicorn python-multipart pillow openpyxl requests pandas
```

Run backend:

```bash
uvicorn app.main:app --reload
```

Backend URLs:

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 2) Frontend Startup

Open second terminal from project root:

```bash
cd frontend
npm install
npm run dev
```

Frontend URL:

- UI: http://localhost:5173

## 3) Required Configuration Check

Verify `backend/.env` has valid values for your machine:

- inventory file path(s)
- image base directory path(s)
- OpenAI API key
- eBay tokens/settings if using eBay features

If paths are invalid, most SKU/image endpoints will return empty or not found results.

## 4) Standard Daily Start (after first setup)

Terminal 1:

```bash
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Terminal 2:

```bash
cd frontend
npm run dev
```

## 5) Optional Quick Health Checks

Backend:

```bash
curl http://localhost:8000/docs
```

Frontend open in browser:

```text
http://localhost:5173
```

## 6) Troubleshooting

Backend port busy:

```bash
uvicorn app.main:app --reload --port 8001
```

Frontend port busy:

- Vite usually auto-selects next free port.

Dependency issues:

```bash
cd frontend
npm cache clean --force
npm install
```

Python interpreter mismatch:

- Ensure the active interpreter is `backend/.venv` before running backend commands.

---

## Documentation

Additional documentation available:
- [API Reference](./API_REFERENCE.md)
- [User Guide](./USER_GUIDE.md)
- [Architecture Compliance](./docs/ARCHITECTURE_COMPLIANCE_REPORT.md)
- [AI Enrichment Guide](./docs/AI_ENRICHMENT_GUIDE.md)

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review API documentation at http://localhost:8000/docs
3. Check existing logs in terminal output
