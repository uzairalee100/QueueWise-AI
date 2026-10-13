# QueueWise AI — Architecture

## System Overview

QueueWise AI uses a **modular monolith** architecture: a single FastAPI backend process with logically separated service modules, and a React single-page application frontend.

```
┌─────────────────────────────────────────┐
│          Frontend (React + Vite)         │
│  ┌───────┬───────┬──────┬────────────┐  │
│  │Citizen│ Staff │ Sim  │  Analytics │  │
│  │ Pages │ Dash  │ Lab  │   Charts   │  │
│  └───┬───┴───┬───┴──┬───┴──────┬─────┘  │
│      │       │      │          │         │
│      │  REST API + WebSocket   │         │
└──────┼───────┼──────┼──────────┼─────────┘
       │       │      │          │
┌──────┼───────┼──────┼──────────┼─────────┐
│      ▼       ▼      ▼          ▼         │
│  ┌─────────────────────────────────┐     │
│  │     FastAPI /api/v1 Router      │     │
│  └────────────┬────────────────────┘     │
│               │                          │
│  ┌────────────┼────────────────────┐     │
│  │     Business Service Layer      │     │
│  │                                 │     │
│  │  ┌──────────┐  ┌─────────────┐  │     │
│  │  │  Queue   │  │    Wait     │  │     │
│  │  │  Engine  │  │  Estimator  │  │     │
│  │  └──────────┘  └─────────────┘  │     │
│  │  ┌──────────┐  ┌─────────────┐  │     │
│  │  │ Counter  │  │ Notification│  │     │
│  │  │Optimizer │  │  Service    │  │     │
│  │  └──────────┘  └─────────────┘  │     │
│  │  ┌──────────┐  ┌─────────────┐  │     │
│  │  │Analytics │  │ Simulation  │  │     │
│  │  │ Service  │  │   Engine    │  │     │
│  │  └──────────┘  └─────────────┘  │     │
│  │  ┌──────────┐  ┌─────────────┐  │     │
│  │  │LangGraph │  │ MCP Tool    │  │     │
│  │  │ Agent    │  │  Server     │  │     │
│  │  └──────────┘  └─────────────┘  │     │
│  └─────────────────────────────────┘     │
│               │                          │
│  ┌────────────▼────────────────────┐     │
│  │     SQLAlchemy ORM + Alembic    │     │
│  └────────────┬────────────────────┘     │
│               │                          │
│  ┌────────────▼────────────────────┐     │
│  │  SQLite (dev) / PostgreSQL (prod)│    │
│  └─────────────────────────────────┘     │
│           Backend (FastAPI)              │
└──────────────────────────────────────────┘
```

## Key Design Decisions

### Why Modular Monolith?
- Single deployment unit — simpler for hackathon demo
- No inter-service network calls
- Shared database transactions for consistency
- Easy to extract services later if needed

### Backend Responsibility
The backend is the **single source of truth** for all queue state:
- Token state transitions are validated server-side
- Concurrent operations protected by database transactions
- Frontend displays data; it never decides queue ordering

### External Dependencies Strategy
All external services (LLM, speech, TTS) are **optional**:
- Abstracted behind provider interfaces
- Configurable via environment variables
- Core queue operations work with zero external deps
- Graceful degradation when providers are unavailable

## Token State Machine

```
WAITING → CALLED → SERVING → COMPLETED
  │         │                    
  │         ├──→ SKIPPED         
  │         │                    
  │         └──→ WAITING (recall)
  │                              
  ├──→ CANCELLED                 
  └──→ SKIPPED                   
```

All transitions enforced by backend validation. Invalid transitions return an error.

## API Design

All APIs are versioned under `/api/v1`:
- **Citizen APIs** — Public, no auth required (token lookup by public ID)
- **Staff APIs** — Require authentication and role authorization
- **Analytics APIs** — Computed from real stored events
- **Simulation APIs** — Isolated from live data
- **AI/Agent APIs** — Optional, with rule-based fallback

## Real-Time Updates

- Primary: **WebSocket** connections for live queue events
- Fallback: **HTTP polling** for environments where WebSocket isn't available
- Client reconnection with state reconciliation

## Data Flow

1. **Token Creation**: Citizen → API → Queue Engine → DB → WebSocket broadcast
2. **Token Called**: Staff → API → Queue Engine → DB → Notification → WebSocket
3. **Wait Estimate**: Queue event → Estimator recalculation → Updated estimate
4. **AI Query**: Staff → Agent → Read-only tools → Metrics → Grounded response
