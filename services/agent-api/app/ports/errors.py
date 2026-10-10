"""Typed failures that adapters raise and orchestration reacts to.

A failed tool is never described as a success (spine AD-9): orchestration catches these and
records the outcome in the trace.
"""


class PortError(Exception):
    """Base class for every failure that crosses a port."""


class DependencyUnavailableError(PortError):
    def __init__(self, service: str, reason: str = "unavailable") -> None:
        super().__init__(f"{service} is {reason}")
        self.service = service


class DeniedError(PortError):
    """The delegated user is not allowed to do this. Core decided; the Agent cannot override."""


class NotFoundError(PortError):
    pass


class StaleRevisionError(PortError):
    """The event changed after the Agent read it."""


class IdempotencyMismatchError(PortError):
    """The same Idempotency-Key was reused with a different body."""


class ContractViolationError(PortError):
    """A response did not match the contract, for example an enum value this build does not know."""
