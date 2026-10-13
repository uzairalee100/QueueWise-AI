# QueueWise AI — Official Demonstration & Evaluator Guide 🚀

**Tagline:** Smarter Queues. Less Waiting. Better Public Services.  
**Hackathon Track:** SC-03 — Public Service Queue and Wait-Time Optimizer  
**Project Repository:** `QueueWise-AI`  
**Test Suite Status:** 136 / 136 Tests Passing (100% Green) ✅  
**Production Build:** Clean TypeScript & Vite compilation (0 errors) ✅  

---

## 1. Executive Summary

QueueWise AI transforms congested, high-friction public service counters—such as hospitals (OPD/Pharmacy), citizen registration offices (NADRA/Passports), and municipal utility counters—into streamlined, transparent, and digitally coordinated operations.

### Key Innovations:
1. **Low-Literacy & Multilingual Accessibility**: Dual-language interface (English + Native Urdu اردو) paired with a hands-free **Voice Assistant** supporting Native Urdu, Roman Urdu (*"mera number kab aayega?"*), and English with automated speech synthesis readout.
2. **Deterministic, Dynamic Wait-Time Estimator**: Multi-server wait approximations that dynamically adjust whenever counter staffing levels change or service durations shift, tested against Poisson-distributed actuals.
3. **Zero-Hallucination AI Operations Advisor**: Supervisor decision assistant connected to read-only telemetry tools that explicitly cite database metrics and timestamps for every recommendation.
4. **Simulation Lab & M/M/c Counter Optimizer**: Stress-testing engine for challenge scenarios A through F (morning surges, counter outages, complex cases, no-shows) with algorithmic counter reallocation advice.
5. **Open Model Context Protocol (MCP) Server**: Full JSON-RPC 2.0 and REST MCP implementation enabling external AI agents (Claude Desktop, Antigravity, Cursor) to inspect queue health and execute supervised queue operations.

---

## 2. Quick Start in 60 Seconds

### Prerequisites:
- Python 3.11+
- Node.js 18+

### Step 1: Start Backend (FastAPI)
```bash
cd backend
.\venv\Scripts\Activate.ps1   # On Windows (or source venv/bin/activate on Linux/macOS)
uvicorn app.main:app --reload --port 8000
```
- API Base: `http://localhost:8000/api/v1`
- Swagger Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

### Step 2: Populate Realistic Demonstration Data
Open a second terminal window to populate a live operational state (completed tokens, serving counters, waiting line, and audit trail):
```bash
cd backend
python -m scripts.demo_seed
```
*Output: 12 completed tokens, 2 serving counters, 8 waiting citizens with priority triage, and 2 churn records.*

### Step 3: Start Frontend (React + Vite)
```bash
cd frontend
npm run dev
```
- Open `http://localhost:5173` in your browser.

---

## 3. End-to-End Walkthrough Script for Judges

