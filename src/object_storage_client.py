from __future__ import annotations

import hashlib
import os
from typing import Any


class ObjectStorageClient:
    """S3-compatible object storage adapter (tested with MinIO)."""

    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        region: str = "us-east-1",
        secure: bool = False,
    ):
        if not endpoint_url:
            raise ValueError("endpoint_url is required")
        if not bucket:
            raise ValueError("bucket is required")

        import boto3
        from botocore.config import Config

        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            use_ssl=secure,
            config=Config(s3={"addressing_style": "path"}, retries={"max_attempts": 3}),
        )

    @classmethod
    def from_env(cls) -> "ObjectStorageClient":
        return cls(
            endpoint_url=os.getenv("S3_ENDPOINT_URL", "http://127.0.0.1:9000"),
            access_key=os.getenv("S3_ACCESS_KEY", "minioadmin"),
            secret_key=os.getenv("S3_SECRET_KEY", "minioadmin"),
            bucket=os.getenv("S3_BUCKET", "storage-test-bucket"),
            secure=os.getenv("S3_SECURE", "false").lower() == "true",
        )

    def ensure_bucket(self) -> None:
        from botocore.exceptions import ClientError

        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError as exc:
            status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            code = exc.response.get("Error", {}).get("Code")
            if status == 404 or code in {"404", "NoSuchBucket", "NotFound"}:
                self.client.create_bucket(Bucket=self.bucket)
            else:
                raise

    def put_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        if not key:
            raise ValueError("object key must not be empty")
        checksum = hashlib.sha256(data).hexdigest()
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            Metadata={"sha256": checksum},
        )
        return checksum

    def get_bytes(self, key: str) -> bytes:
        response: dict[str, Any] = self.client.get_object(Bucket=self.bucket, Key=key)
        try:
            return response["Body"].read()
        finally:
            response["Body"].close()

    def head(self, key: str) -> dict[str, Any]:
        return self.client.head_object(Bucket=self.bucket, Key=key)

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)
