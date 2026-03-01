from datetime import datetime
from http import HTTPStatus
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone
from ninja.errors import HttpError

from apps.api.rest.v0.event import EventDetail, get_event, list_events
from apps.owasp.models.event import Event as EventModel

current_timezone = timezone.get_current_timezone()


class TestEventSerializerValidation:
    @pytest.mark.parametrize(
        "event_object",
        [
            EventModel(
                description="this is a sample event",
                end_date=datetime(2023, 6, 15, tzinfo=current_timezone).date(),
                key="sample-event",
                latitude=59.9139,
                longitude=10.7522,
                name="sample event",
                start_date=datetime(2023, 6, 14, tzinfo=current_timezone).date(),
                url="https://github.com/owasp/Nest",
            ),
            EventModel(
                description=None,
                end_date=None,
                key="event-without-end-date",
                latitude=None,
                longitude=None,
                name="event without end date",
                start_date=datetime(2023, 7, 1, tzinfo=current_timezone).date(),
                url=None,
            ),
        ],
    )
    def test_event_serializer_validation(self, event_object: EventModel):
        event = EventDetail.from_orm(event_object)

        assert event.description == event_object.description
        end_date = event_object.end_date.isoformat() if event_object.end_date else None
        assert event.end_date == end_date
        assert event.key == event_object.key
        assert event.latitude == event_object.latitude
        assert event.longitude == event_object.longitude
        assert event.name == event_object.name
        assert event.start_date == event_object.start_date.isoformat()
        assert event.url == event_object.url


class TestListEvents:
    """Tests for list_events endpoint."""

    @patch("apps.api.rest.v0.event.EventModel")
    def test_list_events_default(self, mock_event_model):
        """Test listing events with default ordering."""
        mock_request = MagicMock()
        mock_filters = MagicMock()
        mock_queryset = MagicMock()
        mock_event_model.objects.all.return_value = mock_queryset
        mock_queryset.order_by.return_value = mock_queryset
        mock_filters.filter.return_value = mock_queryset

        result = list_events(
            mock_request, mock_filters, ordering=None, is_upcoming=None, category=None
        )

        mock_queryset.order_by.assert_called_with("-start_date", "-end_date")
        assert result == mock_queryset

    @patch("apps.api.rest.v0.event.EventModel")
    def test_list_events_with_ordering(self, mock_event_model):
        """Test listing events with custom ordering."""
        mock_request = MagicMock()
        mock_filters = MagicMock()
        mock_queryset = MagicMock()
        mock_event_model.objects.all.return_value = mock_queryset
        mock_queryset.order_by.return_value = mock_queryset
        mock_filters.filter.return_value = mock_queryset

        result = list_events(
            mock_request, mock_filters, ordering="latitude", is_upcoming=None, category=None
        )

        mock_queryset.order_by.assert_called_with("latitude", "-end_date")
        assert result == mock_queryset

    @patch("apps.api.rest.v0.event.EventModel")
    def test_list_events_upcoming(self, mock_event_model):
        """Test listing upcoming events."""
        mock_request = MagicMock()
        mock_filters = MagicMock()
        mock_upcoming_qs = MagicMock()
        mock_event_model.upcoming_events.return_value = mock_upcoming_qs
        mock_upcoming_qs.order_by.return_value = mock_upcoming_qs
        mock_filters.filter.return_value = mock_upcoming_qs

        result = list_events(
            mock_request, mock_filters, ordering=None, is_upcoming=True, category=None
        )

        mock_event_model.upcoming_events.assert_called_once()
        assert result == mock_upcoming_qs

    @patch("apps.api.rest.v0.event.EventModel")
    def test_list_events_with_category_filter(self, mock_event_model):
        """Test listing events with valid category filter."""
        mock_request = MagicMock()
        mock_filters = MagicMock()
        mock_queryset = MagicMock()
        mock_filtered_queryset = MagicMock()
        mock_event_model.Category.values = ["appsec_days", "global", "other", "partner"]

        mock_event_model.objects.all.return_value = mock_queryset
        mock_queryset.filter.return_value = mock_filtered_queryset
        mock_filtered_queryset.order_by.return_value = mock_filtered_queryset
        mock_filters.filter.return_value = mock_filtered_queryset

        result = list_events(
            mock_request,
            mock_filters,
            ordering=None,
            is_upcoming=None,
            category="appsec_days,global",
        )

        mock_queryset.filter.assert_called_with(category__in=["appsec_days", "global"])
        assert result == mock_filtered_queryset

    @patch("apps.api.rest.v0.event.EventModel")
    def test_list_events_invalid_category(self, mock_event_model):
        mock_request = MagicMock()
        mock_filters = MagicMock()
        mock_event_model.Category.values = ["appsec_days", "global", "other", "partner"]

        with pytest.raises(HttpError):
            list_events(
                mock_request,
                mock_filters,
                ordering=None,
                is_upcoming=None,
                category="invalid_category",
            )


class TestGetEvent:
    """Tests for get_event endpoint."""

    @patch("apps.api.rest.v0.event.EventModel")
    def test_get_event_success(self, mock_event_model):
        """Test getting an event when found."""
        mock_request = MagicMock()
        mock_event = MagicMock()
        mock_event_model.objects.filter.return_value.first.return_value = mock_event

        result = get_event(mock_request, "sample-event")

        mock_event_model.objects.filter.assert_called_with(key__iexact="sample-event")
        assert result == mock_event

    @patch("apps.api.rest.v0.event.EventModel")
    def test_get_event_not_found(self, mock_event_model):
        """Test getting an event when not found."""
        mock_request = MagicMock()
        mock_event_model.objects.filter.return_value.first.return_value = None

        result = get_event(mock_request, "nonexistent-event")

        assert result.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
class TestEventIntegration:
    """Integration tests for event API endpoints."""

    def test_list_events_with_category_integration(self, client):
        """Test API endpoint with real DB events filtering by category."""
        today = timezone.now().date()
        EventModel.objects.create(
            key="conf-1",
            name="Conference 1",
            start_date=today,
            category=EventModel.Category.GLOBAL,
        )
        EventModel.objects.create(
            key="work-1",
            name="Workshop 1",
            start_date=today,
            category=EventModel.Category.APPSEC_DAYS,
        )
        EventModel.objects.create(
            key="train-1",
            name="Training 1",
            start_date=today,
            category=EventModel.Category.PARTNER,
        )

        response = client.get("/api/v0/events/?category=global")
        assert response.status_code == HTTPStatus.OK
        data = response.json()

        # Data format is likely paginated under 'items' since it's RouterPaginated
        items = data.get("items", data)
        if isinstance(items, dict):
            # Fallback if structure is e.g. {"data": [...], "count": ...}
            items = items.get("data", items)

        assert len(items) == 1
        assert items[0]["key"] == "conf-1"

    def test_get_event_integration_success(self, client):
        """Test retrieving a single event from the database."""
        today = timezone.now().date()
        EventModel.objects.create(
            key="test-event-integration",
            name="Integration Test Event",
            start_date=today,
            category=EventModel.Category.GLOBAL,
        )

        response = client.get("/api/v0/events/test-event-integration")
        assert response.status_code == HTTPStatus.OK

        data = response.json()
        assert data["key"] == "test-event-integration"
        assert data["name"] == "Integration Test Event"

    def test_get_event_integration_not_found(self, client):
        """Test retrieving a non-existent event."""
        response = client.get("/api/v0/events/non-existent-event-abc")
        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json() == {"message": "Event not found"}
