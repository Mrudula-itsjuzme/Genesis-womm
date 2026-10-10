from uuid import uuid4

import pytest

from app.services.errors import NotFoundError
from app.services.resource_reads import ResourceReadService
from tests.fakes import InMemoryDatabase


def test_missing_resource_is_not_found() -> None:
    with pytest.raises(NotFoundError):
        ResourceReadService(InMemoryDatabase().uow).get(uuid4())
