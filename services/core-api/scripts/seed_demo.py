"""Create an explicit synthetic directory; never replace existing operational records.

Run after migrations: python -m scripts.seed_demo
"""

from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.directory import Club, Membership, Resource, User
from app.settings import Settings


def demo_id(name: str) -> UUID:
    return uuid5(NAMESPACE_URL, "campuscue:synthetic-demo:" + name)


def seed_demo(session: Session, app_env: str) -> None:
    if app_env not in {"local", "test", "demo"}:
        raise ValueError("synthetic seeds are allowed only in local, test, or demo")
    now = datetime.now(UTC)
    club_id = demo_id("club")
    session.execute(
        insert(Club)
        .values(id=club_id, name="Synthetic Demo Club", is_synthetic=True, created_at=now)
        .on_conflict_do_nothing()
    )
    for name, role in (
        ("organizer", "ORGANIZER"),
        ("club-admin", "CLUB_ADMIN"),
        ("campus-admin", None),
    ):
        user_id = demo_id(name)
        email = name + "@example.invalid"
        existing = session.scalar(select(User).where(User.email == email))
        if existing is not None and (existing.id != user_id or not existing.is_synthetic):
            raise ValueError("demo email conflicts with an existing directory identity")
        session.execute(
            insert(User)
            .values(
                id=user_id,
                email=email,
                display_name="Synthetic " + name,
                campus_admin=role is None,
                is_synthetic=True,
                created_at=now,
            )
            .on_conflict_do_nothing()
        )
        if role:
            session.execute(
                insert(Membership)
                .values(user_id=user_id, club_id=club_id, role=role, created_at=now)
                .on_conflict_do_nothing()
            )
    for name in ("Synthetic Hall A", "Synthetic Hall B"):
        session.execute(
            insert(Resource)
            .values(
                id=demo_id(name),
                kind="VENUE",
                name=name,
                description="Synthetic demo venue; not institutional data.",
                location="Synthetic campus",
                capacity=100,
                availability_state="UNKNOWN",
                freshness_state="UNKNOWN",
                source_id="synthetic-demo",
                source_url=None,
                collected_at=now,
                last_checked_at=None,
                is_synthetic=True,
                created_at=now,
            )
            .on_conflict_do_nothing()
        )


def main() -> None:
    settings = Settings()
    engine = create_engine(settings.database_url)
    try:
        with Session(engine) as session:
            seed_demo(session, settings.app_env)
            session.commit()
        print("Synthetic directory ready: organizer, club-admin, campus-admin @example.invalid")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
