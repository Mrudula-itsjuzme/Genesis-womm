from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest

from app.domain.enums import EventStatus
from app.domain.lifecycle import NotAuthorizedError
from app.domain.scheduling import Policy
from app.repositories.unit_of_work import SqlUnitOfWork
from app.services.change_queries import ChangeQueries
from app.services.errors import InvalidRequestError, StaleRevisionError
from app.services.schedule_write import NewEvent, RequestContext
from tests.integration.world import PROOF, World, at

pytestmark = pytest.mark.integration


def test_stage_is_advisory_apply_demotes_and_revalidates_atomically(world: World) -> None:
    ctx = RequestContext(world.organizer, "stage", "stage-key")
    event = world.svc.create_event(
        ctx, NewEvent(world.club_a, "Synthetic changed event", at(10), at(12))
    ).event
    for status in (EventStatus.PROPOSED, EventStatus.SUBMITTED, EventStatus.CONFIRMED):
        event = world.svc.transition_event(
            RequestContext(world.campus, "confirm"),
            event.id,
            status,
            expected_revision=event.revision,
            evidence=PROOF,
        ).event
    item = world.svc.register_dependency(
        RequestContext(world.organizer, "dependency", "item-key"),
        event.id,
        kind="COMMITMENT",
        title="Venue request",
        field_paths=("start_at",),
    )
    untouched = world.svc.register_dependency(
        RequestContext(world.organizer, "dependency-other"),
        event.id,
        kind="TASK",
        title="Catering",
        field_paths=("expected_attendance",),
    )
    staged = world.svc.stage_change(
        RequestContext(world.organizer, "stage", "new-stage-key"),
        event.id,
        expected_revision=event.revision,
        changes={"start_at": at(11)},
        reason="Synthetic timing correction",
    )
    assert staged.status == "STAGED"
    assert world.count("event_revisions") == 4
    assert world.count("change_proposals") == 1
    assert staged.impact[0]["dependent_id"] == str(item.id)
    assert (
        world.svc.stage_change(
            RequestContext(world.organizer, "retry", "new-stage-key"),
            event.id,
            expected_revision=event.revision,
            changes={"start_at": at(11)},
            reason="Synthetic timing correction",
        ).id
        == staged.id
    )
    with pytest.raises(NotAuthorizedError):
        world.svc.apply_change(
            RequestContext(world.organizer, "unauthorized"),
            staged.id,
            expected_revision=event.revision,
        )
    applied = world.svc.apply_change(
        RequestContext(world.club_admin, "apply", "apply-key"),
        staged.id,
        expected_revision=event.revision,
    )
    assert applied.event.status == EventStatus.SUBMITTED
    assert applied.event.start_at == at(11)
    assert applied.event.verified_by is None
    assert applied.event.evidence_id is None
    assert world.count("evidence_records") == 1
    queries = ChangeQueries(
        lambda: SqlUnitOfWork(world.factory), policy=Policy(timedelta(minutes=120))
    )
    items = {row.id: row for row in queries.items(world.organizer, event.id)}
    assert items[item.id].status == "NEEDS_REVALIDATION"
    assert items[item.id].needs_revalidation
    assert not items[untouched.id].needs_revalidation
    assert queries.get(world.organizer, staged.id).status == "APPLIED"
    replay = world.svc.apply_change(
        RequestContext(world.club_admin, "retry-apply", "apply-key"),
        staged.id,
        expected_revision=event.revision,
    )
    assert replay.event.revision == applied.event.revision
    assert replay.replayed
    assert world.count("event_revisions") == 5


def test_stale_apply_leaves_proposal_and_items_unmodified(world: World) -> None:
    event = world.svc.create_event(
        RequestContext(world.organizer, "draft"),
        NewEvent(world.club_a, "Synthetic stale change", at(10), at(12)),
    ).event
    change = world.svc.stage_change(
        RequestContext(world.organizer, "stage"),
        event.id,
        expected_revision=1,
        changes={"start_at": at(11)},
        reason="Schedule correction",
    )
    world.svc.transition_event(
        RequestContext(world.organizer, "propose"),
        event.id,
        EventStatus.PROPOSED,
        expected_revision=1,
    )
    with pytest.raises(StaleRevisionError):
        world.svc.apply_change(
            RequestContext(world.club_admin, "apply"), change.id, expected_revision=1
        )
    assert world.count("change_proposals", "status = 'STAGED'") == 1
    assert world.count("event_revisions") == 2


def test_two_competing_proposals_cannot_both_apply(world: World) -> None:
    event = world.svc.create_event(
        RequestContext(world.organizer, "draft"),
        NewEvent(world.club_a, "Synthetic race", at(10), at(12)),
    ).event
    changes = [
        world.svc.stage_change(
            RequestContext(world.organizer, "stage"),
            event.id,
            expected_revision=1,
            changes={"expected_attendance": attendance},
            reason="Estimate",
        )
        for attendance in (10, 20)
    ]

    def apply(index: int) -> str:
        try:
            world.svc.apply_change(
                RequestContext(world.club_admin, "race-" + str(index)),
                changes[index].id,
                expected_revision=1,
            )
            return "applied"
        except StaleRevisionError:
            return "stale"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(apply, range(2)))
    assert sorted(results) == ["applied", "stale"]
    assert world.count("event_revisions") == 2
    assert world.count("change_proposals", "status = 'APPLIED'") == 1


def test_invalid_dependency_fields_do_not_write(world: World) -> None:
    event = world.svc.create_event(
        RequestContext(world.organizer, "draft"),
        NewEvent(world.club_a, "Synthetic dependency", at(10), at(12)),
    ).event
    with pytest.raises(InvalidRequestError):
        world.svc.register_dependency(
            RequestContext(world.organizer, "bad-dependency"),
            event.id,
            kind="TASK",
            title="Forged",
            field_paths=("status",),
        )
    assert world.count("event_items") == 0
