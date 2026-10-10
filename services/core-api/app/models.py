from sqlalchemy import Column, Integer, String, DateTime
from .database import Base

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    start_at = Column(DateTime)
    end_at = Column(DateTime)
    status = Column(String)
    venue_id = Column(Integer)

class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    capacity = Column(Integer)
    requires_approval = Column(String)

class Commitment(Base):
    __tablename__ = "commitments"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer)
    item = Column(String)
    status = Column(String)
