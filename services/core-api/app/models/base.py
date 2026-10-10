"""SQLAlchemy declarative bases, one per Core-owned schema (spine AD-20).

``student_private`` tables get their own base and are importable only from the allowlisted
student-risk modules (spine AD-13); that base is added with the student-risk plan.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

CORE_SCHEMA = "core"
STUDENT_PRIVATE_SCHEMA = "student_private"
VERSION_TABLE = "alembic_version_core"

# Deterministic constraint names keep Alembic diffs and rollbacks predictable.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(schema=CORE_SCHEMA, naming_convention=NAMING_CONVENTION)
