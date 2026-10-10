import pytest
from datetime import datetime, timedelta
from app.domain.scheduling import check_intervals_overlap, check_campus_gap_violation

def test_intervals_overlap():
    base = datetime(2026, 10, 10, 9, 0)
    
    # 09:00-11:00 and 10:00-12:00 -> overlap
    assert check_intervals_overlap(
        base, base + timedelta(hours=2),
        base + timedelta(hours=1), base + timedelta(hours=3)
    ) == True

    # 09:00-11:00 and 11:00-13:00 -> no overlap (half-open intervals)
    assert check_intervals_overlap(
        base, base + timedelta(hours=2),
        base + timedelta(hours=2), base + timedelta(hours=4)
    ) == False

def test_campus_gap_violation_exact_gap():
    base = datetime(2026, 10, 10, 9, 0)
    
    # 09:00-11:00 and 13:00-14:00 (exactly 120 mins gap) -> no violation
    assert check_campus_gap_violation(
        base, base + timedelta(hours=2),
        base + timedelta(hours=4), base + timedelta(hours=5)
    ) == False

def test_campus_gap_violation_short_gap():
    base = datetime(2026, 10, 10, 9, 0)
    
    # 09:00-11:00 and 12:59-14:00 (119 mins gap) -> violation
    assert check_campus_gap_violation(
        base, base + timedelta(hours=2),
        base + timedelta(hours=3, minutes=59), base + timedelta(hours=5)
    ) == True

def test_campus_gap_violation_overlap():
    base = datetime(2026, 10, 10, 9, 0)
    
    # Overlapping events -> violation
    assert check_campus_gap_violation(
        base, base + timedelta(hours=2),
        base + timedelta(hours=1), base + timedelta(hours=3)
    ) == True
