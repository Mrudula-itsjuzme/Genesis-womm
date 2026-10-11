import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.models.directory import Club, Membership, Resource, User
from scripts.seed_demo import seed_demo
from tests.conftest import upgrade


@pytest.mark.integration
def test_demo_seed_is_repeatable_and_keeps_availability_unknown(engine: Engine) -> None:
    upgrade(engine)
    with Session(engine) as session:
        seed_demo(session, "test")
        session.commit()
        seed_demo(session, "test")
        session.commit()
        users = list(session.scalars(select(User)))
        assert len(users) == 3
        assert all(user.is_synthetic for user in users)
        assert len(list(session.scalars(select(Club)))) == 1
        assert len(list(session.scalars(select(Membership)))) == 2
        resources = list(session.scalars(select(Resource)))
        assert len(resources) == 2
        assert all(r.availability_state == "UNKNOWN" and r.is_synthetic for r in resources)
