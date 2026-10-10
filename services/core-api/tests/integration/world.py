"""A seeded campus and the helpers to drive the write path against PostgreSQL."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.domain.authz import Actor
from app.domain.enums import EventStatus
from app.domain.scheduling import Policy
from app.domain.time import FixedClock
from app.repositories.directory import SqlActorReader
from app.repositories.unit_of_work import SqlUnitOfWork
from app.services.schedule_store import ScheduleUnitOfWork
from app.services.schedule_write import (
    EvidenceInput,
    NewEvent,
    RequestContext,
    ScheduleWriteService,
    WriteResult,
)
from tests.conftest import upgrade
from tests.integration.support import NOW, insert, make_club, make_resource, make_user

IST = timezone(timedelta(hours=5, minutes=30))
E = EventStatus
PROOF = EvidenceInput(
    kind="EMAIL_REFERENCE", reference="archive/2026-10-09/venue-ok", issuer="OSA", captured_at=NOW
)
Slot = tuple[int, int]


def at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, 20, hour, minute, tzinfo=IST)


class RandomIds:
    """Thread-safe ids, so services running in parallel can never collide on a primary key."""

    def new_id(self) -> UUID:
        return uuid4()


@dataclass
class World:
    engine: Engine
    svc: ScheduleWriteService
    factory: sessionmaker[Session]
    club_a: UUID
    club_b: UUID
    hall: UUID
    lab: UUID
    organizer: Actor
    club_admin: Actor
    other: Actor
    campus: Actor

    def count(self, table: str, where: str = "true") -> int:
        statement = f"SELECT count(*) FROM core.{table} WHERE {where}"  # noqa: S608
        with self.engine.connect() as conn:
            return int(conn.execute(text(statement)).scalar_one())

    def service_over(self, uow_factory: Callable[[], ScheduleUnitOfWork]) -> ScheduleWriteService:
        return build_service(uow_factory)


def build_service(uow_factory: Callable[[], ScheduleUnitOfWork]) -> ScheduleWriteService:
    return ScheduleWriteService(
        uow_factory,
        clock=FixedClock(NOW),
        ids=RandomIds(),
        policy=Policy(campus_gap=timedelta(minutes=120)),
    )


def make_world(engine: Engine) -> World:
    upgrade(engine)
    with engine.begin() as conn:
        club_a, club_b = make_club(conn), make_club(conn)
        hall, lab = make_resource(conn), make_resource(conn)
        users = {
            name: make_user(conn, admin=(name == "campus"))
            for name in ("organizer", "club_admin", "other", "campus")
        }
        for name, club, role in (
            ("organizer", club_a, "ORGANIZER"),
            ("club_admin", club_a, "CLUB_ADMIN"),
            ("other", club_b, "ORGANIZER"),
        ):
            insert(
                conn,
                "memberships",
                user_id=users[name],
                club_id=club,
                role=role,
                created_at=NOW,
            )
    factory = sessionmaker(engine, expire_on_commit=False)

    def actor(name: str) -> Actor:
        with factory() as session:
            loaded = SqlActorReader(session).load_actor(users[name])
        assert loaded is not None
        return loaded

    return World(
        engine=engine,
        svc=build_service(lambda: SqlUnitOfWork(factory)),
        factory=factory,
        club_a=club_a,
        club_b=club_b,
        hall=hall,
        lab=lab,
        organizer=actor("organizer"),
        club_admin=actor("club_admin"),
        other=actor("other"),
        campus=actor("campus"),
    )


def ctx(actor: Actor, key: str | None = None, request_id: str = "req-1") -> RequestContext:
    return RequestContext(actor=actor, request_id=request_id, idempotency_key=key)


def draft(
    w: World,
    actor: Actor | None = None,
    *,
    start: Slot = (10, 0),
    end: Slot = (12, 0),
    venue: UUID | None = None,
    club: UUID | None = None,
) -> WriteResult:
    command = NewEvent(
        club_id=club or w.club_a,
        title="Robotics Demo Day",
        start_at=at(*start),
        end_at=at(*end),
        resource_id=venue if venue is not None else w.hall,
    )
    return w.svc.create_event(ctx(actor or w.organizer), command)


def advance(w: World, event: WriteResult, *steps: tuple[EventStatus, Actor]) -> WriteResult:
    for target, actor in steps:
        event = w.svc.transition_event(
            ctx(actor),
            event.event.id,
            target,
            expected_revision=event.event.revision,
            evidence=PROOF if target is E.CONFIRMED else None,
        )
    return event


def submitted(
    w: World,
    actor: Actor | None = None,
    *,
    start: Slot = (10, 0),
    end: Slot = (12, 0),
    venue: UUID | None = None,
    club: UUID | None = None,
) -> WriteResult:
    owner = actor or w.organizer
    created = draft(w, owner, start=start, end=end, venue=venue, club=club)
    return advance(w, created, (E.PROPOSED, owner), (E.SUBMITTED, owner))


def confirmed(
    w: World,
    actor: Actor | None = None,
    *,
    start: Slot = (10, 0),
    end: Slot = (12, 0),
    venue: UUID | None = None,
    club: UUID | None = None,
) -> WriteResult:
    ready = submitted(w, actor, start=start, end=end, venue=venue, club=club)
    return advance(w, ready, (E.CONFIRMED, w.campus))