| Step | Page / Feature | URL | What to Demonstrate |
|---|---|---|---|
| **1** | **Home Portal** | `/` | Responsive portal showcasing citizen services, staff operations, simulation lab, analytics, and voice assistant. Switch language between English and اردو. |
| **2** | **Citizen Kiosk** | `/kiosk` | Select a service category (General Inquiry, Document Verification, or Cash Deposit). Optionally check the **Priority Assistance** toggle (Elderly/Urgent). Click **Issue Token**. Observe the generated URL-safe public ID, human-readable display number (e.g. `GEN-025`), and scannable QR code. |
| **3** | **Live Queue Tracking** | `/track/:publicId` | Live position tracker showing citizens ahead, dynamically calculated wait time, and counter status. Test the audio chime and cancellation feature. |
| **4** | **Voice Assistant** | Top Nav / Floating Mic | Click the microphone icon or quick-prompt chips. Try spoken or typed queries in Roman Urdu: *"mera number kab aayega?"*, *"kitne log agay hain"*, or *"kahan jana hai"*. Hear the synthesized audio readout with chime hints. |
| **5** | **Staff Counter Desk** | `/staff` | Select Counter 1 or 2. Demonstrate the full token lifecycle: **Call Next** ➔ **Start Serving** (live elapsed stopwatch) ➔ **Complete Service**. Test **Skip (No-show)** and **Recall** to requeue a citizen. View real-time WebSocket event feed updating instantly without page refresh. |
| **6** | **Operational Analytics** | `/analytics` | Supervisor dashboard showing 100% computed metrics from stored database events. Review throughput, average wait, SLA compliance (< 10 min threshold), 24-hr traffic chart with peak rush hour detection, desk utilization, and immutable audit trail. |
| **7** | **Simulation Lab** | `/simulation` | Select a preset challenge scenario (Scenario B: Morning Demand Surge or Scenario C: Staff Outage). Run the discrete-event simulation. Observe dynamic estimator fidelity (predicted vs actual wait times) and click **Optimize Allocation** to generate M/M/c counter distribution recommendations. |
| **8** | **AI Operations Advisor** | `/agent` | Ask natural language operational questions: *"What is the current queue status?"*, *"Where are the bottlenecks?"*, or *"How should I allocate counters?"*. Expand the **Zero-Hallucination Grounding Drawer** to inspect real metrics cited and database timestamps. |

---

## 4. Challenge Requirements Compliance Matrix (SC-03)

| Requirement | Implementation Detail | Status | Verified In |
|---|---|:---:|---|
| **Digital Token Issuance** | Unpredictable, URL-safe public IDs with human-readable sequence numbers (`GEN-001`, `DOC-002`). Idempotency key protection prevents double-issuance on network retries. Priority triage support. | ✅ | `test_api_tokens.py`, `test_queue_engine.py` |
| **Queue Position Tracking** | Dynamic rank calculation based on arrival time, service category, and priority triage level. Recalculates in real-time as counters call and complete tokens. | ✅ | `test_citizen_experience.py`, `test_queue_engine.py` |
| **Wait-Time Estimation** | Closed-form multi-server wait estimator incorporating active counter count, category service durations, and historical rolling averages. Recalculates dynamically on staffing changes. | ✅ | `test_wait_estimator.py` |
| **Counter Management** | Complete state machine (`OPEN_IDLE`, `OPEN_SERVING`, `PAUSED`, `CLOSED`). Invariant rules strictly prevent closing while serving or double-serving a single citizen. | ✅ | `test_counter_ops.py`, `test_staff_dashboard.py` |
| **Real-Time Push & Alerts** | Bidirectional WebSocket communication (`/ws`) with private citizen token channels and global broadcast channels. Automatic reconnect and HTTP polling fallback. Web Audio synthesized chimes. | ✅ | `test_websocket.py`, `test_notifications.py` |
| **Operational Analytics** | Zero mock data. Computes average/median/P95 wait times, SLA compliance % (< 10 min threshold), hourly traffic trends, rush hour detection, and counter utilization directly from `Token` and `ServiceEvent` ORM tables. | ✅ | `test_analytics.py` |
| **Simulation Lab** | Deterministic discrete-event simulation engine with pseudo-random seed reproducibility. Implements challenge scenarios A through F and compares predicted wait times against Poisson actuals. | ✅ | `test_simulation_lab.py` |
| **Resource Optimizer** | M/M/c multi-server queue theoretical solver using offered load (Erlangs) to optimize counter-to-service assignments and minimize citizen wait times. | ✅ | `test_simulation_lab.py` |
| **AI Grounding (Zero Hallucination)** | LangGraph-compatible operations advisor querying read-only database telemetry tools. Every response includes structured metadata citing source metrics, counts, and timestamps. | ✅ | `test_ai_agent.py` |
| **Model Context Protocol (MCP)** | Open MCP standard implementation over JSON-RPC 2.0 (`/api/v1/mcp/rpc`) and REST (`/api/v1/mcp/invoke`) exposing 7 queue management tools for external agentic IDEs and models. | ✅ | `test_mcp_server.py` |
| **Voice & Multilingual** | Full English, Native Urdu (اردو), and Roman Urdu support. Voice intent classifier, token extraction, Web Speech API speech-to-text, and browser audio speech synthesis. | ✅ | `test_voice_adapter.py` |
| **Security & Privacy** | Public token endpoints do not leak citizen contact info or internal sequential primary keys. SQL injection resilient, Pydantic v2 input validation, read-only telemetry tools. | ✅ | `test_demo_and_security.py` |

