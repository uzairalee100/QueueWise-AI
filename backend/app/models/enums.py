"""
QueueWise AI — Domain Enums

Enumerations for user roles, counter statuses, token lifecycle states,
event types, and notifications.
"""
from enum import Enum


class UserRole(str, Enum):
    """User roles for authentication and role-based access control."""
    CITIZEN = "CITIZEN"
    OPERATOR = "OPERATOR"
    SUPERVISOR = "SUPERVISOR"
    ADMIN = "ADMIN"


class CounterStatus(str, Enum):
    """Operational states of a service counter."""
    OPEN_IDLE = "OPEN_IDLE"
    OPEN_SERVING = "OPEN_SERVING"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"


class TokenStatus(str, Enum):
    """Lifecycle states of a queue token."""
    WAITING = "WAITING"
    CALLED = "CALLED"
    SERVING = "SERVING"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"


class ServiceEventType(str, Enum):
    """Audit and operational events recorded during service delivery."""
    TOKEN_CREATED = "TOKEN_CREATED"
    TOKEN_CALLED = "TOKEN_CALLED"
    TOKEN_SERVING = "TOKEN_SERVING"
    TOKEN_COMPLETED = "TOKEN_COMPLETED"
    TOKEN_SKIPPED = "TOKEN_SKIPPED"
    TOKEN_CANCELLED = "TOKEN_CANCELLED"
    TOKEN_RECALLED = "TOKEN_RECALLED"
    COUNTER_STATUS_CHANGED = "COUNTER_STATUS_CHANGED"
    OPERATOR_ASSIGNED = "OPERATOR_ASSIGNED"


class NotificationType(str, Enum):
    """Categories of notifications sent to token holders."""
    CREATED = "CREATED"
    APPROACHING = "APPROACHING"
    CALLED = "CALLED"
    SKIPPED = "SKIPPED"
    COMPLETED = "COMPLETED"


class NotificationChannel(str, Enum):
    """Delivery channels for notifications."""
    IN_APP = "IN_APP"
    BROWSER = "BROWSER"
    SMS = "SMS"


class NotificationStatus(str, Enum):
    """Delivery status of a notification."""
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class SimulationStatus(str, Enum):
    """Lifecycle of a queue simulation run."""
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    RESET = "RESET"
