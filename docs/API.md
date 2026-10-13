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

#### Quick Counter Controls
```http
POST /api/v1/counters/{counter_id}/open
POST /api/v1/counters/{counter_id}/pause
POST /api/v1/counters/{counter_id}/resume
POST /api/v1/counters/{counter_id}/close
```
Dedicated operator action endpoints for opening, pausing, resuming, and closing counters.

#### Assign Operator & Services
```http
PATCH /api/v1/counters/{counter_id}/operator
PUT /api/v1/counters/{counter_id}/services
```
Assign staff operator or configure which service categories a counter serves.

---

### Queues (Metrics & Wait Time Estimation)

#### System Queue Summary
```http
GET /api/v1/queues/summary?session_id=default
```
Returns system-wide operational summary for all active service categories.
Includes live queue depths, active vs total counters, average service duration,
estimated wait time for prospective arrivals, and stalled queue detection.

**Response:**
```json
{
  "session_id": "default",
  "timestamp": "2026-10-13T10:00:00Z",
  "total_waiting": 3,
  "total_serving": 1,
  "total_active_counters": 2,
  "services": [
    {
      "service_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "service_name": "General Inquiries & Token Issuance",
      "service_code": "GEN",
      "waiting_count": 3,
      "serving_count": 1,
      "completed_count": 12,
      "skipped_count": 1,
      "cancelled_count": 0,
      "active_counters": 2,
      "total_counters": 3,
      "avg_service_duration_seconds": 180,
      "estimated_wait_for_next_arrival": 360,
      "is_stalled": false,
      "queue_status": "NORMAL",
      "next_token_display_number": "GEN-014",
      "currently_serving": [
        {
          "counter_id": "...",
          "counter_name": "Counter 1",
          "token_id": "...",
          "token_display_number": "GEN-013",
          "service_started_at": "2026-10-13T09:58:00Z",
          "duration_seconds": 120
        }
      ]
    }
  ]
}
```

#### Prospective Arrival Wait Estimate
```http
GET /api/v1/queues/{service_id}/estimate?session_id=default&priority=0
```
Calculates arrival wait estimate for a citizen considering joining this queue.

#### Service Waiting Tokens
```http
GET /api/v1/queues/{service_id}/waiting?session_id=default
```
Returns ordered list of waiting tokens with dynamic wait estimates.

---

### Notifications (Milestone 4)

#### Get Notifications for Token
```http
GET /api/v1/notifications/{token_public_id}
GET /api/v1/tokens/{token_public_id}/notifications
```
Fetches in-app notification history for a specific token (e.g. `CREATED`, `APPROACHING`, `CALLED`, `SKIPPED`, `COMPLETED`).

**Response:**
```json
[
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "token_id": "8905bfe1-95bc-4886-905e-f78fbb4cb55e",
    "type": "CALLED",
    "channel": "IN_APP",
    "status": "SENT",
    "title": "Your Turn! Token CALLED",
    "message": "Token GEN-001 has been called to Counter 1. Please proceed immediately.",
    "created_at": "2026-10-13T10:05:00Z",
    "sent_at": "2026-10-13T10:05:00Z",
    "retry_count": 0
  }
]
```

---

## Real-Time WebSockets (Milestone 4)

### Live Stream Endpoint
```http
WS /ws/live
WS /api/v1/ws/live
```

Connects to the real-time event pipeline. Clients can subscribe to system-wide session events, private citizen token updates, and counter operator streams.

#### Query Parameters:
- `session_id` (optional, default `"default"`): Scope to a operational session or branch.
- `token_public_id` (optional): Subscribe to private token notifications (e.g., approaching call alert).
- `counter_id` (optional): Scope to a physical counter's call/serve lifecycle.

#### Client Messages:
- Ping Heartbeat:
  ```json
  { "event": "PING" }
  ```
- Re-subscribe / Scope:
  ```json
  { "action": "subscribe", "token_public_id": "...", "counter_id": "..." }
  ```

#### Server Broadcast Events:
- `TOKEN_CREATED`: Emitted when any citizen creates a token.
- `TOKEN_CALLED`: Emitted when an operator calls a token to a counter.
- `TOKEN_SERVING`: Emitted when service starts.
- `TOKEN_COMPLETED`: Emitted when service finishes.
- `TOKEN_SKIPPED`: Emitted when a no-show token is skipped.
- `TOKEN_RECALLED`: Emitted when a token is recalled into waiting queue.
- `TOKEN_CANCELLED`: Emitted when a citizen cancels.
- `COUNTER_STATUS_CHANGED`: Emitted when a counter opens, pauses, resumes, or closes.
- `NOTIFICATION`: Targeted in-app notification dispatch for citizen tokens.

---

## Upcoming Endpoints

### Milestone 7 (Simulation Lab)
- `POST /api/v1/simulation/runs`
- `POST /api/v1/simulation/runs/{id}/start`

### Milestone 8 (Operational Analytics)
- `GET /api/v1/analytics/summary`
- `GET /api/v1/analytics/queues`

### Milestone 10 (AI Operations Agent)
- `POST /api/v1/agent/ask`

