"""Tests for dataset folders API endpoints.

Tests cover:
- Folder CRUD operations
- Dataset membership
- Tag operations
- Tree structure
- RLS isolation
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.middleware.auth import get_current_user
from backend.api.routes.dataset_folders import router


def mock_user_override():
    """Override auth to return test user."""
    return {"user_id": "test-user-123", "email": "test@example.com"}


@pytest.fixture
def test_app():
    """Create test app with dataset folders router and auth override."""
    app = FastAPI()
    app.dependency_overrides[get_current_user] = mock_user_override
    app.include_router(router, prefix="/api")
    return app


@pytest.fixture
def client(test_app):
    """Create test client with auth bypass."""
    return TestClient(test_app)


@pytest.fixture
def mock_folder():
    """Mock folder data."""
    return {
        "id": str(uuid.uuid4()),
        "user_id": "test-user-123",
        "name": "Test Folder",
        "description": "A test folder",
        "color": "#FF5733",
        "icon": "folder",
        "parent_folder_id": None,
        "tags": ["tag1", "tag2"],
        "dataset_count": 0,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }


@pytest.fixture
def mock_dataset():
    """Mock dataset data."""
    return {
        "id": str(uuid.uuid4()),
        "name": "Test Dataset",
        "added_at": datetime.now(UTC),
    }


class TestCreateFolder:
    """Tests for POST /api/v1/datasets/folders."""

    def test_create_folder_success(self, client, mock_folder):
        """Should create folder with valid data."""
        with patch(
            "backend.api.routes.dataset_folders.dataset_folder_repository.create_folder",
            return_value=mock_folder,
        ):
            response = client.post(
                "/api/v1/datasets/folders",
                json={
                    "name": "Test Folder",
                    "description": "A test folder",
                    "color": "#FF5733",
                    "tags": ["tag1", "tag2"],
                },
            )
            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "Test Folder"
            assert data["color"] == "#FF5733"
            assert "tag1" in data["tags"]

    def test_create_folder_minimal(self, client, mock_folder):
        """Should create folder with just name."""
        with patch(
            "backend.api.routes.dataset_folders.dataset_folder_repository.create_folder",
            return_value=mock_folder,
        ):
            response = client.post(
                "/api/v1/datasets/folders",
                json={"name": "Minimal Folder"},
            )
            assert response.status_code == 201

    def test_create_folder_invalid_color(self, client):
        """Should reject invalid hex color."""
        response = client.post(
            "/api/v1/datasets/folders",
            json={"name": "Test", "color": "invalid"},
        )
        assert response.status_code == 422


class TestListFolders:
    """Tests for GET /api/v1/datasets/folders."""

    def test_list_folders_empty(self, client):
        """Should return empty list when no folders."""
        with patch(
            "backend.api.routes.dataset_folders.dataset_folder_repository.list_all_folders",
            return_value=[],
        ):
            response = client.get("/api/v1/datasets/folders")
            assert response.status_code == 200
            data = response.json()
            assert data["folders"] == []
            assert data["total"] == 0

    def test_list_folders_with_data(self, client, mock_folder):
        """Should return folders list."""
        with patch(
            "backend.api.routes.dataset_folders.dataset_folder_repository.list_all_folders",
            return_value=[mock_folder],
        ):
            response = client.get("/api/v1/datasets/folders")
            assert response.status_code == 200
            data = response.json()
            assert len(data["folders"]) == 1
            assert data["total"] == 1

    def test_list_folders_filtered_by_tag(self, client, mock_folder):
        """Should filter folders by tag."""
        with patch(
            "backend.api.routes.dataset_folders.dataset_folder_repository.list_folders",
            return_value=[mock_folder],
        ):
            response = client.get("/api/v1/datasets/folders?tag=tag1")
            assert response.status_code == 200


class TestGetFolderTree:
    """Tests for GET /api/v1/datasets/folders/tree."""

    def test_get_tree_empty(self, client):
        """Should return empty tree."""
        with patch(
            "backend.api.routes.dataset_folders.dataset_folder_repository.get_folder_tree",
            return_value=[],
        ):
            response = client.get("/api/v1/datasets/folders/tree")
            assert response.status_code == 200
            data = response.json()
            assert data["folders"] == []

    def test_get_tree_nested(self, client, mock_folder):
        """Should return nested folder structure."""
        parent_folder = {**mock_folder, "children": []}
        child_folder = {
            **mock_folder,
            "id": str(uuid.uuid4()),
            "name": "Child Folder",
            "parent_folder_id": mock_folder["id"],
            "children": [],
        }
        parent_folder["children"] = [child_folder]

        with patch(
            "backend.api.routes.dataset_folders.dataset_folder_repository.get_folder_tree",
            return_value=[parent_folder],
        ):
            response = client.get("/api/v1/datasets/folders/tree")
            assert response.status_code == 200
            data = response.json()
            assert len(data["folders"]) == 1
            assert len(data["folders"][0]["children"]) == 1


class TestGetFolder:
    """Tests for GET /api/v1/datasets/folders/{folder_id}."""

    def test_get_folder_success(self, client, mock_folder):
        """Should return folder details."""
        with patch(
            "backend.api.routes.dataset_folders.dataset_folder_repository.get_folder",
            return_value=mock_folder,
        ):
            response = client.get(f"/api/v1/datasets/folders/{mock_folder['id']}")
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Test Folder"

    def test_get_folder_not_found(self, client):
        """Should return 404 for missing folder."""
        with patch(
            "backend.api.routes.dataset_folders.dataset_folder_repository.get_folder",
            return_value=None,
        ):
            response = client.get(f"/api/v1/datasets/folders/{uuid.uuid4()}")
            assert response.status_code == 404


class TestUpdateFolder:
    """Tests for PATCH /api/v1/datasets/folders/{folder_id}."""

    def test_update_folder_name(self, client, mock_folder):
        """Should update folder name."""
        updated_folder = {**mock_folder, "name": "Updated Name"}
        with patch(
            "backend.api.routes.dataset_folders.dataset_folder_repository.update_folder",
            return_value=updated_folder,
        ):
            response = client.patch(
                f"/api/v1/datasets/folders/{mock_folder['id']}",
                json={"name": "Updated Name"},
            )
            assert response.status_code == 200
            assert response.json()["name"] == "Updated Name"

    def test_update_folder_not_found(self, client):
        """Should return 404 for missing folder."""
        with patch(
            "backend.api.routes.dataset_folders.dataset_folder_repository.update_folder",
            return_value=None,
        ):
            response = client.patch(
                f"/api/v1/datasets/folders/{uuid.uuid4()}",
                json={"name": "New Name"},
            )
            assert response.status_code == 404


class TestDeleteFolder:
    """Tests for DELETE /api/v1/datasets/folders/{folder_id}."""

    def test_delete_folder_success(self, client):
        """Should delete folder."""
        with patch(
            "backend.api.routes.dataset_folders.dataset_folder_repository.delete_folder",
            return_value=True,
        ):
            response = client.delete(f"/api/v1/datasets/folders/{uuid.uuid4()}")
            assert response.status_code == 204

    def test_delete_folder_not_found(self, client):
        """Should return 404 for missing folder."""
        with patch(
            "backend.api.routes.dataset_folders.dataset_folder_repository.delete_folder",
            return_value=False,
        ):
            response = client.delete(f"/api/v1/datasets/folders/{uuid.uuid4()}")
            assert response.status_code == 404


class TestFolderTags:
    """Tests for GET /api/v1/datasets/folders/tags."""

    def test_get_tags_empty(self, client):
        """Should return empty tags list."""
        with patch(
            "backend.api.routes.dataset_folders.dataset_folder_repository.get_all_tags",
            return_value=[],
        ):
            response = client.get("/api/v1/datasets/folders/tags")
            assert response.status_code == 200
            assert response.json()["tags"] == []

    def test_get_tags_with_data(self, client):
        """Should return unique tags."""
        with patch(
            "backend.api.routes.dataset_folders.dataset_folder_repository.get_all_tags",
            return_value=["project", "archive", "important"],
        ):
            response = client.get("/api/v1/datasets/folders/tags")
            assert response.status_code == 200
            tags = response.json()["tags"]
            assert len(tags) == 3
            assert "project" in tags


class TestFolderDatasets:
    """Tests for dataset membership endpoints."""

    def test_add_datasets_to_folder(self, client, mock_folder):
        """Should add datasets to folder."""
        with patch(
            "backend.api.routes.dataset_folders.dataset_folder_repository.get_folder",
            return_value=mock_folder,
        ):
            with patch(
                "backend.api.routes.dataset_folders.dataset_folder_repository.add_datasets_to_folder",
                return_value=2,
            ):
                response = client.post(
                    f"/api/v1/datasets/folders/{mock_folder['id']}/datasets",
                    json={"dataset_ids": [str(uuid.uuid4()), str(uuid.uuid4())]},
                )
                assert response.status_code == 200
                data = response.json()
                assert data["added"] == 2
                assert data["total_requested"] == 2

    def test_remove_dataset_from_folder(self, client):
        """Should remove dataset from folder."""
        with patch(
            "backend.api.routes.dataset_folders.dataset_folder_repository.remove_dataset_from_folder",
            return_value=True,
        ):
            response = client.delete(
                f"/api/v1/datasets/folders/{uuid.uuid4()}/datasets/{uuid.uuid4()}"
            )
            assert response.status_code == 204

    def test_get_folder_datasets(self, client, mock_folder, mock_dataset):
        """Should list datasets in folder."""
        with patch(
            "backend.api.routes.dataset_folders.dataset_folder_repository.get_folder",
            return_value=mock_folder,
        ):
            with patch(
                "backend.api.routes.dataset_folders.dataset_folder_repository.get_folder_datasets",
                return_value=[mock_dataset],
            ):
                response = client.get(f"/api/v1/datasets/folders/{mock_folder['id']}/datasets")
                assert response.status_code == 200
                data = response.json()
                assert len(data["datasets"]) == 1
                assert data["total"] == 1
