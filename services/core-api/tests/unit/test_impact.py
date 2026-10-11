from uuid import UUID

from app.domain.impact import Dependency, impact_for


def test_matches_only_changed_fields_and_groups_by_item() -> None:
    item = UUID(int=1)
    dependencies = [
        Dependency(item, "COMMITMENT", "Venue request", "REQUESTED", "start_at"),
        Dependency(item, "COMMITMENT", "Venue request", "REQUESTED", "resource_id"),
        Dependency(UUID(int=2), "TASK", "Catering", "OPEN", "expected_attendance"),
    ]
    impacts = impact_for({"start_at", "resource_id"}, dependencies)
    assert len(impacts) == 1
    assert impacts[0].dependent_id == item
    assert impacts[0].changed_fields == ("resource_id", "start_at")
    assert impacts[0].revalidation_required


def test_closed_items_and_unchanged_fields_are_not_affected() -> None:
    assert (
        impact_for({"start_at"}, [Dependency(UUID(int=1), "TASK", "Done", "CLOSED", "start_at")])
        == ()
    )
    assert impact_for(set(), [Dependency(UUID(int=2), "TASK", "Open", "OPEN", "start_at")]) == ()


def test_results_are_stable_and_duplicate_bindings_do_not_duplicate_reasons() -> None:
    dependency = Dependency(UUID(int=2), "TASK", "Schedule speaker", "OPEN", "end_at")
    assert impact_for({"end_at"}, [dependency, dependency]) == impact_for({"end_at"}, [dependency])
