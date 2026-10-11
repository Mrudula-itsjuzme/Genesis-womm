"""MinIO S3 object storage client for managing event proposals and presigned URLs."""

from hashlib import sha256
from typing import Any
from uuid import UUID


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
    ) -> None:
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.proposal_bucket = proposal_bucket
        self.archive_bucket = archive_bucket
        self.use_ssl = use_ssl
        self._client = client
        self.public_endpoint = public_endpoint
        self._download_client: Any = None

    def _s3_client(self, endpoint: str) -> Any:
        import boto3
        from botocore.client import Config

        protocol = "https" if self.use_ssl else "http"
        endpoint_url = endpoint if endpoint.startswith("http") else f"{protocol}://{endpoint}"
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
            self._client = self._s3_client(self.endpoint)
        return self._client

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
        signer = self.client
        if self.public_endpoint:
            if self._download_client is None:
                self._download_client = self._s3_client(self.public_endpoint)
            signer = self._download_client
        url: str = signer.generate_presigned_url(
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

        copy_source = {"Bucket": source_bucket, "Key": source_key}
        self.client.copy_object(
            CopySource=copy_source,
            Bucket=destination_bucket,
            Key=destination_key,
        )
        self.client.delete_object(Bucket=source_bucket, Key=source_key)
        return destination_key
