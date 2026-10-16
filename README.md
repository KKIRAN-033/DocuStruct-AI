# INCUXAI — Autonomous Document & Tabular AI Workstation

<p align="center">
  <img src="frontend/src/assets/incux-logo.jpeg" alt="INCUXAI Logo" width="120" style="border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.15);" />
</p>

<p align="center">
  <strong>Autonomous Multi-Dataset Tabular Extraction • Multimodal Vision-OCR Fusion • Exact Decimal Verification • Multi-Model AI Orchestration</strong>
</p>

<p align="center">
  <a href="#key-innovations"><img src="https://img.shields.io/badge/Architecture-Deterministic%20%2B%20Vision%20Fusion-0052FF.svg" alt="Architecture" /></a>
  <a href="#quick-start"><img src="https://img.shields.io/badge/Stack-FastAPI%20%7C%20React%2018%20%7C%20Vite-10B981.svg" alt="Stack" /></a>
  <a href="#testing"><img src="https://img.shields.io/badge/Tests-100%25%20Passing%20(476%2B)-success.svg" alt="Tests" /></a>
  <a href="#license"><img src="https://img.shields.io/badge/Version-v2.0.0-6366F1.svg" alt="Version" /></a>
</p>

---

## 🌟 Executive Overview

**INCUXAI** is an enterprise-grade document intelligence workstation engineered for financial analysts, tax auditors, compliance officers, and data teams. It transforms complex, messy, multi-page PDFs, scanned invoices, receipts, and mobile photos into verified, ready-to-use canonical spreadsheets.

Unlike fragile regex parsers or hallucination-prone black-box LLMs, INCUXAI operates on a **Deterministic-First Authority** principle backed by an arbitrary-precision **Decimal Arithmetic Evaluator** and a resilient **Multimodal Vision AI Fallback Engine**.

---

## 🚀 Key Innovations & Architectural Novelty

### 1. Multi-Dataset Autonomous Segregation (50+ Pages)
Intelligent schema awareness dynamically detects differing column definitions across page boundaries (e.g., Orders vs. Student Records vs. Financial Expenses) within a single document. Instead of corrupting tables by forcing mismatched headers together, INCUXAI automatically splits distinct datasets into independent canonical tables with dedicated spreadsheet views.

### 2. Multi-Engine OCR & Vision AI Fusion
Combines high-speed deterministic vector geometry for crisp digital PDFs with state-of-the-art multimodal Vision AI (`google/gemini-2.5-flash`, `nvidia/nemotron-3.5-super-vl:free`) for scanned papers, mobile photos, angled receipts, and low-contrast scans.

### 3. Exact Decimal Arithmetic Verification & Quality Gates
Every number extracted is evaluated using Python's exact `Decimal` representation—binary floating-point rounding errors (`0.1 + 0.2 != 0.3`) are strictly eliminated. Cross-checks row sums against printed invoice/statement totals and flags discrepancies with color-coded provenance overlays without fabricating numbers.

### 4. 7-Tier Multi-LLM Orchestration Registry
Provider-agnostic inference across DeepSeek V3, Llama 3.3 70B, Qwen 2.5 72B, Claude 3.5 Sonnet, GPT-4o, and Gemini in strict non-destructive standby with automated latency tracking, capability probing, and circuit-breaking fallback.

### 5. Interactive Spreadsheet Grid & Inline Human-in-the-Loop Editor
Full browser-based editing experience featuring:
- In-cell live value editing
- **Add Row** with auto-populated empty schema
- **Delete Row** with instant UI refresh
- Cell Provenance Inspector showing exact bounding box coordinates `(x0, y0, x1, y1)` and source page numbers
- Discrepancy Adjudication drawer to accept or override AI proposals

### 6. Granular & Lossless Multi-Table Export
- **Individual Table Export**: Download any specific table as clean RFC 4180 CSV
- **Export All Tables (ZIP)**: Multi-CSV download package
- **Multi-Sheet Excel Workbook (`.xlsx`)**: Exports each extracted table into its own named worksheet (`Table 1 - Orders`, `Table 2 - Students`) with auto-fitted column widths and styled headers
- **Audit-Ready JSON**: Complete bounding boxes, raw values, formulas, and math verification scores

### 7. High-Capacity Enterprise Processing
- Supports files up to **50 MiB** and up to **100 pages**
- Streaming multipart file handling with strict security screening (MIME type validation, PDF header verification, malicious zip/tar protection)

---

## 🏗️ System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                   React 18 + Vite + TypeScript UI                      │
│     (Design Tokens, Interactive Grid, Provenance Inspector,            │
│      Multi-Table Exporter, Add/Edit Row Engine, Model Registry)        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP Fetch (Port 5173 -> 8000)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   FastAPI High-Performance API Adapter                 │
│                   backend/app/api/ (Port 8000)                         │
│   • POST /api/v1/extract (50 MiB cap)   • GET  /api/v1/models/status   │
│   • POST /api/v1/export/csv, excel, json• GET  /api/v1/health          │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     Deterministic Pipeline Engine                      │
│                   backend/app/pipeline.py                              │
│   1. Security Gate (50 MiB, 100 pgs) 5. Arithmetic Evaluator (Decimal) │
│   2. Page Router (Digital/Scanned)  6. Quality Gate & Reason Codes     │
│   3. Multimodal Vision Fallback     7. Header Deduplication Filter     │
│   4. Multi-Dataset Reconstructor    8. Windows Handle Cleanup Safety   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     Multi-LLM Registry & Workers                       │
│                   backend/app/llm/ (7 Providers)                       │
│   • OpenRouter, Groq, Together, DeepSeek, ZAI Providers                │
│   • Real-Time Health & Capability Probes                               │
└────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Quick Start

### Prerequisites
- **Python**: 3.11+
- **Node.js**: 18+ (LTS recommended)
- **Git**

---

### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv venv

# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp ../.env.example .env
# Edit .env and supply your OPENROUTER_API_KEY (optional for Vision AI)

# Start FastAPI development server
uvicorn app.api.main:app --host 127.0.0.1 --port 8000 --reload
```

The backend API will be available at: `http://127.0.0.1:8000` (Docs: `http://127.0.0.1:8000/docs`).

---

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start Vite development workstation
npm run dev
```

The web application will open at: `http://127.0.0.1:5173`.

---

## 🧪 Testing & Quality Assurance

INCUXAI enforces 100% test pass rates across both frontend and backend suites:

```bash
# Run all backend unit and integration tests (395+ tests)
cd backend
pytest -v

# Run all frontend component, accessibility, and E2E tests (81+ tests)
cd frontend
npm run test
```

---

## 🔒 Security & Invariants

1. **Zero Fabrication Invariant**: INCUXAI never invents numerical values or balances discrepancies artificially.
2. **Deterministic Precedence**: Coordinate-based vector extraction runs first; LLMs/Vision AI operate strictly when needed or for advisory proposals.
3. **Stateless Operations**: Document files are processed in ephemeral memory buffers with automatic handle cleanup to prevent file locking on Windows and Linux.
4. **Input Sanitization**: Rejects non-PDF/unsupported image files, nested bomb archives, and files exceeding 50 MiB.

---

## 📄 License

Proprietary enterprise software. Built for autonomous enterprise document automation.
