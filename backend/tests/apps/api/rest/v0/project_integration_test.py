from http import HTTPStatus

import pytest
from django.utils import timezone

from apps.owasp.models.enums.project import ProjectLevel, ProjectType
from apps.owasp.models.project import Project


@pytest.fixture
def project_data():
    """Create test projects with different types."""
    now = timezone.now()
    Project.objects.create(
        name="Tool Project",
        key="tool-project",
        type=ProjectType.TOOL,
        level=ProjectLevel.LAB,
        created_at=now,
        updated_at=now,
        is_active=True,
    )
    Project.objects.create(
        name="Doc Project",
        key="doc-project",
        type=ProjectType.DOCUMENTATION,
        level=ProjectLevel.LAB,
        created_at=now,
        updated_at=now,
        is_active=True,
    )
    Project.objects.create(
        name="Code Project",
        key="code-project",
        type=ProjectType.CODE,
        level=ProjectLevel.LAB,
        created_at=now,
        updated_at=now,
        is_active=True,
    )
    Project.objects.create(
        name="Other Project",
        key="other-project",
        type=ProjectType.OTHER,
        level=ProjectLevel.LAB,
        created_at=now,
        updated_at=now,
        is_active=True,
    )


@pytest.mark.django_db
class TestProjectIntegration:
    """Integration tests for project type filtering."""

    def test_list_projects_without_type_returns_all(self, client, project_data):
        """Test listing projects without a type filter returns all active projects."""
        response = client.get("/api/v0/projects/")
        assert response.status_code == HTTPStatus.OK
        data = response.json()

        # CustomPagination returns {"items": [...], "total_count": ...}
        assert "items" in data
        assert "total_count" in data
        assert data["total_count"] >= 4

        types = [item["type"] for item in data["items"]]
        assert "tool" in types
        assert "documentation" in types
        assert "code" in types
        assert "other" in types

    def test_list_projects_single_type_filter(self, client, project_data):
        """Test filtering projects by a single type."""
        response = client.get("/api/v0/projects/?type=tool")
        assert response.status_code == HTTPStatus.OK
        data = response.json()

        assert data["total_count"] == 1
        assert data["items"][0]["type"] == "tool"
        assert data["items"][0]["name"] == "Tool Project"

    def test_list_projects_multiple_type_filter(self, client, project_data):
        """Test filtering projects by multiple comma-separated types."""
        response = client.get("/api/v0/projects/?type=tool,documentation")
        assert response.status_code == HTTPStatus.OK
        data = response.json()

        assert data["total_count"] == 2
        types = {item["type"] for item in data["items"]}
        assert types == {"tool", "documentation"}

    def test_list_projects_invalid_type_returns_400(self, client, project_data):
        """Test that an invalid project type returns a 400 Bad Request."""
        response = client.get("/api/v0/projects/?type=invalid_type")
        assert response.status_code == HTTPStatus.BAD_REQUEST
        data = response.json()

        assert "message" in data
        assert "Invalid project types: invalid_type" in data["message"]
