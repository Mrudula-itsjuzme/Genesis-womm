import pytest
from pydantic import ValidationError

from app.schemas.changes import ChangeFields, DependencyCreate, StageChange


def test_partial_changes_preserve_omitted_versus_explicit_null() -> None:
    request = StageChange(
        expected_revision=1, reason="Clear venue", changes=ChangeFields(resource_id=None)
    )
    assert request.changes.model_dump(exclude_unset=True) == {"resource_id": None}


@pytest.mark.parametrize(
    "changes",
    [
        {},
        {"status": "CONFIRMED"},
        {"start_at": None},
        {"start_at": "2026-10-11T10:00:00"},
        {"expected_attendance": True},
        {"expected_attendance": -1},
    ],
)
def test_invalid_change_fields_are_rejected(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ChangeFields.model_validate(changes)


def test_dependencies_cannot_claim_official_status_or_duplicate_bindings() -> None:
    with pytest.raises(ValidationError):
        DependencyCreate.model_validate(
            {
                "kind": "COMMITMENT",
                "title": "Venue",
                "field_paths": ["start_at"],
                "status": "CONFIRMED",
            }
        )
    with pytest.raises(ValidationError):
        DependencyCreate.model_validate(
            {"kind": "TASK", "title": "Speaker", "field_paths": ["start_at", "start_at"]}
        )
