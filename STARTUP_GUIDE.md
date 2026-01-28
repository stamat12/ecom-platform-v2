# ecom-platform-v2 - Startup Guide

A complete e-commerce platform with a FastAPI backend and React frontend for managing SKU inventory, product images, and JSON generation.

---

## Prerequisites

Before starting, ensure you have installed:
- **Python 3.8+** ([Download](https://www.python.org/downloads/))
- **Node.js 16+** ([Download](https://nodejs.org/))
- **npm** (comes with Node.js)

---

## Project Structure

```
ecom-platform-v2/
├── backend/          # FastAPI application (Python)
├── frontend/         # React application (JavaScript)
├── docs/             # Documentation
└── ...
```

---

## Backend Setup (FastAPI)

### 1. Navigate to Backend Directory
```bash
cd backend
```

### 2. Create Virtual Environment
```bash
python -m venv .venv
```

### 3. Activate Virtual Environment

**On Windows (Command Prompt):**
```bash
.venv\Scripts\activate
```

**On Windows (PowerShell):**
```bash
.\.venv\Scripts\Activate.ps1
```

**On macOS/Linux:**
```bash
source .venv/bin/activate
```

### 4. Install Dependencies

First, check if `requirements.txt` exists. If not, install the required packages:
```bash
pip install fastapi uvicorn python-multipart pillow openpyxl
```

Or if `requirements.txt` exists:
```bash
pip install -r requirements.txt
```

### 5. Environment Configuration

The `.env` file is already configured with:
- `INVENTORY_FILE_PATH` - Path to Excel inventory file
- `IMAGE_BASE_DIRS` - Directories containing product images
- `API_KEYS` - Google, OpenAI, eBay, Replicate API keys

**Note:** Verify paths in `.env` are correct for your system.

### 6. Start Backend Server

```bash
uvicorn app.main:app --reload
```

The API will start at: **http://localhost:8000**

**API Documentation:** http://localhost:8000/docs (Swagger UI)

---

## Frontend Setup (React + Vite)

### 1. Navigate to Frontend Directory
```bash
cd frontend
```

### 2. Install Dependencies
```bash
npm install
```

### 3. Start Development Server
```bash
npm run dev
```

The frontend will start at: **http://localhost:5173** (Vite default)

---

## Running Both Services Simultaneously

### Option 1: Two Terminal Windows

**Terminal 1 (Backend):**
```bash
cd backend
.venv\Scripts\activate  # or source .venv/bin/activate on macOS/Linux
uvicorn app.main:app --reload
```

**Terminal 2 (Frontend):**
```bash
cd frontend
npm run dev
```

### Option 2: Using a Process Manager

Install `concurrently` globally:
```bash
npm install -g concurrently
```

From the root directory, run both:
```bash
concurrently "cd backend && .venv\Scripts\activate && uvicorn app.main:app --reload" "cd frontend && npm run dev"
```

---

## Accessing the Application

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **API ReDoc:** http://localhost:8000/redoc

---

## Key Features

### SKU Management
- View all SKUs from inventory (`/skus`)
- View single SKU details (`/skus/{sku}`)
- Batch view multiple SKUs (`/skus/batch`)

### JSON Generation
- Automatic JSON status checking
- Generate JSON for individual SKUs
- Batch generation support

### Image Operations
- Image listing and viewing
- Image rotation
- Image classification
- Main image marking

### AI Enrichment
- AI-powered product detail enrichment
- Batch enrichment support
- Multiple SKU processing

---

## Backend API Endpoints

### SKU List & Management
- `GET /skus` - Get all SKUs with filtering
- `GET /skus/{sku}` - Get SKU details
- `GET /skus/columns/available` - Get available columns
- `GET /skus/columns/distinct-values` - Get distinct column values

### Images
- `GET /skus/{sku}/images` - List images for SKU
- `GET /images/{encoded_path}` - Serve image file
- `POST /skus/{sku}/rotate` - Rotate image
- `POST /classify` - Classify images

### JSON Operations
- `GET /json/status/{sku}` - Check if JSON exists
- `POST /json/generate/{sku}` - Generate JSON for SKU

### Main Images
- `POST /main-images/mark` - Mark main image
- `POST /main-images/unmark` - Unmark main image
- `POST /batch-main-images/mark` - Batch mark operations

### Product Details
- `GET /product/{sku}` - Get product detail
- `PATCH /product/{sku}` - Update product detail

### AI Enrichment
- `POST /enrich` - Enrich single SKU
- `POST /enrich-batch` - Enrich multiple SKUs
- `GET /ai-config` - Get AI configuration

---

## Troubleshooting

### Backend Issues

**Port 8000 already in use:**
```bash
uvicorn app.main:app --reload --port 8001
```

**Import errors:**
Ensure virtual environment is activated and dependencies are installed:
```bash
pip install fastapi uvicorn python-multipart pillow openpyxl
```

**Image not found errors:**
Verify `IMAGE_BASE_DIRS` paths in `.env` match your system

### Frontend Issues

**Port 5173 already in use:**
The development server will automatically try the next available port. Check terminal output.

**Dependency errors:**
Clear cache and reinstall:
```bash
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

**CORS errors:**
Ensure backend is running on port 8000. Check CORS settings in `backend/app/main.py`

---

## Building for Production

### Backend
Backend runs as-is in production with:
```bash
uvicorn app.main:app --workers 4
```

### Frontend
Build optimized production bundle:
```bash
npm run build
```

Output will be in `frontend/dist/` directory.

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
