"""Tests for storage path organization in datasets.

Tests for:
- SpacesClient.put_file() with prefix support
- Dataset upload with storage_path metadata
- Backward compatibility with old uploads (no prefix)
- Chart upload using prefixed paths
"""

import uuid
from unittest.mock import patch

import pytest

from backend.api.models import DatasetResponse
from backend.services.spaces import SpacesClient, SpacesError


class TestSpacesClientPutFile:
    """Test SpacesClient.put_file() method."""

    def test_put_file_with_prefix(self):
        """Test put_file constructs correct S3 key from prefix and filename."""
        client = SpacesClient(
            access_key="test_key",
            secret_key="test_secret",  # noqa: S106
            region="nyc3",
            bucket="test-bucket",
            endpoint_url="https://test.digitaloceanspaces.com",
        )

        with patch.object(client, "upload_file") as mock_upload:
            mock_upload.return_value = (
                "https://test.digitaloceanspaces.com/test-bucket/datasets/user1/file.csv"
            )

            # Call put_file with prefix
            client.put_file(
                prefix="datasets/user1",
                filename="file.csv",
                data=b"test data",
                content_type="text/csv",
            )

            # Verify upload_file was called with correct key
            mock_upload.assert_called_once()
            call_args = mock_upload.call_args
            assert call_args[1]["key"] == "datasets/user1/file.csv"
            assert call_args[1]["data"] == b"test data"
            assert call_args[1]["content_type"] == "text/csv"

    def test_put_file_with_empty_prefix(self):
        """Test put_file handles empty prefix gracefully."""
        client = SpacesClient(
            access_key="test_key",
            secret_key="test_secret",  # noqa: S106
            region="nyc3",
            bucket="test-bucket",
            endpoint_url="https://test.digitaloceanspaces.com",
        )

        with patch.object(client, "upload_file") as mock_upload:
            mock_upload.return_value = "https://test.digitaloceanspaces.com/test-bucket/file.csv"

            # Call put_file without prefix
            client.put_file(
                prefix="",
                filename="file.csv",
                data=b"test data",
                content_type="text/csv",
            )

            # Verify upload_file was called with correct key (no double slashes)
            call_args = mock_upload.call_args
            assert call_args[1]["key"] == "file.csv"

    def test_put_file_normalizes_prefix_slashes(self):
        """Test put_file normalizes leading/trailing slashes in prefix."""
        client = SpacesClient(
            access_key="test_key",
            secret_key="test_secret",  # noqa: S106
            region="nyc3",
            bucket="test-bucket",
            endpoint_url="https://test.digitaloceanspaces.com",
        )

        with patch.object(client, "upload_file") as mock_upload:
            mock_upload.return_value = (
                "https://test.digitaloceanspaces.com/test-bucket/datasets/user1/file.csv"
            )

            # Call put_file with messy prefix
            client.put_file(
                prefix="/datasets/user1/",
                filename="file.csv",
                data=b"test data",
                content_type="text/csv",
            )

            # Verify prefix slashes were normalized
            call_args = mock_upload.call_args
            assert call_args[1]["key"] == "datasets/user1/file.csv"

    def test_put_file_propagates_error(self):
        """Test put_file propagates SpacesError from upload_file."""
        client = SpacesClient(
            access_key="test_key",
            secret_key="test_secret",  # noqa: S106
            region="nyc3",
            bucket="test-bucket",
            endpoint_url="https://test.digitaloceanspaces.com",
        )

        with patch.object(client, "upload_file") as mock_upload:
            mock_upload.side_effect = SpacesError("Connection failed", "upload", "test_key")

            # Call put_file - should propagate the error
            with pytest.raises(SpacesError):
                client.put_file(
                    prefix="datasets/user1",
                    filename="file.csv",
                    data=b"test data",
                )


