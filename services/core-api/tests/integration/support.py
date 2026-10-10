"""SQL-level seeding helpers shared by the integration tests.

They write rows with plain SQL, deliberately bypassing the application, so a test controls
exactly what is in the database.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Connection, text

NOW = datetime(2026, 10, 10, 4, 0, tzinfo=UTC)
# Identifiers that are text by design: a request id header and a source registry id.
TEXT_IDS = {"request_id", "source_id"}
START = datetime(2026, 10, 20, 4, 30, tzinfo=UTC)
END = START + timedelta(hours=2)


def insert(conn: Connection, table: str, **columns: Any) -> None:
    names = ", ".join(columns)
    params = ", ".join(f":{name}" for name in columns)
    conn.execute(text(f"INSERT INTO core.{table} ({names}) VALUES ({params})"), columns)  # noqa: S608


def make_user(conn: Connection, *, admin: bool = False) -> UUID:
    user = uuid4()
    insert(
        conn,
        "users",
        id=user,
        email=f"{user}@example.invalid",
        display_name="Test User",
        campus_admin=admin,
        is_synthetic=True,
        created_at=NOW,
    )
    return user


def make_club(conn: Connection) -> UUID:
    club = uuid4()
    insert(conn, "clubs", id=club, name=f"Club {club}", is_synthetic=True, created_at=NOW)
    return club


def make_resource(conn: Connection, **overrides: Any) -> UUID:
    resource = uuid4()
    values: dict[str, Any] = {
        "id": resource,
        "kind": "VENUE",
        "name": f"Hall {resource}",
        "source_id": "test",
        "is_synthetic": True,
        "created_at": NOW,
    }
    values.update(overrides)
    insert(conn, "resources", **values)
    return resource


def make_evidence(conn: Connection, user: UUID) -> UUID:
    evidence = uuid4()
    insert(
        conn,
        "evidence_records",
        id=evidence,
        kind="EMAIL_REFERENCE",
        reference="mailto-archive-1",
        captured_at=NOW,
        recorded_by=user,
        created_at=NOW,
    )
    return evidence


def make_event(conn: Connection, club: UUID, user: UUID, **overrides: Any) -> UUID:
    event = uuid4()
    values: dict[str, Any] = {
        "id": event,
        "club_id": club,
        "title": "Demo Day",
        "start_at": START,
        "end_at": END,
        "status": "DRAFT",
        "revision": 1,
        "created_by": user,
        "is_synthetic": True,
        "created_at": NOW,
        "updated_at": NOW,
    }
    values.update(overrides)
    insert(conn, "events", **values)
    return event
