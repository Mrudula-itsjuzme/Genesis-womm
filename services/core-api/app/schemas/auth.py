from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.domain.enums import Role
from app.schemas.common import CampusDatetime

Email = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=320)]


class DemoLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: Email


class MembershipOut(BaseModel):
    club_id: UUID
    club_name: str
    role: Role


class UserOut(BaseModel):
    id: UUID
    email: Email
    display_name: str
    campus_admin: bool
    memberships: list[MembershipOut] = Field(default_factory=list)
    synthetic: bool


class SessionOut(BaseModel):
    access_token: str = Field(min_length=1)
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 - OAuth bearer scheme identifier
    expires_at: CampusDatetime
    user: UserOut
