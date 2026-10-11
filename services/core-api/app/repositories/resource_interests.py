"""SQLAlchemy storage for private resource-interest records."""

from sqlalchemy.orm import Session

from app.models.directory import ResourceInterest
from app.services.resource_interests import ResourceInterestRecord


class SqlResourceInterestStore:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, record: ResourceInterestRecord) -> None:
        self._session.add(ResourceInterest(**vars(record)))