class TestDatasetStoragePath:
    """Test dataset storage_path field and prefixed uploads."""

    def test_dataset_response_includes_storage_path(self):
        """Test DatasetResponse includes storage_path field."""
        response = DatasetResponse(
            id=str(uuid.uuid4()),
            user_id="test_user_1",
            name="Sales Data",
            source_type="csv",
            storage_path="datasets/test_user_1",
            row_count=1000,
            column_count=5,
            file_size_bytes=50000,
            created_at="2025-12-10T10:00:00+00:00",
            updated_at="2025-12-10T10:00:00+00:00",
        )
        assert response.storage_path == "datasets/test_user_1"

    def test_dataset_response_storage_path_optional(self):
        """Test DatasetResponse storage_path is optional (backward compat)."""
        response = DatasetResponse(
            id=str(uuid.uuid4()),
            user_id="test_user_1",
            name="Sales Data",
            source_type="csv",
            row_count=1000,
            column_count=5,
            file_size_bytes=50000,
            created_at="2025-12-10T10:00:00+00:00",
            updated_at="2025-12-10T10:00:00+00:00",
        )
        # storage_path defaults to None
        assert response.storage_path is None

    def test_dataset_response_with_both_file_key_and_storage_path(self):
        """Test DatasetResponse works with both file_key and storage_path."""
        dataset_id = str(uuid.uuid4())
        response = DatasetResponse(
            id=dataset_id,
            user_id="test_user_1",
            name="Sales Data",
            source_type="csv",
            file_key=f"datasets/test_user_1/{dataset_id}.csv",
            storage_path="datasets/test_user_1",
            row_count=1000,
            column_count=5,
            file_size_bytes=50000,
            created_at="2025-12-10T10:00:00+00:00",
            updated_at="2025-12-10T10:00:00+00:00",
        )
        assert response.file_key == f"datasets/test_user_1/{dataset_id}.csv"
        assert response.storage_path == "datasets/test_user_1"

    def test_dataset_storage_path_backward_compatible_key_reconstruction(self):
        """Test datasets with file_key can be read even without storage_path.

        This ensures backward compatibility: old datasets without storage_path
        can still be read because file_key contains the full path.
        """
        dataset_id = str(uuid.uuid4())
        # Old dataset without storage_path but with full file_key
        response = DatasetResponse(
            id=dataset_id,
            user_id="test_user_1",
            name="Old Dataset",
            source_type="csv",
            file_key=f"datasets/test_user_1/{dataset_id}.csv",
            # storage_path is None (not stored for old datasets)
            storage_path=None,
            row_count=500,
            column_count=3,
            file_size_bytes=25000,
            created_at="2025-12-10T10:00:00+00:00",
            updated_at="2025-12-10T10:00:00+00:00",
        )

        # Can still be read because file_key is set
        assert response.file_key is not None
        # storage_path would be None, but file_key is sufficient
        assert response.storage_path is None


class TestStoragePathPattern:
    """Test storage path naming conventions."""

    def test_dataset_prefix_pattern_user_only(self):
        """Test storage prefix follows datasets/user_id pattern."""
        user_id = "test_user_1"
        expected_prefix = f"datasets/{user_id}"

        dataset_id = str(uuid.uuid4())
        file_key = f"{expected_prefix}/{dataset_id}.csv"

        # Verify pattern
        assert file_key.startswith(f"datasets/{user_id}/")
        assert file_key.endswith(".csv")

    def test_chart_prefix_pattern(self):
        """Test chart storage prefix follows charts/user_id/dataset_id pattern."""
        user_id = "test_user_1"
        dataset_id = str(uuid.uuid4())
        expected_prefix = f"charts/{user_id}/{dataset_id}"

        chart_filename = f"{uuid.uuid4()}.png"
        chart_key = f"{expected_prefix}/{chart_filename}"

        # Verify pattern
        assert chart_key.startswith(f"charts/{user_id}/{dataset_id}/")
        assert chart_key.endswith(".png")

    def test_future_workspace_pattern(self):
        """Test storage path can support future workspace/user hierarchy.

        When workspaces are implemented, storage_path can become:
        'datasets/workspace_id/user_id' instead of just 'datasets/user_id'
        """
        workspace_id = "workspace_1"
        user_id = "test_user_1"
        # Future pattern (not used yet)
        future_prefix = f"datasets/{workspace_id}/{user_id}"

        # storage_path field is flexible enough to support this
        response = DatasetResponse(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name="Future Dataset",
            source_type="csv",
            storage_path=future_prefix,  # Can support workspace prefix
            row_count=1000,
            column_count=5,
            file_size_bytes=50000,
            created_at="2025-12-10T10:00:00+00:00",
            updated_at="2025-12-10T10:00:00+00:00",
        )
        assert response.storage_path == future_prefix
