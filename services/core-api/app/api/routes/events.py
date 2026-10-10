from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ... import schemas, models
from ...database import SessionLocal
from ...domain.scheduling import check_campus_gap_violation

router = APIRouter(prefix="/api/v1/events", tags=["events"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("", response_model=schemas.EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(event: schemas.EventCreate, db: Session = Depends(get_db)):
    # Fetch existing events
    existing_events = db.query(models.Event).all()
    
    for existing in existing_events:
        if check_campus_gap_violation(
            start_a=event.start_at,
            end_a=event.end_at,
            start_b=existing.start_at,
            end_b=existing.end_at
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Event violates the 120-minute campus-wide gap rule or overlaps with an existing event."
            )
            
    db_event = models.Event(**event.model_dump())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

@router.get("", response_model=List[schemas.EventResponse])
def list_events(db: Session = Depends(get_db)):
    return db.query(models.Event).all()
