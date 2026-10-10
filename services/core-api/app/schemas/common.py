"""Wire types shared by every route."""

from datetime import datetime
from typing import Annotated, Any
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, BaseModel, Field, PlainSerializer

from app.domain.enums import ErrorCode

# The pilot campus is fixed (AGENTS.md 5.1). Conversion happens only at the wire boundary.
CAMPUS_TZ = ZoneInfo("Asia/Kolkata")


def _to_campus(value: datetime) -> datetime:
    return value.astimezone(CAMPUS_TZ)


# Input must carry an offset (naive values are rejected with 422); output is shown in IST.
CampusDatetime = Annotated[
    AwareDatetime,
    PlainSerializer(_to_campus, return_type=datetime, when_used="json"),
]


class ErrorEnvelope(BaseModel):
    """Every non-2xx response, from every service."""

    code: ErrorCode
    message: str
    details: list[dict[str, Any]] = Field(default_factory=list)
    request_id: str
