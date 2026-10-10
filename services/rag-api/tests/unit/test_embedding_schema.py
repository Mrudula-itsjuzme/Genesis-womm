from pathlib import Path


def test_initial_schema_uses_the_local_embedding_dimension() -> None:
    migration = Path("alembic/versions/b4d6b94ac156_initial_schema_for_documentchunk.py")

    assert "VECTOR(dim=768)" in migration.read_text()
