"""A deterministic planner that follows the real prompt's workflow with no model (spine AD-11).

It exists so a demo survives a rate limit or no internet. It reads the same campus context the
model reads, asks for what is missing, explains conflicts instead of filing over them, and files
a proposal only after a clean check or an explicit go-ahead. It understands plain date and time
phrases ("24 November 2026 from 3pm to 5pm"), not relative ones.
"""

import calendar
import re
from dataclasses import dataclass
from datetime import date

from app.ports.llm import LlmResponse, ToolCall
from app.schemas.chat import ChatMessage

_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_CLUB_LINE = re.compile(rf"^- ({_UUID}) \| ([^|]+) \| ([^|]+)$", re.M)
_VENUE_LINE = re.compile(rf"^- ({_UUID}) \| ([^|]+) \| [^|]+ \| [^|]+$", re.M)
_TOOL_RESULT = re.compile(r"^\[Tool (\w+)\]: ?(.*)$", re.S)
_CONFLICT_LINE = re.compile(r"^\s*- \[(\w+)\] ", re.M)

_PLAN_WORDS = re.compile(
    r"\b(plan|host|organi[sz]e|schedule|arrange|book|hold|set up|propose|workshop|hackathon|"
    r"talk|meetup|event|seminar|demo)\b",
    re.I,
)
_GO_AHEAD = re.compile(r"\b(go ahead|proceed|anyway|file it|propose it|do it|yes)\b", re.I)
_TITLE = re.compile(
    r"\b(?:plan|host|organi[sz]e|schedule|arrange|set up|hold)\s+(?:a|an|the|our|new)?\s*"
    r"(.+?)\s+(?:for|in|on|at|from|during)\b",
    re.I,
)

