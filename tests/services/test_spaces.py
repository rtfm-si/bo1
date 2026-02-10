"""Tests for DigitalOcean Spaces storage service."""

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from backend.services.spaces import (
    SpacesClient,
    SpacesConfigurationError,
    SpacesError,
    get_spaces_client,
    reset_spaces_client,
)


@pytest.fixture
def mock_boto3_client():
    """Mock boto3 S3 client."""
    with patch("backend.services.spaces.boto3.client") as mock:
        yield mock


@pytest.fixture
def spaces_client(mock_boto3_client):
    """Create SpacesClient with mocked boto3."""
    reset_spaces_client()
    client = SpacesClient(
        access_key="test_key",
        secret_key="test_secret",  # noqa: S106
        region="nyc3",
        bucket="test-bucket",
        endpoint_url="https://nyc3.digitaloceanspaces.com",
    )
    return client


class TestSpacesClientUpload:
    """Tests for upload operations."""

    def test_upload_bytes_success(self, spaces_client, mock_boto3_client):
        """Test uploading bytes data."""
        mock_client = mock_boto3_client.return_value

        result = spaces_client.upload_file(
            key="datasets/test.csv",
            data=b"col1,col2\nval1,val2",
            content_type="text/csv",
        )

        mock_client.put_object.assert_called_once()
        call_kwargs = mock_client.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["Key"] == "datasets/test.csv"
        assert call_kwargs["ContentType"] == "text/csv"
        assert "test-bucket/datasets/test.csv" in result

    def test_upload_with_metadata(self, spaces_client, mock_boto3_client):
        """Test uploading with custom metadata."""
        mock_client = mock_boto3_client.return_value

        spaces_client.upload_file(
            key="datasets/test.csv",
            data=b"data",
            content_type="text/csv",
            metadata={"user_id": "123", "original_name": "sales.csv"},
        )

        call_kwargs = mock_client.put_object.call_args[1]
        assert call_kwargs["Metadata"] == {"user_id": "123", "original_name": "sales.csv"}

    def test_upload_failure_raises_error(self, spaces_client, mock_boto3_client):
        """Test upload failure raises SpacesError."""
        mock_client = mock_boto3_client.return_value
        mock_client.put_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            "PutObject",
        )

        with pytest.raises(SpacesError) as exc:
            spaces_client.upload_file(key="test.csv", data=b"data")

        assert "upload" in str(exc.value)
        assert exc.value.operation == "upload"
        assert exc.value.key == "test.csv"


class TestSpacesClientDownload:
    """Tests for download operations."""

    def test_download_success(self, spaces_client, mock_boto3_client):
        """Test downloading file."""
        mock_client = mock_boto3_client.return_value
        mock_response = MagicMock()
        mock_response.__getitem__ = MagicMock(return_value=MagicMock(read=lambda: b"csv,data"))
        mock_client.get_object.return_value = {"Body": MagicMock(read=lambda: b"csv,data")}

        result = spaces_client.download_file("datasets/test.csv")

        mock_client.get_object.assert_called_once_with(
            Bucket="test-bucket", Key="datasets/test.csv"
        )
        assert result == b"csv,data"

    def test_download_not_found(self, spaces_client, mock_boto3_client):
        """Test download of non-existent file."""
        mock_client = mock_boto3_client.return_value
        mock_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not found"}},
            "GetObject",
        )

        with pytest.raises(SpacesError) as exc:
            spaces_client.download_file("nonexistent.csv")

        assert exc.value.operation == "download"


