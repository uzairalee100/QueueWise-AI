# QueueWise AI

**Smarter Queues. Less Waiting. Better Public Services.**

QueueWise AI is an AI-assisted, real-time public service queue management platform designed for hospitals, banks, and government service counters. Citizens can obtain digital tokens, track their queue position, and receive estimated waiting times. Staff can manage counters, call tokens, and monitor live operational metrics.

> 🏆 Hackathon Track: **SC-03 — Public Service Queue and Wait-Time Optimizer**

---

## ✨ Key Features

- **Digital Token Issuance** — Citizens get unique tokens via web interface
- **Live Queue Tracking** — Real-time position and dynamic wait-time estimates
- **Counter Management** — Staff can open, pause, resume, and close service counters
- **Smart Notifications** — Alerts when your turn is approaching
- **Operational Analytics** — Metrics calculated from real service events
- **Simulation Lab** — Test demand spikes, counter changes, and service scenarios
- **AI Operations Agent** — Evidence-based recommendations via LangGraph
- **Counter Optimizer** — Deterministic allocation recommendations
- **Multilingual Voice** — English, Urdu, Roman Urdu, and Sindhi support
- **QR Code Tokens** — Scannable status pages for each token

## 🏗️ Architecture

**Modular monolith** with clear separation of concerns:

```
Frontend (React + Vite + TypeScript + Tailwind CSS)
    ↕
Backend (FastAPI + Python 3.11 + SQLAlchemy)
    ↕
Database (SQLite dev / PostgreSQL production)
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed diagrams and design decisions.

## 📁 Project Structure

```
QueueWise-AI/
├── frontend/               # React + Vite + TypeScript + Tailwind
│   ├── src/
│   │   ├── components/     # Reusable UI components
│   │   ├── pages/          # Page-level components
│   │   ├── services/       # API client & utilities
│   │   └── types/          # TypeScript type definitions
│   └── package.json
├── backend/                # FastAPI + Python
│   ├── app/
│   │   ├── api/            # REST API endpoints
│   │   ├── core/           # Config, database, logging
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   ├── services/       # Business logic services
│   │   ├── repositories/   # Data access layer
│   │   ├── simulation/     # Queue simulation engine
│   │   ├── agents/         # LangGraph AI agent
│   │   ├── mcp/            # MCP tool server
│   │   └── localization/   # Translations & voice
│   ├── tests/              # Pytest test suite
│   └── requirements.txt
├── docs/                   # Project documentation
├── docker-compose.yml      # Optional Docker setup
├── .env.example            # Environment variable template
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- **Python** 3.11+ 
- **Node.js** 18+ and npm
- **Git**

### 1. Clone & Configure

```bash
git clone <repository-url>
cd QueueWise-AI
cp .env.example .env
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\Activate.ps1
# Activate (Linux/macOS)
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the backend
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.  
API docs: `http://localhost:8000/docs`

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

The app will be available at `http://localhost:5173`.  
The Vite dev server proxies `/api/*` requests to the backend.

### 4. Verify

- Open `http://localhost:5173` — you should see the QueueWise AI home page
- Visit `http://localhost:8000/health` — should return `{"status": "healthy"}`
- Visit `http://localhost:8000/docs` — interactive API documentation

## 🧪 Running Tests

### Backend Tests

```bash
cd backend
pytest -v
```

## 🐳 Docker (Optional)

```bash
docker-compose up --build
```

## ⚙️ Environment Variables

See [`.env.example`](.env.example) for all configuration options. Key settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./queuewise.db` | Database connection string |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed frontend origins |
| `LLM_PROVIDER` | `none` | AI provider (none/openai/gemini) |
| `DEBUG` | `true` | Enable debug mode and API docs |

## 📊 Development Milestones

- [x] **M1: Foundation** — Project structure, health endpoint, frontend shell
- [x] **M2: Data & Queue Engine** — Models, migrations, token CRUD, state machine
- [x] **M3: Wait Estimator & Counters** — Dynamic estimates, counter management
- [x] **M4: Real-Time Updates & Notifications** — WebSockets live push, in-app alerts
- [x] **M5: Citizen Experience** — Mobile-first kiosk, live queue tracking, Web Audio alerts
- [x] **M6: Staff Operations Dashboard** — Counter desk, call/serve/complete/skip/recall lifecycle
- [x] **M7: Simulation Lab & Optimizer** — Scenarios A–F, estimate vs actual fidelity, M/M/c optimizer
- [ ] **M8: Operational Analytics** — Aggregated historical metrics, charts, service times
- [ ] **M9: AI Operations Agent** — LangGraph, evidence-based recommendations
- [ ] **M10: MCP & Voice** — MCP tool server, bilingual voice assistant
- [ ] **M11: Security, Demo & Delivery** — Auth review, complete test suite, demo seed

## 📝 License

Hackathon project — see team agreement for terms.