---

## 5. Automated Test Suite Metrics

All 15 test suites pass cleanly across unit, integration, invariant, and API levels:

```
tests/test_ai_agent.py ................................                  [ 23%] (32 tests)
tests/test_analytics.py .........                                        [ 30%] (9 tests)
tests/test_api_tokens.py ......                                          [ 34%] (6 tests)
tests/test_citizen_experience.py ...                                     [ 36%] (3 tests)
tests/test_counter_ops.py ....                                           [ 39%] (4 tests)
tests/test_demo_and_security.py .....                                    [ 43%] (5 tests)
tests/test_health.py ...                                                 [ 45%] (3 tests)
tests/test_mcp_server.py ...........                                     [ 53%] (11 tests)
tests/test_notifications.py ....                                         [ 56%] (4 tests)
tests/test_queue_engine.py ...........                                   [ 64%] (11 tests)
tests/test_simulation_lab.py .................                           [ 77%] (17 tests)
tests/test_staff_dashboard.py ...............                            [ 88%] (15 tests)
tests/test_voice_adapter.py ........                                     [ 94%] (8 tests)
tests/test_wait_estimator.py .....                                       [ 97%] (5 tests)
tests/test_websocket.py ...                                              [100%] (3 tests)

=========================== 136 passed in 12.09s ============================
```

To run the complete suite locally:
```bash
cd backend
pytest -v
```

---

## 6. Architecture & Data Invariants

```
   ┌────────────────────────────────────────────────────────┐
   │         React Frontend (Vite + TypeScript + Tailwind)  │
   │  ┌──────────┬───────────┬──────────────┬────────────┐  │
   │  │  Kiosk   │ Live Track│  Staff Desk  │ Analytics  │  │
   │  │  /kiosk  │ /track/:id│    /staff    │ /analytics │  │
   │  └────┬─────┴─────┬─────┴──────┬───────┴─────┬──────┘  │
   │       │           │            │             │         │
   │       │   REST API (/api/v1) + WebSocket (/ws)         │
   └───────┼───────────┼────────────┼─────────────┼─────────┘
           ▼           ▼            ▼             ▼
   ┌────────────────────────────────────────────────────────┐
   │              FastAPI Modular Monolith                  │
   │  ┌──────────────┐ ┌───────────────┐ ┌───────────────┐  │
   │  │ Queue Engine │ │Wait Estimator │ │Counter Optimizer│ │
   │  └──────┬───────┘ └───────┬───────┘ └───────┬───────┘  │
   │  ┌──────┴───────┐ ┌───────┴───────┐ ┌───────┴───────┐  │
   │  │  MCP Server  │ │ Voice Adapter │ │   AI Advisor  │  │
   │  └──────────────┘ └───────────────┘ └───────────────┘  │
   │                           │                            │
   │                 SQLAlchemy Async ORM                   │
   └───────────────────────────┼────────────────────────────┘
                               ▼
               SQLite (Dev/Demo) / PostgreSQL (Prod)
```

- **Invariant 1**: A token can only be served by one counter at any given time.
- **Invariant 2**: A counter in `CLOSED` or `PAUSED` state cannot call or serve tokens.
- **Invariant 3**: Completed or cancelled tokens cannot be re-opened, called, or modified.
- **Invariant 4**: Public token lookup exposes only safe tracking attributes (`public_id`, `display_number`, `position`, `estimated_wait`), never sequential database IDs or contact info.
- **Invariant 5**: AI telemetry and MCP tools execute read-only queries with zero side-effects.

---

> [!TIP]
> To reset and re-seed the live demonstration at any time during a live presentation, simply run:
> `python -m scripts.demo_seed`
