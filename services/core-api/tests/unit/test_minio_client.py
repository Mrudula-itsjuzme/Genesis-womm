from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.services.minio_client import MinIOProposalStorage


@pytest.fixture
def mock_s3_client() -> MagicMock:
    client = MagicMock()
    client.generate_presigned_url.return_value = "https://minio.local/campuscue-proposals-dev/proposals/test.pdf?sig=123"
    return client


@pytest.fixture
def storage(mock_s3_client: MagicMock) -> MinIOProposalStorage:
    return MinIOProposalStorage(
        endpoint="localhost:9000",
        access_key="test_access",
        secret_key="test_secret",
        proposal_bucket="campuscue-proposals-dev",
        archive_bucket="campuscue-proposals-archive-dev",
        client=mock_s3_client,
    )


def test_build_object_key(storage: MinIOProposalStorage) -> None:
    club_id = uuid4()
    event_id = uuid4()
    proposal_id = uuid4()

    key = storage.build_object_key(club_id, event_id, proposal_id, 1)
    assert key == f"proposals/{club_id}/{event_id}/{proposal_id}/v1.pdf"

    archive_key = storage.build_archive_key(club_id, event_id, proposal_id, 1)
    assert archive_key == f"proposals-archive/{club_id}/{event_id}/{proposal_id}/v1.pdf"


def test_upload_proposal_success(storage: MinIOProposalStorage, mock_s3_client: MagicMock) -> None:
    club_id = uuid4()
    event_id = uuid4()
    proposal_id = uuid4()
    pdf_bytes = b"%PDF-1.4 sample proposal content"

    bucket, key, size, sha = storage.upload_proposal(
        club_id=club_id,
        event_id=event_id,
        proposal_id=proposal_id,
        revision=2,
        file_bytes=pdf_bytes,
        metadata={"custom": "val"},
    )

    assert bucket == "campuscue-proposals-dev"
    assert key == f"proposals/{club_id}/{event_id}/{proposal_id}/v2.pdf"
    assert size == len(pdf_bytes)
    assert len(sha) == 64

    mock_s3_client.put_object.assert_called_once()
    kwargs = mock_s3_client.put_object.call_args.kwargs
    assert kwargs["Bucket"] == "campuscue-proposals-dev"
    assert kwargs["Key"] == key
    assert kwargs["Body"] == pdf_bytes
    assert kwargs["Metadata"]["revision"] == "2"
    assert kwargs["Metadata"]["custom"] == "val"


def test_upload_proposal_rejects_non_pdf(storage: MinIOProposalStorage) -> None:
    club_id = uuid4()
    event_id = uuid4()
    proposal_id = uuid4()

    with pytest.raises(ValueError, match="must be a PDF starting with %PDF-"):
        storage.upload_proposal(

            club_id=club_id,
            event_id=event_id,
            proposal_id=proposal_id,
            revision=1,
            file_bytes=b"<html>not a pdf</html>",
        )


def test_generate_presigned_download_url(
    storage: MinIOProposalStorage, mock_s3_client: MagicMock
) -> None:
    url = storage.generate_presigned_download_url(
        bucket="campuscue-proposals-dev",
        object_key="proposals/test/v1.pdf",
        expires_in_seconds=600,
    )
    assert "sig=123" in url
    mock_s3_client.generate_presigned_url.assert_called_once_with(
        "get_object",
        Params={"Bucket": "campuscue-proposals-dev", "Key": "proposals/test/v1.pdf"},
        ExpiresIn=600,
    )


def test_archive_proposal(storage: MinIOProposalStorage, mock_s3_client: MagicMock) -> None:
    source_bucket = "campuscue-proposals-dev"
    source_key = "proposals/c1/e1/p1/v1.pdf"

    dest_key = storage.archive_proposal(source_bucket, source_key)

    assert dest_key == "proposals-archive/c1/e1/p1/v1.pdf"
    mock_s3_client.copy_object.assert_called_once_with(
        CopySource={"Bucket": source_bucket, "Key": source_key},
        Bucket="campuscue-proposals-archive-dev",
        Key=dest_key,
    )
    mock_s3_client.delete_object.assert_called_once_with(
        Bucket=source_bucket,
        Key=source_key,
    )
