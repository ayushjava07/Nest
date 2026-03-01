from http import HTTPStatus
from unittest.mock import MagicMock, patch

import pytest
from ninja.errors import HttpError

from apps.api.rest.v0.project import list_projects


class TestListProjectsFiltering:
    """Unit tests for the list_projects endpoint filtering by type."""

    @patch("apps.api.rest.v0.project.apply_structured_search")
    @patch("apps.api.rest.v0.project.ProjectModel")
    def test_list_projects_without_type_filter(self, mock_project_model, mock_apply_search):
        """Test listing projects when no type filter is provided."""
        mock_request = MagicMock()
        mock_filters = MagicMock()
        mock_filters.type = None
        mock_filters.level = None
        mock_filters.q = None

        mock_queryset = MagicMock()
        mock_apply_search.return_value = mock_queryset
        mock_queryset.order_by.return_value = mock_queryset

        result = list_projects(mock_request, mock_filters, ordering=None)

        # Ensure no type filtering was applied to the queryset
        for call_args in mock_queryset.filter.call_args_list:
            assert "type__in" not in call_args.kwargs

        mock_queryset.order_by.assert_called()
        assert result == mock_queryset

    @patch("apps.api.rest.v0.project.apply_structured_search")
    @patch("apps.api.rest.v0.project.ProjectModel")
    def test_list_projects_single_type_filter(self, mock_project_model, mock_apply_search):
        """Test filtering projects by a single type."""
        mock_request = MagicMock()
        mock_filters = MagicMock()
        mock_filters.type = "tool"
        mock_filters.level = None
        mock_filters.q = None

        mock_queryset = MagicMock()
        mock_filtered_queryset = MagicMock()
        mock_apply_search.return_value = mock_queryset
        mock_queryset.filter.return_value = mock_filtered_queryset
        mock_filtered_queryset.order_by.return_value = mock_filtered_queryset

        result = list_projects(mock_request, mock_filters)

        mock_queryset.filter.assert_called_with(type__in=["tool"])
        assert result == mock_filtered_queryset

    @patch("apps.api.rest.v0.project.apply_structured_search")
    @patch("apps.api.rest.v0.project.ProjectModel")
    def test_list_projects_multiple_type_filter(self, mock_project_model, mock_apply_search):
        """Test filtering projects by multiple comma-separated types."""
        mock_request = MagicMock()
        mock_filters = MagicMock()
        mock_filters.type = "code,tool"
        mock_filters.level = None
        mock_filters.q = None

        mock_queryset = MagicMock()
        mock_filtered_queryset = MagicMock()
        mock_apply_search.return_value = mock_queryset
        mock_queryset.filter.return_value = mock_filtered_queryset
        mock_filtered_queryset.order_by.return_value = mock_filtered_queryset

        result = list_projects(mock_request, mock_filters)

        mock_queryset.filter.assert_called_with(type__in=["code", "tool"])
        assert result == mock_filtered_queryset

    @patch("apps.api.rest.v0.project.apply_structured_search")
    @patch("apps.api.rest.v0.project.ProjectModel")
    def test_list_projects_with_spaces_in_type(self, mock_project_model, mock_apply_search):
        """Test that spaces in the comma-separated type list are correctly stripped."""
        mock_request = MagicMock()
        mock_filters = MagicMock()
        mock_filters.type = "code, tool "
        mock_filters.level = None
        mock_filters.q = None

        mock_queryset = MagicMock()
        mock_filtered_queryset = MagicMock()
        mock_apply_search.return_value = mock_queryset
        mock_queryset.filter.return_value = mock_filtered_queryset
        mock_filtered_queryset.order_by.return_value = mock_filtered_queryset

        list_projects(mock_request, mock_filters)

        mock_queryset.filter.assert_called_with(type__in=["code", "tool"])

    @patch("apps.api.rest.v0.project.apply_structured_search")
    @patch("apps.api.rest.v0.project.ProjectModel")
    def test_list_projects_with_invalid_type(self, mock_project_model, mock_apply_search):
        """Test that providing an invalid type raises an HttpError."""
        mock_request = MagicMock()
        mock_filters = MagicMock()
        mock_filters.type = "invalid"
        mock_filters.level = None
        mock_filters.q = None

        mock_queryset = MagicMock()
        mock_apply_search.return_value = mock_queryset

        with pytest.raises(HttpError) as excinfo:
            list_projects(mock_request, mock_filters)

        assert excinfo.value.status_code == HTTPStatus.BAD_REQUEST
        assert "Invalid project types: invalid" in excinfo.value.message
