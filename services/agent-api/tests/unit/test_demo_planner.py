"""The offline planner: the same workflow as the real prompt, with no network and no model.

It exists so a demo survives a rate limit or no internet. It reads the same campus context the
model reads, asks for what is missing, explains conflicts instead of filing over them, and files
a proposal only after a clean check or an explicit go-ahead.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest

from app.clients.fakes import FakeCoreClient, FakeRagClient
from app.orchestration.context import render_context
from app.orchestration.engine import OrchestrationEngine
from app.ports.clock import FixedClock
from app.ports.core import CallContext
from app.ports.llm import LlmResponse
from app.providers.demo_planner import plan
from app.providers.fakes import FakeLlmProvider
from app.schemas.chat import ChatMessage, TurnContext
from app.schemas.core import Conflict
from app.schemas.enums import ConflictConstraint, ConflictType, Severity

EVENTS_CLUB = UUID("20000000-0000-4000-8000-000000000001")
ROBOTICS_CLUB = UUID("20000000-0000-4000-8000-000000000002")
AUDITORIUM = UUID("30000000-0000-4000-8000-000000000001")
SEMINAR = UUID("30000000-0000-4000-8000-000000000002")
NOW = datetime(2026, 11, 1, 3, 0, tzinfo=UTC)
CTX = CallContext(request_id="req-1", delegation_token="t.o.k")


def system_prompt(*, clubs: int = 2) -> str:
    rows: list[dict[str, Any]] = [
        {"id": str(EVENTS_CLUB), "name": "Synthetic Events Club", "role": "ORGANIZER"},
        {"id": str(ROBOTICS_CLUB), "name": "Synthetic Robotics Club", "role": "ORGANIZER"},
    ]
    context = TurnContext.model_validate(
        {
            "now": NOW.isoformat(),
            "timezone": "Asia/Kolkata",
            "clubs": rows[:clubs],
            "venues": [
                {
                    "id": str(AUDITORIUM),
                    "name": "Synthetic Main Auditorium",
                    "capacity": 450,
                    "availability": "CONFIRMED",
                },
                {
                    "id": str(SEMINAR),
                    "name": "Synthetic Seminar Hall",
                    "capacity": 120,
                    "availability": "REQUESTED",
                },
            ],
        }
    )
    return "RULES\n" + render_context(context)


def user(text: str) -> ChatMessage:
    return ChatMessage(role="user", content=text)


def assistant(text: str) -> ChatMessage:
    return ChatMessage(role="assistant", content=text)


def tool(name: str, text: str) -> ChatMessage:
    return ChatMessage(role="user", content=f"[Tool {name}]: {text}")


FULL = (
    "Plan a Guest Workshop for the Synthetic Robotics Club in the Synthetic Main Auditorium "
    "on 24 November 2026 from 3pm to 5pm."
)


def check_args(response: LlmResponse) -> dict[str, Any]:
    [call] = response.tool_calls
    assert call.name == "check_event_conflicts"
    return call.arguments


# ---- reading the request -----------------------------------------------------------------


def test_a_complete_request_is_checked_with_real_ids_and_campus_times() -> None:
    args = check_args(plan([user(FULL)], system_prompt()))

    assert args == {
        "club_id": str(ROBOTICS_CLUB),
        "resource_id": str(AUDITORIUM),
        "start_at": "2026-11-24T15:00:00+05:30",
        "end_at": "2026-11-24T17:00:00+05:30",
    }


@pytest.mark.parametrize(
    ("text", "start", "end"),
    [
        ("on 2026-12-05 from 09:00 to 10:30", "09:00", "10:30"),
        ("on 5 December 2026 from 10am to 12pm", "10:00", "12:00"),
        ("on December 5, 2026 from 3 to 5pm", "15:00", "17:00"),
        ("on 5th Dec 2026 from 9:30am to 11am", "09:30", "11:00"),
    ],
)
def test_dates_and_times_are_read_in_the_ways_people_write_them(
    text: str, start: str, end: str
) -> None:
    request = f"Plan a talk for the Synthetic Events Club in the Seminar Hall {text}."

    args = check_args(plan([user(request)], system_prompt()))

    assert (args["start_at"], args["end_at"]) == (
        f"2026-12-05T{start}:00+05:30",
        f"2026-12-05T{end}:00+05:30",
    )


def test_a_venue_is_found_by_its_distinctive_word() -> None:
    request = FULL.replace("Synthetic Main Auditorium", "seminar hall")

    assert check_args(plan([user(request)], system_prompt()))["resource_id"] == str(SEMINAR)


# ---- asking instead of guessing ----------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expects"),
    [
        ("I want to host a hackathon.", "club"),
        ("Plan a talk for the Synthetic Events Club in the Seminar Hall.", "date"),
        (
            "Plan a talk for the Synthetic Events Club on 24 November 2026 from 3pm to 5pm.",
            "venue",
        ),
    ],
    ids=["no club", "no date or time", "no venue"],
)
def test_one_question_is_asked_for_what_is_missing(text: str, expects: str) -> None:
    reply = plan([user(text)], system_prompt())

    assert reply.tool_calls == []
    assert reply.text is not None
    assert expects in reply.text.lower()
    assert reply.text.count("?") == 1


def test_a_person_with_one_club_is_not_asked_which() -> None:
    request = FULL.replace("for the Synthetic Robotics Club ", "")

    args = check_args(plan([user(request)], system_prompt(clubs=1)))

    assert args["club_id"] == str(EVENTS_CLUB)


def test_something_that_is_not_planning_gets_a_short_honest_answer() -> None:
    reply = plan([user("What is the cafeteria menu today?")], system_prompt())

    assert reply.tool_calls == []
    assert reply.text is not None
    assert "plan" in reply.text.lower()
    assert "offline" in reply.text.lower()


# ---- reading Core's answer ---------------------------------------------------------------


def test_a_clean_check_is_followed_by_a_proposal_with_a_title_from_the_request() -> None:
    history = [
        user(FULL),
        assistant("Calling tools..."),
        tool("check_event_conflicts", "No conflicts detected. The slot appears available."),
    ]

    [call] = plan(history, system_prompt()).tool_calls

    assert call.name == "file_event_draft_proposal"
    assert call.arguments["payload"] == {
        "club_id": str(ROBOTICS_CLUB),
        "title": "Guest Workshop",
        "start_at": "2026-11-24T15:00:00+05:30",
        "end_at": "2026-11-24T17:00:00+05:30",
        "resource_id": str(AUDITORIUM),
    }


def test_an_info_notice_alone_does_not_stop_a_proposal() -> None:
    notice = "Found 1 conflict(s):\n  - [INFO] UNKNOWN_AVAILABILITY: nobody confirmed it."
    history = [user(FULL), assistant("Calling tools..."), tool("check_event_conflicts", notice)]

    assert plan(history, system_prompt()).tool_calls[0].name == "file_event_draft_proposal"


def test_a_warning_is_explained_and_nothing_is_filed() -> None:
    warning = (
        "Found 1 conflict(s):\n  - [WARNING] TENTATIVE_OVERLAP: Overlaps "
        '"Synthetic Guest Lecture" (CONFIRMED, Fri 20 Nov 09:30-11:30 IST).'
    )
    history = [user(FULL), assistant("Calling tools..."), tool("check_event_conflicts", warning)]

    reply = plan(history, system_prompt())

    assert reply.tool_calls == []
    assert reply.text is not None
    assert "Synthetic Guest Lecture" in reply.text
    assert "anyway" in reply.text.lower()


def test_an_explicit_go_ahead_after_a_warning_files_the_same_slot() -> None:
    history = [
        user(FULL),
        assistant("I found conflicts. Want me to propose it anyway?"),
        user("Yes, go ahead anyway."),
    ]

    [call] = plan(history, system_prompt()).tool_calls

    assert call.name == "file_event_draft_proposal"
    assert call.arguments["payload"]["start_at"] == "2026-11-24T15:00:00+05:30"


def test_a_go_ahead_with_nothing_to_go_ahead_with_is_not_a_proposal() -> None:
    assert plan([user("go ahead")], system_prompt()).tool_calls == []


def test_after_filing_it_says_proposed_and_that_a_person_must_confirm() -> None:
    history = [
        user(FULL),
        assistant("Calling tools..."),
        tool("file_event_draft_proposal", "Draft proposal filed (action_id=1, status=PROPOSED)."),
    ]

    reply = plan(history, system_prompt())

    assert reply.tool_calls == []
    assert reply.text is not None
    assert "PROPOSED" in reply.text
    assert "confirm" in reply.text.lower()
    assert "booked" not in reply.text.lower().replace("not booked", "")


def test_a_failed_tool_is_reported_as_failed() -> None:
    history = [user(FULL), assistant("Calling tools..."), tool("check_event_conflicts", "Error: x")]

    reply = plan(history, system_prompt())

    assert reply.tool_calls == []
    assert reply.text is not None
    assert "could not" in reply.text.lower()


# ---- the whole turn through the engine ---------------------------------------------------


async def run_turn(history: list[ChatMessage], core: FakeCoreClient) -> Any:
    llm = FakeLlmProvider(demo_mode=True)
    engine = OrchestrationEngine(
        llm=llm, core=core, rag=FakeRagClient(corpus=[]), clock=FixedClock(NOW)
    )
    return await engine.run(history, CTX, system_prompt())


async def test_a_clean_slot_ends_in_one_real_proposal() -> None:
    core = FakeCoreClient(clock=FixedClock(NOW))

    reply = await run_turn([user(FULL)], core)

    assert [a.status for a in reply.proposed_actions] == ["PROPOSED"]
    assert [t.tool for t in reply.trace] == ["check_event_conflicts", "file_event_draft_proposal"]


async def test_a_colliding_slot_ends_with_an_explanation_and_no_proposal() -> None:
    clash = Conflict(
        type=ConflictType.TENTATIVE_OVERLAP,
        severity=Severity.WARNING,
        constraint=ConflictConstraint.VENUE_OVERLAP,
        event_ids=[UUID(int=0), UUID(int=5)],
        start_at=NOW,
        end_at=NOW,
        message="Another event is proposed for the same venue.",
        override_required=False,
    )
    core = FakeCoreClient(clock=FixedClock(NOW), conflicts=[clash])

    reply = await run_turn([user(FULL)], core)

    assert reply.proposed_actions == []
    assert "TENTATIVE_OVERLAP" in reply.message


# ---- a conversation, not just a sentence -------------------------------------------------

CLASH = FULL.replace("24 November 2026 from 3pm to 5pm", "20 November 2026 from 10am to 12pm")


def test_a_later_date_and_time_replace_the_earlier_ones_but_the_venue_is_kept() -> None:
    history = [
        user(CLASH),
        assistant("Core found conflicts for that slot. Should I propose it anyway?"),
        user("Ok, try 24 November 2026, 3pm to 5pm in the same one instead."),
    ]

    args = check_args(plan(history, system_prompt()))

    assert args["start_at"] == "2026-11-24T15:00:00+05:30"
    assert args["resource_id"] == str(AUDITORIUM)


def test_a_time_range_written_with_an_en_dash_is_understood() -> None:
    dash = chr(0x2013)
    request = FULL.replace("from 3pm to 5pm", f"from 3pm {dash} 5pm")

    assert check_args(plan([user(request)], system_prompt()))["start_at"].endswith("15:00:00+05:30")


def test_a_go_ahead_does_not_file_unless_conflicts_were_just_explained() -> None:
    history = [user(FULL), assistant("Checking that now."), user("go ahead")]

    reply = plan(history, system_prompt())

    assert all(call.name != "file_event_draft_proposal" for call in reply.tool_calls)


def test_the_title_is_not_invented_when_the_request_names_none() -> None:
    request = (
        "Book the Synthetic Main Auditorium for the Synthetic Events Club on 2026-12-05 9 to 10."
    )

    [call] = plan([user(request)], system_prompt()).tool_calls

    assert call.name == "check_event_conflicts"


# ---- edges the first cut missed ----------------------------------------------------------


def test_a_yes_inside_a_fresh_request_is_checked_not_filed() -> None:
    reply = plan([user("Yes please. " + FULL)], system_prompt())

    assert [call.name for call in reply.tool_calls] == ["check_event_conflicts"]


def test_the_venue_mentioned_last_is_the_one_used() -> None:
    history = [
        user(FULL.replace("Synthetic Main Auditorium", "Seminar Hall")),
        assistant("Which venue should it be in?"),
        user("Actually the auditorium, please."),
    ]

    assert check_args(plan(history, system_prompt()))["resource_id"] == str(AUDITORIUM)


def test_midnight_is_midnight_and_noon_is_noon() -> None:
    request = FULL.replace("3pm to 5pm", "12am to 2am")
    midnight = check_args(plan([user(request)], system_prompt()))
    noon = check_args(plan([user(FULL.replace("3pm to 5pm", "12pm to 2pm"))], system_prompt()))

    assert midnight["start_at"] == "2026-11-24T00:00:00+05:30"
    assert noon["start_at"] == "2026-11-24T12:00:00+05:30"


def test_an_end_before_the_start_is_asked_about_not_accepted() -> None:
    reply = plan([user(FULL.replace("3pm to 5pm", "5pm to 3pm"))], system_prompt())

    assert reply.tool_calls == []
    assert reply.text is not None
    assert "start and end time" in reply.text


def test_a_time_written_before_an_iso_date_is_not_confused_with_it() -> None:
    request = (
        "Plan a talk for the Synthetic Events Club in the Seminar Hall from 3pm to 5pm "
        "on 2026-12-05."
    )

    args = check_args(plan([user(request)], system_prompt()))

    assert (args["start_at"], args["end_at"]) == (
        "2026-12-05T15:00:00+05:30",
        "2026-12-05T17:00:00+05:30",
    )
