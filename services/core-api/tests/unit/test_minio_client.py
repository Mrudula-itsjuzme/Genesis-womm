from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from botocore.exceptions import ClientError

from app.services.minio_client import MinIOProposalStorage


@pytest.fixture
def mock_s3_client() -> MagicMock:
    client = MagicMock()
    client.generate_presigned_url.return_value = (
        "https://minio.local/campuscue-proposals-dev/proposals/test.pdf?sig=123"
    )
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


# ---- a fresh object store has no buckets -------------------------------------------------


def missing_bucket() -> ClientError:
    return ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadBucket")


def upload(storage: MinIOProposalStorage) -> None:
    storage.upload_proposal(
        club_id=uuid4(),
        event_id=uuid4(),
        proposal_id=uuid4(),
        revision=1,
        file_bytes=b"%PDF-1.4 sample",
    )


def test_a_missing_bucket_is_created_before_the_first_upload(
    storage: MinIOProposalStorage, mock_s3_client: MagicMock
) -> None:
    mock_s3_client.head_bucket.side_effect = missing_bucket()

    upload(storage)

    mock_s3_client.create_bucket.assert_called_once_with(Bucket="campuscue-proposals-dev")
    names = [call[0] for call in mock_s3_client.method_calls]
    assert names.index("create_bucket") < names.index("put_object")


def test_an_existing_bucket_is_left_alone(
    storage: MinIOProposalStorage, mock_s3_client: MagicMock
) -> None:
    upload(storage)

    mock_s3_client.create_bucket.assert_not_called()


def test_a_bucket_is_checked_once_not_on_every_upload(
    storage: MinIOProposalStorage, mock_s3_client: MagicMock
) -> None:
    upload(storage)
    upload(storage)

    mock_s3_client.head_bucket.assert_called_once()


def test_a_bucket_another_request_just_created_is_not_an_error(
    storage: MinIOProposalStorage, mock_s3_client: MagicMock
) -> None:
    mock_s3_client.head_bucket.side_effect = missing_bucket()
    mock_s3_client.create_bucket.side_effect = ClientError(
        {"Error": {"Code": "BucketAlreadyOwnedByYou"}}, "CreateBucket"
    )

    upload(storage)

    mock_s3_client.put_object.assert_called_once()


def test_a_refused_bucket_check_is_not_papered_over_with_a_create(
    storage: MinIOProposalStorage, mock_s3_client: MagicMock
) -> None:
    mock_s3_client.head_bucket.side_effect = ClientError(
        {"Error": {"Code": "403", "Message": "Forbidden"}}, "HeadBucket"
    )

    with pytest.raises(ClientError):
        upload(storage)

    mock_s3_client.create_bucket.assert_not_called()
    mock_s3_client.put_object.assert_not_called()


def test_the_archive_bucket_is_ensured_before_a_file_is_moved_into_it(
    storage: MinIOProposalStorage, mock_s3_client: MagicMock
) -> None:
    mock_s3_client.head_bucket.side_effect = missing_bucket()

    storage.archive_proposal("campuscue-proposals-dev", "proposals/a/b/c/v1.pdf")

    mock_s3_client.create_bucket.assert_called_once_with(Bucket="campuscue-proposals-archive-dev")


# ---- links the browser can follow --------------------------------------------------------


def test_download_links_are_signed_for_the_address_a_browser_can_reach() -> None:
    internal, browser_facing = MagicMock(), MagicMock()
    browser_facing.generate_presigned_url.return_value = "http://localhost:9000/b/k?sig=1"
    storage = MinIOProposalStorage(
        endpoint="minio:9000",
        access_key="a",
        secret_key="s",
        client=internal,
        presign_client=browser_facing,
    )

    link = storage.generate_presigned_download_url("bucket", "key", expires_in_seconds=60)

    assert link == "http://localhost:9000/b/k?sig=1"
    browser_facing.generate_presigned_url.assert_called_once()
    internal.generate_presigned_url.assert_not_called()


def test_without_a_public_address_links_use_the_internal_client(
    storage: MinIOProposalStorage, mock_s3_client: MagicMock
) -> None:
    storage.generate_presigned_download_url("bucket", "key")

    mock_s3_client.generate_presigned_url.assert_called_once()


def test_a_real_signed_link_points_at_the_public_address_not_the_internal_one() -> None:
    storage = MinIOProposalStorage(
        endpoint="minio:9000",
        public_endpoint="localhost:9000",
        access_key="a" * 8,
        secret_key="s" * 16,
    )

    link = storage.generate_presigned_download_url("bucket", "proposals/x.pdf", 60)

    assert link.startswith("http://localhost:9000/bucket/proposals/x.pdf?")
    assert "X-Amz-Signature=" in link
    assert "minio:9000" not in link