class TestSpacesClientDelete:
    """Tests for delete operations."""

    def test_delete_success(self, spaces_client, mock_boto3_client):
        """Test deleting file."""
        mock_client = mock_boto3_client.return_value

        result = spaces_client.delete_file("datasets/test.csv")

        mock_client.delete_object.assert_called_once_with(
            Bucket="test-bucket", Key="datasets/test.csv"
        )
        assert result is True

    def test_delete_failure(self, spaces_client, mock_boto3_client):
        """Test delete failure."""
        mock_client = mock_boto3_client.return_value
        mock_client.delete_object.side_effect = ClientError(
            {"Error": {"Code": "InternalError", "Message": "Server error"}},
            "DeleteObject",
        )

        with pytest.raises(SpacesError) as exc:
            spaces_client.delete_file("test.csv")

        assert exc.value.operation == "delete"


class TestSpacesClientPresignedUrl:
    """Tests for presigned URL generation."""

    def test_presigned_url_get(self, spaces_client, mock_boto3_client):
        """Test generating presigned GET URL."""
        mock_client = mock_boto3_client.return_value
        mock_client.generate_presigned_url.return_value = "https://signed-url.com/test"

        result = spaces_client.generate_presigned_url("datasets/test.csv", expires_in=7200)

        mock_client.generate_presigned_url.assert_called_once_with(
            ClientMethod="get_object",
            Params={"Bucket": "test-bucket", "Key": "datasets/test.csv"},
            ExpiresIn=7200,
        )
        assert result == "https://signed-url.com/test"

    def test_presigned_url_put(self, spaces_client, mock_boto3_client):
        """Test generating presigned PUT URL."""
        mock_client = mock_boto3_client.return_value
        mock_client.generate_presigned_url.return_value = "https://signed-url.com/upload"

        spaces_client.generate_presigned_url("datasets/new.csv", expires_in=3600, http_method="PUT")

        mock_client.generate_presigned_url.assert_called_once_with(
            ClientMethod="put_object",
            Params={"Bucket": "test-bucket", "Key": "datasets/new.csv"},
            ExpiresIn=3600,
        )


class TestSpacesClientFileExists:
    """Tests for file existence checks."""

    def test_file_exists_true(self, spaces_client, mock_boto3_client):
        """Test file exists check returns true."""
        mock_client = mock_boto3_client.return_value
        mock_client.head_object.return_value = {"ContentLength": 1234}

        result = spaces_client.file_exists("datasets/test.csv")

        assert result is True

    def test_file_exists_false(self, spaces_client, mock_boto3_client):
        """Test file exists check returns false for 404."""
        mock_client = mock_boto3_client.return_value
        mock_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}},
            "HeadObject",
        )

        result = spaces_client.file_exists("nonexistent.csv")

        assert result is False


class TestSpacesClientSingleton:
    """Tests for singleton pattern."""

    def test_get_spaces_client_singleton(self, mock_boto3_client):
        """Test singleton returns same instance."""
        reset_spaces_client()

        # Mock settings to provide credentials
        with patch("backend.services.spaces.get_settings") as mock_settings:
            mock_settings.return_value.do_spaces_key = "test-key"
            mock_settings.return_value.do_spaces_secret = "test-secret"  # noqa: S105
            mock_settings.return_value.do_spaces_region = "lon1"
            mock_settings.return_value.do_spaces_bucket = "test-bucket"
            mock_settings.return_value.do_spaces_endpoint_url = (
                "https://lon1.digitaloceanspaces.com"
            )

            client1 = get_spaces_client()
            client2 = get_spaces_client()

        assert client1 is client2

    def test_reset_spaces_client(self, mock_boto3_client):
        """Test reset creates new instance."""
        reset_spaces_client()

        # Mock settings to provide credentials
        with patch("backend.services.spaces.get_settings") as mock_settings:
            mock_settings.return_value.do_spaces_key = "test-key"
            mock_settings.return_value.do_spaces_secret = "test-secret"  # noqa: S105
            mock_settings.return_value.do_spaces_region = "lon1"
            mock_settings.return_value.do_spaces_bucket = "test-bucket"
            mock_settings.return_value.do_spaces_endpoint_url = (
                "https://lon1.digitaloceanspaces.com"
            )

            client1 = get_spaces_client()
            reset_spaces_client()
            client2 = get_spaces_client()

        assert client1 is not client2