_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_DAY_FIRST = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?([A-Za-z]{3,9})\.?,?\s+(\d{4})\b")
_MONTH_FIRST = re.compile(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b")
_TIME_RANGE = re.compile(
    r"(?<![\d:])(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*(?:to|-|until|till)\s*"
    r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b",
    re.I,
)

_MONTHS = {
    word.lower(): number
    for number in range(1, 13)
    for word in (calendar.month_name[number], calendar.month_abbr[number])
}
_FILLER = {"synthetic", "club", "the"}
_IST = "+05:30"
_EXAMPLE = "24 November 2026 from 3pm to 5pm"


@dataclass(frozen=True)
class _Named:
    id: str
    name: str

    @property
    def key(self) -> str:
        """The word that identifies it in a sentence: its longest, once filler is dropped."""
        words: list[str] = [w for w in re.findall(r"[a-z]+", self.name.lower()) if w not in _FILLER]
        return max(words or [self.name.lower()], key=len)


@dataclass(frozen=True)
class _Campus:
    clubs: tuple[_Named, ...]
    venues: tuple[_Named, ...]

    @classmethod
    def read(cls, system_prompt: str) -> "_Campus":
        return cls(
            clubs=tuple(_Named(i, n.strip()) for i, n, _ in _CLUB_LINE.findall(system_prompt)),
            venues=tuple(_Named(i, n.strip()) for i, n, *_ in _VENUE_LINE.findall(system_prompt)),
        )


def _last_mention(options: tuple[_Named, ...], text: str) -> _Named | None:
    lowered = text.lower()
    found = [(lowered.rfind(o.key), o) for o in options if o.key in lowered]
    return max(found, key=lambda pair: pair[0])[1] if found else None


def _read_date(text: str) -> tuple[date, tuple[int, int]] | None:
    """The last date in the text and where it sits, so the time search can skip it."""
    found: list[tuple[int, date, tuple[int, int]]] = []
    for pattern, order in ((_ISO, "ymd"), (_DAY_FIRST, "dmy"), (_MONTH_FIRST, "mdy")):
        for match in pattern.finditer(text):
            a, b, c = match.groups()
            try:
                if order == "ymd":
                    when = date(int(a), int(b), int(c))
                elif order == "dmy":
                    when = date(int(c), _MONTHS[b.lower()], int(a))
                else:
                    when = date(int(c), _MONTHS[a.lower()], int(b))
            except (KeyError, ValueError):
                continue
            found.append((match.start(), when, match.span()))
    if not found:
        return None
    _, when, span = max(found, key=lambda item: item[0])
    return when, span


def _minutes(hour: int, minute: int, meridiem: str | None) -> int:
    if meridiem == "pm" and hour < 12:
        hour += 12
    if meridiem == "am" and hour == 12:
        hour = 0
    return hour * 60 + minute


_EN_DASH = chr(0x2013)


def _read_times(text: str) -> tuple[int, int] | None:
    matches = list(_TIME_RANGE.finditer(text.replace(_EN_DASH, "-")))
    if not matches:
        return None
    h1, m1, p1, h2, m2, p2 = matches[-1].groups()
    end = _minutes(int(h2), int(m2 or 0), p2 and p2.lower())
    first = p1 and p1.lower()
    if first is None and p2:
        # "3 to 5pm" is an afternoon; "10 to 12pm" cannot be, so the start falls back to morning.
        start = _minutes(int(h1), int(m1 or 0), p2.lower())
        if start >= end:
            start = _minutes(int(h1), int(m1 or 0), "am")
    else:
        start = _minutes(int(h1), int(m1 or 0), first)
    return (start, end) if start < end else None


def _iso(when: date, minutes: int) -> str:
    return f"{when.isoformat()}T{minutes // 60:02d}:{minutes % 60:02d}:00{_IST}"


@dataclass(frozen=True)
class _Slot:
    """A request with everything needed to check and file it."""

    club: _Named
    venue: _Named
    start_at: str
    end_at: str
    title: str

    def check_arguments(self) -> dict[str, str]:
        return {
            "club_id": self.club.id,
            "resource_id": self.venue.id,
            "start_at": self.start_at,
            "end_at": self.end_at,
        }

    def proposal_arguments(self) -> dict[str, object]:
        payload = {**self.check_arguments(), "title": self.title}
        return {"summary": f"Propose {self.title}", "payload": payload}


@dataclass(frozen=True)
class _Request:
    club: _Named | None
    venue: _Named | None
    start_at: str | None
    end_at: str | None
    title: str

    @classmethod
    def read(cls, text: str, campus: _Campus) -> "_Request":
        club = _last_mention(campus.clubs, text)
        if club is None and len(campus.clubs) == 1:
            club = campus.clubs[0]
        dated = _read_date(text)
        times_text = text
        if dated is not None:
            first, last = dated[1]
            times_text = f"{text[:first]} {text[last:]}"
        times = _read_times(times_text)
        start_at = end_at = None
        if dated is not None and times is not None:
            start_at, end_at = _iso(dated[0], times[0]), _iso(dated[0], times[1])
        titled = _TITLE.search(text)
        return cls(
            club=club,
            venue=_last_mention(campus.venues, text),
            start_at=start_at,
            end_at=end_at,
            title=titled.group(1).strip() if titled else "Club event",
        )

    def slot(self) -> _Slot | None:
        if self.club and self.venue and self.start_at and self.end_at:
            return _Slot(self.club, self.venue, self.start_at, self.end_at, self.title)
        return None

    def question(self, campus: _Campus) -> str:
        """The one thing to ask next. Only meaningful while the request is incomplete."""
        if self.club is None:
            if not campus.clubs:
                return "You are not a member of any club, so I cannot prepare a proposal."
            names = " or ".join(c.name for c in campus.clubs)
            return f"Which club is this for: {names}?"
        if self.start_at is None:
            return f"What date and what start and end time? For example {_EXAMPLE}."
        names = ", ".join(v.name for v in campus.venues)
        return f"Which venue should it be in: {names}?"


def _check(slot: _Slot) -> LlmResponse:
    call = ToolCall(id="demo-check", name="check_event_conflicts", arguments=slot.check_arguments())
    return LlmResponse(text=None, tool_calls=[call])


def _file(slot: _Slot) -> LlmResponse:
    call = ToolCall(
        id="demo-file", name="file_event_draft_proposal", arguments=slot.proposal_arguments()
    )
    return LlmResponse(text=None, tool_calls=[call])


def _said(text: str) -> LlmResponse:
    return LlmResponse(text=text, tool_calls=[])


def _spoken(messages: list[ChatMessage]) -> str:
    """Everything the person has said in this conversation, oldest first."""
    return "\n".join(
        m.content for m in messages if m.role == "user" and not m.content.startswith("[Tool ")
    )


def _after_tool(
    name: str, result: str, messages: list[ChatMessage], campus: _Campus
) -> LlmResponse:
    if name == "file_event_draft_proposal":
        if result.startswith("Error:"):
            return _said(f"I could not file the proposal. {result}")
        return _said(
            "I filed the proposal. Its status is PROPOSED, and you must confirm it yourself "
            "before anything is scheduled."
        )
    if result.startswith("Error:"):
        return _said(f"I could not complete the conflict check, so nothing was proposed. {result}")
    slot = _Request.read(_spoken(messages), campus).slot()
    if slot is None:
        return _said("I lost track of the request. Please describe the event again.")
    severities = _CONFLICT_LINE.findall(result)
    if "No conflicts detected" in result or all(s == "INFO" for s in severities):
        return _file(slot)
    lines = "\n".join(line for line in result.splitlines()[1:] if line.strip().startswith("- ["))
    return _said(
        "Core found conflicts for that slot:\n"
        f"{lines}\n"
        "I have not proposed anything. Should I propose it anyway, or try another time or venue?"
    )


def plan(messages: list[ChatMessage], system_prompt: str) -> LlmResponse:
    campus = _Campus.read(system_prompt)
    last = messages[-1].content
    tool = _TOOL_RESULT.match(last)
    if tool is not None:
        return _after_tool(tool.group(1), tool.group(2), messages, campus)

    spoken = _spoken(messages)
    earlier = [m for m in messages[:-1] if m.role == "assistant"]
    after_conflicts = bool(earlier) and "conflict" in earlier[-1].content.lower()
    after_question = bool(earlier) and earlier[-1].content.rstrip().endswith("?")
    if not (_PLAN_WORDS.search(last) or after_question or after_conflicts):
        return _said(
            "I am running in offline demo mode and can only plan events. Try: Plan a workshop "
            f"for <club> in <venue> on {_EXAMPLE}."
        )
    request = _Request.read(spoken, campus)
    slot = request.slot()
    nothing_planned = not _PLAN_WORDS.search(last) and not _PLAN_WORDS.search(
        _spoken(messages[:-1])
    )
    if _GO_AHEAD.search(last) and nothing_planned:
        return _said("There is nothing to go ahead with yet. What would you like to plan?")
    if slot is None:
        return _said(request.question(campus))
    return _file(slot) if _GO_AHEAD.search(last) and after_conflicts else _check(slot)
