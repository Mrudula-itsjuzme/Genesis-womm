"""Wire enums, mirrored from the producing services' contracts.

Core owns these vocabularies (spine AD-18). A contract test fails if a value here differs
from `contracts/schemas/shared.schema.json`, and the clients raise a typed error on a value
they do not know instead of ignoring it.
"""

from enum import StrEnum


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    CONFLICT_DETECTED = "CONFLICT_DETECTED"
    STALE_REVISION = "STALE_REVISION"
    IDEMPOTENCY_MISMATCH = "IDEMPOTENCY_MISMATCH"
    INVALID_TRANSITION = "INVALID_TRANSITION"
    DUPLICATE_OVERRIDE = "DUPLICATE_OVERRIDE"
    EVIDENCE_REQUIRED = "EVIDENCE_REQUIRED"
    DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"
    AGENT_OUTPUT_INVALID = "AGENT_OUTPUT_INVALID"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class EventStatus(StrEnum):
    DRAFT = "DRAFT"
    PROPOSED = "PROPOSED"
    SUBMITTED = "SUBMITTED"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class AvailabilityState(StrEnum):
    UNKNOWN = "UNKNOWN"
    REQUESTED = "REQUESTED"
    CONFIRMED = "CONFIRMED"


class ConflictType(StrEnum):
    VENUE_OVERLAP = "VENUE_OVERLAP"
    CAMPUS_GAP_VIOLATION = "CAMPUS_GAP_VIOLATION"
    TENTATIVE_OVERLAP = "TENTATIVE_OVERLAP"
    DEPENDENCY_CONFLICT = "DEPENDENCY_CONFLICT"
    UNKNOWN_AVAILABILITY = "UNKNOWN_AVAILABILITY"


class ConflictConstraint(StrEnum):
    VENUE_OVERLAP = "VENUE_OVERLAP"
    CAMPUS_GAP = "CAMPUS_GAP"


class Severity(StrEnum):
    BLOCKING = "blocking"
    WARNING = "warning"
    INFO = "info"


class AgentActionType(StrEnum):
    """What the Agent may propose. There is no booking, confirmation or override type."""

    CREATE_EVENT_DRAFT = "CREATE_EVENT_DRAFT"
    REQUEST_EVENT_CHANGE = "REQUEST_EVENT_CHANGE"
    RECORD_COMMITMENT = "RECORD_COMMITMENT"
    CREATE_FOLLOWUP_DRAFT = "CREATE_FOLLOWUP_DRAFT"


class AgentActionStatus(StrEnum):
    PROPOSED = "PROPOSED"
    EXECUTED = "EXECUTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class ToolOutcome(StrEnum):
    OK = "OK"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    DENIED = "DENIED"
    INVALID_ARGUMENTS = "INVALID_ARGUMENTS"


class AccessLevel(StrEnum):
    """RAG document access class. Core derives it from the user's role and sends it to the
    Agent; it is never taken from model output or user text (spine AD-12)."""

    CAMPUS_PUBLIC = "CAMPUS_PUBLIC"