class TestSpacesConfigurationError:
    """Tests for configuration validation."""

    def test_missing_access_key_raises_error(self, mock_boto3_client):
        """Test missing access key raises SpacesConfigurationError."""
        with patch("backend.services.spaces.get_settings") as mock_settings:
            mock_settings.return_value.do_spaces_key = ""
            mock_settings.return_value.do_spaces_secret = "secret"  # noqa: S105
            mock_settings.return_value.do_spaces_region = "lon1"
            mock_settings.return_value.do_spaces_bucket = "bucket"
            mock_settings.return_value.do_spaces_endpoint_url = ""

            with pytest.raises(SpacesConfigurationError) as exc:
                SpacesClient(
                    access_key="",
                    secret_key="secret",  # noqa: S106
                    bucket="bucket",
                )
            assert "DO_SPACES_KEY" in exc.value.missing_fields
            assert exc.value.operation == "init"

    def test_missing_secret_key_raises_error(self, mock_boto3_client):
        """Test missing secret key raises SpacesConfigurationError."""
        with patch("backend.services.spaces.get_settings") as mock_settings:
            mock_settings.return_value.do_spaces_key = "key"
            mock_settings.return_value.do_spaces_secret = ""
            mock_settings.return_value.do_spaces_region = "lon1"
            mock_settings.return_value.do_spaces_bucket = "bucket"
            mock_settings.return_value.do_spaces_endpoint_url = ""

            with pytest.raises(SpacesConfigurationError) as exc:
                SpacesClient(
                    access_key="key",
                    secret_key="",  # noqa: S106
                    bucket="bucket",
                )
            assert "DO_SPACES_SECRET" in exc.value.missing_fields

    def test_missing_bucket_raises_error(self, mock_boto3_client):
        """Test missing bucket raises SpacesConfigurationError."""
        # Mock settings to return empty bucket (otherwise default is used)
        with patch("backend.services.spaces.get_settings") as mock_settings:
            mock_settings.return_value.do_spaces_key = ""
            mock_settings.return_value.do_spaces_secret = ""
            mock_settings.return_value.do_spaces_region = "lon1"
            mock_settings.return_value.do_spaces_bucket = ""  # Empty bucket
            mock_settings.return_value.do_spaces_endpoint_url = ""

            with pytest.raises(SpacesConfigurationError) as exc:
                SpacesClient(
                    access_key="key",
                    secret_key="secret",  # noqa: S106
                    # Don't pass bucket - let it use settings default (which is mocked to empty)
                )
            assert "DO_SPACES_BUCKET" in exc.value.missing_fields

    def test_missing_all_credentials_raises_error(self, mock_boto3_client):
        """Test missing all credentials lists all fields."""
        # Mock settings to return all empty
        with patch("backend.services.spaces.get_settings") as mock_settings:
            mock_settings.return_value.do_spaces_key = ""
            mock_settings.return_value.do_spaces_secret = ""
            mock_settings.return_value.do_spaces_region = "lon1"
            mock_settings.return_value.do_spaces_bucket = ""
            mock_settings.return_value.do_spaces_endpoint_url = ""

            with pytest.raises(SpacesConfigurationError) as exc:
                SpacesClient()  # No explicit args - uses settings
            assert len(exc.value.missing_fields) == 3
            assert "DO_SPACES_KEY" in exc.value.missing_fields
            assert "DO_SPACES_SECRET" in exc.value.missing_fields
            assert "DO_SPACES_BUCKET" in exc.value.missing_fields

    def test_valid_credentials_no_error(self, mock_boto3_client):
        """Test valid credentials don't raise error."""
        client = SpacesClient(
            access_key="key",
            secret_key="secret",  # noqa: S106
            bucket="bucket",
        )
        assert client.bucket == "bucket"
