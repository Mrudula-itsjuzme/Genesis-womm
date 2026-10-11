"""The demo fixture is safe, deterministic, and can be applied more than once."""

from sqlalchemy import Engine, text

from scripts.seed_demo import DEMO_USERS, seed_demo_data
from tests.conftest import upgrade


def test_demo_seed_is_idempotent_and_contains_a_venue_overlap(engine: Engine) -> None:
    upgrade(engine)

    seed_demo_data(engine)
    seed_demo_data(engine)

    with engine.connect() as connection:
        counts = {
            "users": connection.scalar(text("SELECT count(*) FROM core.users")),
            "clubs": connection.scalar(text("SELECT count(*) FROM core.clubs")),
            "resources": connection.scalar(text("SELECT count(*) FROM core.resources")),
            "events": connection.scalar(text("SELECT count(*) FROM core.events")),
        }
        demo_emails = connection.scalars(text("SELECT email FROM core.users ORDER BY email")).all()
        unsafe_rows = connection.scalar(
            text(
                "SELECT count(*) FROM core.users "
                "WHERE is_synthetic IS NOT TRUE OR email NOT LIKE '%.invalid'"
            )
        )
        venue_overlaps = connection.scalar(
            text(
                "SELECT count(*) FROM core.events first "
                "JOIN core.events second ON first.id < second.id "
                "AND first.resource_id = second.resource_id "
                "AND first.start_at < second.end_at AND first.end_at > second.start_at"
            )
        )

    assert counts == {"users": 4, "clubs": 2, "resources": 6, "events": 4}
    assert demo_emails == sorted(user.email for user in DEMO_USERS)
    assert unsafe_rows == 0
    assert venue_overlaps >= 1
