"""DigitalOcean Spaces storage service.

S3-compatible object storage for datasets, charts, and exports.
"""

import logging
from typing import BinaryIO

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from bo1.config import get_settings

logger = logging.getLogger(__name__)


class SpacesError(Exception):
    """Error during Spaces operation."""

    def __init__(self, message: str, operation: str, key: str | None = None):
        self.operation = operation
        self.key = key
        super().__init__(f"Spaces {operation} failed: {message}")


class SpacesClient:
    """S3-compatible client for DigitalOcean Spaces.

    Provides upload, download, delete, and presigned URL operations
    with retry logic and error handling.
    """

    def __init__(
        self,
        access_key: str | None = None,
        secret_key: str | None = None,
        region: str | None = None,
        bucket: str | None = None,
        endpoint_url: str | None = None,
    ):
        """Initialize Spaces client.

        Args:
            access_key: DO Spaces access key (defaults to settings)
            secret_key: DO Spaces secret key (defaults to settings)
            region: DO Spaces region (defaults to settings)
            bucket: Bucket name (defaults to settings)
            endpoint_url: Endpoint URL (defaults to settings)
        """
        settings = get_settings()

        self._access_key = access_key or settings.do_spaces_key
        self._secret_key = secret_key or settings.do_spaces_secret
        self._region = region or settings.do_spaces_region
        self._bucket = bucket or settings.do_spaces_bucket
        self._endpoint_url = endpoint_url or settings.do_spaces_endpoint_url

        # Configure retry logic
        config = Config(
            retries={
                "max_attempts": 3,
                "mode": "standard",
            },
            connect_timeout=10,
            read_timeout=30,
        )

        self._client = boto3.client(
            "s3",
            region_name=self._region,
            endpoint_url=self._endpoint_url,
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
            config=config,
        )

    @property
    def bucket(self) -> str:
        """Get bucket name."""
        return self._bucket

    def upload_file(
        self,
        key: str,
        data: bytes | BinaryIO,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> str:
        """Upload a file to Spaces.

        Args:
            key: Object key (path in bucket)
            data: File data as bytes or file-like object
            content_type: MIME content type
            metadata: Optional metadata dict

        Returns:
            Full URL to uploaded object

        Raises:
            SpacesError: If upload fails
        """
        try:
            extra_args = {"ContentType": content_type, "ACL": "private"}
            if metadata:
                extra_args["Metadata"] = metadata

            if isinstance(data, bytes):
                self._client.put_object(
                    Bucket=self._bucket,
                    Key=key,
                    Body=data,
                    **extra_args,
                )
            else:
                self._client.upload_fileobj(
                    data,
                    self._bucket,
                    key,
                    ExtraArgs=extra_args,
                )

            logger.info(f"Uploaded {key} to Spaces bucket {self._bucket}")
            return f"{self._endpoint_url}/{self._bucket}/{key}"

        except (BotoCoreError, ClientError) as e:
            logger.error(f"Failed to upload {key}: {e}")
            raise SpacesError(str(e), "upload", key) from e

    def download_file(self, key: str) -> bytes:
        """Download a file from Spaces.

        Args:
            key: Object key (path in bucket)

        Returns:
            File contents as bytes

        Raises:
            SpacesError: If download fails
        """
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
            data = response["Body"].read()
            logger.debug(f"Downloaded {key} from Spaces ({len(data)} bytes)")
            return data

        except (BotoCoreError, ClientError) as e:
            logger.error(f"Failed to download {key}: {e}")
            raise SpacesError(str(e), "download", key) from e

    def delete_file(self, key: str) -> bool:
        """Delete a file from Spaces.

        Args:
            key: Object key (path in bucket)

        Returns:
            True if deleted (or didn't exist)

        Raises:
            SpacesError: If delete fails
        """
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
            logger.info(f"Deleted {key} from Spaces bucket {self._bucket}")
            return True

        except (BotoCoreError, ClientError) as e:
            logger.error(f"Failed to delete {key}: {e}")
            raise SpacesError(str(e), "delete", key) from e

    def generate_presigned_url(
        self,
        key: str,
        expires_in: int = 3600,
        http_method: str = "GET",
    ) -> str:
        """Generate a presigned URL for temporary access.

        Args:
            key: Object key (path in bucket)
            expires_in: URL validity in seconds (default: 1 hour)
            http_method: HTTP method (GET for download, PUT for upload)

        Returns:
            Presigned URL string

        Raises:
            SpacesError: If URL generation fails
        """
        try:
            client_method = "get_object" if http_method == "GET" else "put_object"
            url = self._client.generate_presigned_url(
                ClientMethod=client_method,
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires_in,
            )
            logger.debug(f"Generated presigned URL for {key} (expires in {expires_in}s)")
            return url

        except (BotoCoreError, ClientError) as e:
            logger.error(f"Failed to generate presigned URL for {key}: {e}")
            raise SpacesError(str(e), "presign", key) from e

    def file_exists(self, key: str) -> bool:
        """Check if a file exists in Spaces.

        Args:
            key: Object key (path in bucket)

        Returns:
            True if file exists
        """
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise SpacesError(str(e), "head", key) from e


# Singleton instance (lazy-loaded)
_spaces_client: SpacesClient | None = None


def get_spaces_client() -> SpacesClient:
    """Get or create Spaces client singleton.

    Returns:
        SpacesClient instance
    """
    global _spaces_client
    if _spaces_client is None:
        _spaces_client = SpacesClient()
    return _spaces_client


def reset_spaces_client() -> None:
    """Reset Spaces client singleton (for testing)."""
    global _spaces_client
    _spaces_client = None
