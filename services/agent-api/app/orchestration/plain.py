"""Plain text for the chat window (spine AD-9).

The web chat does not render Markdown, so a model that writes it anyway shows the audience raw
asterisks. Only presentation marks are removed. Words, numbers and line structure are untouched,
and a marker that is not clearly paired is left alone rather than guessed at.
"""

import re

_BOLD = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*")
_BOLD_UNDERSCORE = re.compile(r"(?<!\w)__(?=\S)(.+?)(?<=\S)__(?!\w)")
_CODE = re.compile(r"`([^`\n]+)`")
_HEADING = re.compile(r"^(\s*)#{1,6}\s+", re.M)
_STAR_BULLET = re.compile(r"^(\s*)\*\s+", re.M)


def plain_text(text: str) -> str:
    text = _BOLD.sub(r"\1", text)
    text = _BOLD_UNDERSCORE.sub(r"\1", text)
    text = _CODE.sub(r"\1", text)
    text = _HEADING.sub(r"\1", text)
    return _STAR_BULLET.sub(r"\1- ", text)
