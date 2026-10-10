import pytest
from sqlalchemy import Engine

from tests.integration.world import World, make_world


@pytest.fixture
def world(engine: Engine) -> World:
    """A migrated database seeded with two clubs, two venues and four users."""
    return make_world(engine)
