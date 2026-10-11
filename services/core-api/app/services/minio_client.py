"""MinIO S3 object storage client for managing event proposals and presigned URLs."""

from hashlib import sha256
from typing import Any
from uuid import UUID

from botocore.exceptions import ClientError

# What an S3-compatible store answers when a bucket does not exist yet.
_NO_SUCH_BUCKET = {"404", "NoSuchBucket", "NotFound"}


class MinIOProposalStorage:
    """Encapsulates MinIO operations for uploading, presigning, and archiving proposal PDFs."""

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        proposal_bucket: str = "campuscue-proposals-dev",
        archive_bucket: str = "campuscue-proposals-archive-dev",
        use_ssl: bool = False,
        client: Any = None,
        public_endpoint: str | None = None,
        presign_client: Any = None,
    ) -> None:
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.proposal_bucket = proposal_bucket
        self.archive_bucket = archive_bucket
        self.use_ssl = use_ssl
        self._client = client
        # Links are signed for the address a browser can reach, which inside Docker is not the
        # address Core uses. Signing is local, so this client never connects anywhere.
        self.public_endpoint = public_endpoint
        self._presign_client = presign_client
        self._known_buckets: set[str] = set()

    def _make_client(self, endpoint: str) -> Any:
        # Lazy import and initialization of boto3
        import boto3
        from botocore.client import Config

        endpoint_url = endpoint
        if not endpoint.startswith("http"):
            endpoint_url = f"{'https' if self.use_ssl else 'http'}://{endpoint}"
        return boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = self._make_client(self.endpoint)
        return self._client

    @property
    def presign_client(self) -> Any:
        if self._presign_client is None:
            self._presign_client = (
                self._make_client(self.public_endpoint) if self.public_endpoint else self.client
            )
        return self._presign_client

    def _ensure_bucket(self, name: str) -> None:
        """A fresh object store has no buckets: create the one about to be used, once."""
        if name in self._known_buckets:
            return
        try:
            self.client.head_bucket(Bucket=name)
        except ClientError as error:
            if str(error.response.get("Error", {}).get("Code", "")) not in _NO_SUCH_BUCKET:
                raise
            try:
                self.client.create_bucket(Bucket=name)
            except ClientError as created:
                # Another request created it between the check and now.
                if str(created.response.get("Error", {}).get("Code", "")) not in {
                    "BucketAlreadyOwnedByYou",
                    "BucketAlreadyExists",
                }:
                    raise
        self._known_buckets.add(name)

    def build_object_key(
        self, club_id: UUID, event_id: UUID, proposal_id: UUID, revision: int
    ) -> str:
        """Standardized key format: proposals/{club_id}/{event_id}/{proposal_id}/v{revision}.pdf"""
        return f"proposals/{club_id}/{event_id}/{proposal_id}/v{revision}.pdf"

    def build_archive_key(
        self, club_id: UUID, event_id: UUID, proposal_id: UUID, revision: int
    ) -> str:
        """Standardized archive key format:
        proposals-archive/{club_id}/{event_id}/{proposal_id}/v{revision}.pdf
        """
        return f"proposals-archive/{club_id}/{event_id}/{proposal_id}/v{revision}.pdf"

    def upload_proposal(
        self,
        club_id: UUID,
        event_id: UUID,
        proposal_id: UUID,
        revision: int,
        file_bytes: bytes,
        content_type: str = "application/pdf",
        metadata: dict[str, str] | None = None,
    ) -> tuple[str, str, int, str]:
        """Uploads proposal bytes to MinIO and returns (bucket, key, size_bytes, sha256_hash)."""
        if not file_bytes:
            raise ValueError("Cannot upload empty file bytes")

        # Validate PDF magic bytes (%PDF-)
        if not file_bytes.startswith(b"%PDF-"):
            raise ValueError("Invalid format: Proposal file must be a PDF starting with %PDF-")

        key = self.build_object_key(club_id, event_id, proposal_id, revision)
        file_size = len(file_bytes)
        file_hash = sha256(file_bytes).hexdigest()

        meta = metadata or {}
        meta.update(
            {
                "club_id": str(club_id),
                "event_id": str(event_id),
                "proposal_id": str(proposal_id),
                "revision": str(revision),
            }
        )

        self._ensure_bucket(self.proposal_bucket)
        self.client.put_object(
            Bucket=self.proposal_bucket,
            Key=key,
            Body=file_bytes,
            ContentType=content_type,
            Metadata=meta,
        )

        return self.proposal_bucket, key, file_size, file_hash

    def generate_presigned_download_url(
        self,
        bucket: str,
        object_key: str,
        expires_in_seconds: int = 900,
    ) -> str:
        """Generates a short-lived presigned GET URL (default 15 minutes TTL)."""
        url: str = self.presign_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": object_key},
            ExpiresIn=expires_in_seconds,
        )
        return url

    def archive_proposal(
        self,
        source_bucket: str,
        source_key: str,
        dest_bucket: str | None = None,
        dest_key: str | None = None,
    ) -> str:
        """Copies object to archive bucket/key, then removes source object (archive-move)."""
        destination_bucket = dest_bucket or self.archive_bucket
        destination_key = dest_key or source_key.replace("proposals/", "proposals-archive/")

        self._ensure_bucket(destination_bucket)
        copy_source = {"Bucket": source_bucket, "Key": source_key}
        self.client.copy_object(
            CopySource=copy_source,
            Bucket=destination_bucket,
            Key=destination_key,
        )
        self.client.delete_object(Bucket=source_bucket, Key=source_key)
        return destination_key
