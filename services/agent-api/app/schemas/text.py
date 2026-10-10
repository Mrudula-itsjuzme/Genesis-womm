from typing import Annotated

from pydantic import StringConstraints

MessageText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
]
Summary = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
