"""Closed vocabularies shared by every layer.

Enums are defined once here and exported through OpenAPI. Changes are additive:
never rename a value or change its meaning (AGENTS.md 11.1).
"""

from enum import StrEnum


class EventStatus(StrEnum):
    """Event lifecycle. Only CONFIRMED means an authorized actor verified it with evidence."""

    DRAFT = "DRAFT"
    PROPOSED = "PROPOSED"
    SUBMITTED = "SUBMITTED"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class CommitmentStatus(StrEnum):
    """Commitment lifecycle, separate from the event's. ACKNOWLEDGED is not CONFIRMED."""

    DRAFT = "DRAFT"
    REQUESTED = "REQUESTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    CONDITIONALLY_CONFIRMED = "CONDITIONALLY_CONFIRMED"
    CONFIRMED = "CONFIRMED"
    NEEDS_REVALIDATION = "NEEDS_REVALIDATION"
    CLOSED = "CLOSED"


class ConflictType(StrEnum):
    VENUE_OVERLAP = "VENUE_OVERLAP"
    CAMPUS_GAP_VIOLATION = "CAMPUS_GAP_VIOLATION"
    TENTATIVE_OVERLAP = "TENTATIVE_OVERLAP"
    DEPENDENCY_CONFLICT = "DEPENDENCY_CONFLICT"
    UNKNOWN_AVAILABILITY = "UNKNOWN_AVAILABILITY"


class ConflictConstraint(StrEnum):
    """The independent scheduling constraint a conflict violates."""

    VENUE_OVERLAP = "VENUE_OVERLAP"
    CAMPUS_GAP = "CAMPUS_GAP"


class Severity(StrEnum):
    """Lowercase on the wire, as in contracts/CONTRACTS.md."""

    BLOCKING = "blocking"
    WARNING = "warning"
    INFO = "info"


class OverrideScope(StrEnum):
    CAMPUS_GAP = "CAMPUS_GAP"
    VENUE_OVERLAP = "VENUE_OVERLAP"


class AvailabilityState(StrEnum):
    """UNKNOWN until evidence says otherwise; an empty calendar never means free."""

    UNKNOWN = "UNKNOWN"
    REQUESTED = "REQUESTED"
    CONFIRMED = "CONFIRMED"


class ResourceKind(StrEnum):
    VENUE = "VENUE"
    EQUIPMENT = "EQUIPMENT"
    SERVICE = "SERVICE"


class FreshnessState(StrEnum):
    """How current a sourced record is. No state implies availability (Plan 06)."""

    CURRENT = "CURRENT"
    STALE = "STALE"
    HISTORICAL = "HISTORICAL"
    PARSE_FAILED = "PARSE_FAILED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    UNKNOWN = "UNKNOWN"


class ToolOutcome(StrEnum):
    """Result of one Agent tool call, as recorded in the response trace."""

    OK = "OK"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    DENIED = "DENIED"
    INVALID_ARGUMENTS = "INVALID_ARGUMENTS"


class Role(StrEnum):
    ORGANIZER = "ORGANIZER"
    CLUB_ADMIN = "CLUB_ADMIN"
    FACULTY_ADVISOR = "FACULTY_ADVISOR"
    CAMPUS_ADMIN = "CAMPUS_ADMIN"
    STUDENT = "STUDENT"


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


class ProposalStatus(StrEnum):
    """Proposal lifecycle. Ingestion into RAG requires APPROVED status."""

    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REVISION_REQUESTED = "REVISION_REQUESTED"
    CHUNKED = "CHUNKED"
    ARCHIVED = "ARCHIVED"
