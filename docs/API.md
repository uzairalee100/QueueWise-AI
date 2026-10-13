# QueueWise AI — API Reference

## Base URL

All API endpoints are prefixed with `/api/v1`.

**Local development:** `http://localhost:8000/api/v1`

---

## System Endpoints

### Health Check

```http
GET /health
```

Returns application health status.

**Response:**
```json
{
  "status": "healthy",
  "app": "QueueWise AI",
  "version": "0.1.0",
  "environment": "development"
}
```

### API Status

```http
GET /api/v1/status
```

Returns API version and operational status.

**Response:**
```json
{
  "api_version": "v1",
  "status": "operational"
}
```

---

## Active Milestone 2 Endpoints

### Services

#### List Services
```http
GET /api/v1/services?active_only=true
```
Returns list of active institution service categories.

**Response:**
```json
[
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "General Inquiries & Token Issuance",
    "code": "GEN",
    "description": "General assistance, reception, and info desk",
    "default_duration_seconds": 180,
    "priority_policy": "FIFO",
    "is_active": true,
    "created_at": "2026-10-13T10:00:00Z"
  }
]
```

#### Create Service Category
```http
POST /api/v1/services
```
Registers a new service category.

**Request Body:**
```json
{
  "name": "Pharmacy Dispensation",
  "code": "PHARM",
  "description": "Prescription fulfillment and consultation",
  "default_duration_seconds": 240,
  "priority_policy": "FIFO",
  "is_active": true
}
```

---

### Tokens (Citizen Facing)

#### Issue Digital Token
```http
POST /api/v1/tokens
```
Issues a new queue token for a citizen. Supports duplicate request protection via `idempotency_key`.

**Request Body:**
```json
{
  "service_code": "GEN",
  "session_id": "default",
  "contact_info": "+923001234567",
  "idempotency_key": "unique-client-guid",
  "priority": 0
}
```

**Response (201 Created):**
```json
{
  "public_id": "N7qK48bW8...",
  "display_number": "GEN-001",
  "status": "WAITING",
  "service_name": "General Inquiries & Token Issuance",
  "service_code": "GEN",
  "position_ahead": 0,
  "estimated_wait_seconds": 180,
  "called_counter_name": null,
  "created_at": "2026-10-13T10:01:00Z",
  "called_at": null,
  "session_id": "default"
}
```

#### Track Token Status
```http
GET /api/v1/tokens/{public_id}
```
Public, unauthenticated status lookup for citizens with real-time position ahead and wait estimates.

**Response (200 OK):**
```json
{
  "public_id": "N7qK48bW8...",
  "display_number": "GEN-001",
  "status": "CALLED",
  "service_name": "General Inquiries & Token Issuance",
  "service_code": "GEN",
  "position_ahead": 0,
  "estimated_wait_seconds": 0,
  "called_counter_name": "Counter 1",
  "created_at": "2026-10-13T10:01:00Z",
  "called_at": "2026-10-13T10:03:00Z",
  "session_id": "default"
}
```

#### Cancel Token
```http
POST /api/v1/tokens/{public_id}/cancel?reason=Citizen+cancelled
```
Allows citizen to cancel their waiting token.

---

### Counters (Staff Facing)

#### List Counters
```http
GET /api/v1/counters
```
Returns all counters with supported services and current status.

#### Call Next Token
```http
POST /api/v1/counters/{counter_id}/call-next?session_id=default
```
Calls the next waiting token (by priority and FIFO order) to this counter. Enforces counter availability and transitions token from `WAITING` to `CALLED`.

#### Start Service
```http
POST /api/v1/counters/{counter_id}/serve
```
Transitions current called token from `CALLED` to `SERVING`.

#### Complete Service
```http
POST /api/v1/counters/{counter_id}/complete
```
Transitions serving token to `COMPLETED` and frees counter back to `OPEN_IDLE`.

#### Skip Token
```http
POST /api/v1/counters/{counter_id}/skip?reason=No-show
```
Marks called token as `SKIPPED` and frees counter back to `OPEN_IDLE`.

#### Recall Token
```http
POST /api/v1/counters/{counter_id}/recall?reason=Requeued+to+waiting
```
Requeues called token back to `WAITING` and frees counter back to `OPEN_IDLE`.

#### Update Counter Status
```http
PATCH /api/v1/counters/{counter_id}/status
```
Updates operational status (`OPEN_IDLE`, `PAUSED`, `CLOSED`). Cannot pause/close while actively serving.

---

## Upcoming Endpoints

### Milestone 3 (Wait Estimator & Live Counters)
- Dynamic wait-time recalculation on queue changes
- Queue summary metrics endpoint: `GET /api/v1/queues/summary`

### Milestone 5 (WebSockets & Real-Time)
- `WS /ws/live` - Real-time queue event push

### Milestone 6 (Analytics)
- `GET /api/v1/analytics/summary`
- `GET /api/v1/analytics/queues`

### Milestone 7 (Simulation Lab)
- `POST /api/v1/simulation/runs`
- `POST /api/v1/simulation/runs/{id}/start`

### Milestone 8 (AI Operations Agent)
- `POST /api/v1/agent/ask`
