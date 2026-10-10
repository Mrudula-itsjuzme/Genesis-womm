from datetime import datetime, timedelta

def check_intervals_overlap(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    """
    Check if two half-open intervals [start_a, end_a) and [start_b, end_b) overlap.
    Returns True if they overlap, False otherwise.
    """
    if start_a >= end_a or start_b >= end_b:
        raise ValueError("Invalid interval: start must be before end")
    
    return max(start_a, start_b) < min(end_a, end_b)

def check_campus_gap_violation(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime, required_gap_minutes: int = 120) -> bool:
    """
    Check if the gap between two intervals satisfies the required campus-wide gap.
    Returns True if there is a VIOLATION (gap is less than required_gap_minutes), False if the gap is acceptable.
    Overlapping intervals are automatically a violation.
    """
    if check_intervals_overlap(start_a, end_a, start_b, end_b):
        return True
    
    gap = timedelta(minutes=required_gap_minutes)
    
    # Gap is valid if A ends before B starts (by at least `gap`), or B ends before A starts (by at least `gap`).
    # Therefore, violation is when NOT (end_a + gap <= start_b OR end_b + gap <= start_a)
    return not (end_a + gap <= start_b or end_b + gap <= start_a)
