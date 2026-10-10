"""Failures a use case can report. The API layer turns each into the standard error envelope.

Authorization, invalid-transition and missing-evidence failures come from ``domain.lifecycle``
and are re-raised unchanged; they are not duplicated here.
"""

from uuid import UUID

from app.domain.scheduling import Conflict


class ServiceError(Exception):
    """Base class for a refused request."""


class ConflictDetectedError(ServiceError):
    """A blocking conflict stopped a confirmation. Drafts and proposals never raise this."""

    def __init__(self, conflicts: list[Conflict]) -> None:
        super().__init__("the change conflicts with another confirmed event")
        self.conflicts = conflicts


class StaleRevisionError(ServiceError):
    def __init__(self, event_id: UUID, expected: int, actual: int | None = None) -> None:
        super().__init__(f"event {event_id} is at revision {actual}, not {expected}")
        self.event_id = event_id
        self.expected = expected
        self.actual = actual


class NotFoundError(ServiceError):
    def __init__(self, entity: str, entity_id: UUID) -> None:
        super().__init__(f"{entity} {entity_id} not found")
        self.entity = entity
        self.entity_id = entity_id


class IdempotencyMismatchError(ServiceError):
    """The same Idempotency-Key was reused with a different request."""


class DuplicateOverrideError(ServiceError):
    """An override for this scope and pair of events already exists."""


class InvalidRequestError(ServiceError):
    """The request is well formed but breaks a business rule, for example a blank reason."""


class AgentUnavailableError(ServiceError):
    """The planning assistant could not be reached or did not answer in time.

    The message is for logs. It may name internal hosts, so it is never sent to a client.
    """


class AgentOutputInvalidError(ServiceError):
    """The planning assistant answered, but not in the shape Core's contract allows.

    The message is for logs. It may quote the reply, so it is never sent to a client.
    """


class StorageUnavailableError(ServiceError):
    """Object storage could not be reached or refused the operation.

    The message is for logs. It may name hosts or buckets, so it is never sent to a client.
    """
