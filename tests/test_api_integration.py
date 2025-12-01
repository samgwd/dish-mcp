"""Integration tests for API calls with mocked HTTP responses."""

import pytest
import responses
from book_room import book_room
from cancel_booking import cancel_booking
from room_availability.api import _serialise_resource_ids, get_room_availability
from utils.constants import (
    BOOKINGS_ENDPOINT,
    BOOKINGS_OCCURRENCES_ENDPOINT,
    get_cancel_booking_endpoint,
)
from utils.type_defs import DatetimeRange, UserInfo


class TestSerialiseResourceIds:
    """Tests for _serialise_resource_ids function."""

    def test_string_input_returned_as_is(self) -> None:
        """String input is returned unchanged."""
        result = _serialise_resource_ids("id1,id2,id3")

        assert result == "id1,id2,id3"

    def test_list_input_joined(self) -> None:
        """List input is joined with commas."""
        result = _serialise_resource_ids(["id1", "id2", "id3"])

        assert result == "id1,id2,id3"

    def test_single_item_list(self) -> None:
        """Single item list returns just that item."""
        result = _serialise_resource_ids(["single_id"])

        assert result == "single_id"

    def test_empty_list(self) -> None:
        """Empty list returns empty string."""
        result = _serialise_resource_ids([])

        assert result == ""


class TestGetRoomAvailability:
    """Tests for get_room_availability API function."""

    @responses.activate
    def test_sends_correct_params(self) -> None:
        """Verify correct query parameters are sent."""
        responses.add(
            responses.GET,
            BOOKINGS_OCCURRENCES_ENDPOINT,
            json=[],
            status=200,
        )

        datetime_range = DatetimeRange(
            start_datetime="2025-01-15T09:00:00Z",
            end_datetime="2025-01-15T17:00:00Z",
        )
        resource_ids = ["id1", "id2"]

        get_room_availability(
            resource_ids=resource_ids,
            datetime_range=datetime_range,
            cookie="connect.sid=test_cookie",
        )

        assert len(responses.calls) == 1
        request = responses.calls[0].request

        # Check query params
        assert "resourceId=id1%2Cid2" in request.url or "resourceId=id1,id2" in request.url
        assert "start=2025-01-15T09" in request.url
        assert "end=2025-01-15T17" in request.url

    @responses.activate
    def test_sends_correct_headers(self) -> None:
        """Verify correct headers are sent."""
        responses.add(
            responses.GET,
            BOOKINGS_OCCURRENCES_ENDPOINT,
            json=[],
            status=200,
        )

        datetime_range = DatetimeRange(
            start_datetime="2025-01-15T09:00:00Z",
            end_datetime="2025-01-15T17:00:00Z",
        )

        get_room_availability(
            resource_ids=["id1"],
            datetime_range=datetime_range,
            cookie="connect.sid=my_session",
        )

        request = responses.calls[0].request
        assert request.headers["Cookie"] == "connect.sid=my_session"
        assert request.headers["Content-Type"] == "application/json"

    @responses.activate
    def test_returns_response_on_success(self) -> None:
        """Return response object on success."""
        expected_data = [{"bookingId": "123", "resourceId": "room1"}]
        responses.add(
            responses.GET,
            BOOKINGS_OCCURRENCES_ENDPOINT,
            json=expected_data,
            status=200,
        )

        datetime_range = DatetimeRange(
            start_datetime="2025-01-15T09:00:00Z",
            end_datetime="2025-01-15T17:00:00Z",
        )

        response = get_room_availability(
            resource_ids=["id1"],
            datetime_range=datetime_range,
            cookie="connect.sid=test",
        )

        assert response.status_code == 200
        assert response.json() == expected_data

    @responses.activate
    def test_raises_on_http_error(self) -> None:
        """Raise exception on HTTP error status."""
        responses.add(
            responses.GET,
            BOOKINGS_OCCURRENCES_ENDPOINT,
            json={"error": "Unauthorised"},
            status=401,
        )

        datetime_range = DatetimeRange(
            start_datetime="2025-01-15T09:00:00Z",
            end_datetime="2025-01-15T17:00:00Z",
        )

        with pytest.raises(Exception):  # noqa: B017
            get_room_availability(
                resource_ids=["id1"],
                datetime_range=datetime_range,
                cookie="connect.sid=invalid",
            )

    @responses.activate
    def test_custom_select_and_populate(self) -> None:
        """Verify custom select and populate parameters."""
        responses.add(
            responses.GET,
            BOOKINGS_OCCURRENCES_ENDPOINT,
            json=[],
            status=200,
        )

        datetime_range = DatetimeRange(
            start_datetime="2025-01-15T09:00:00Z",
            end_datetime="2025-01-15T17:00:00Z",
        )

        get_room_availability(
            resource_ids=["id1"],
            datetime_range=datetime_range,
            cookie="connect.sid=test",
            select="custom_select",
            populate="custom_populate",
        )

        request = responses.calls[0].request
        assert "%24select=custom_select" in request.url or "$select=custom_select" in request.url


class TestBookRoom:
    """Tests for book_room API function."""

    @responses.activate
    def test_sends_correct_payload(self) -> None:
        """Verify correct JSON payload is sent."""
        responses.add(
            responses.POST,
            BOOKINGS_ENDPOINT,
            json={"bookingId": "new123"},
            status=201,
        )

        datetime_range: DatetimeRange = {
            "start_datetime": "2025-01-15T10:00:00.000Z",
            "end_datetime": "2025-01-15T11:00:00.000Z",
        }
        user_info: UserInfo = {
            "team_id": "team123",
            "member_id": "member456",
        }

        book_room(
            datetime_range=datetime_range,
            meeting_room_name="Boyle",
            user_info=user_info,
            cookie="connect.sid=test",
            summary="Test Meeting",
        )

        assert len(responses.calls) == 1
        request = responses.calls[0].request
        import json

        payload = json.loads(request.body)

        assert payload["start"]["dateTime"] == "2025-01-15T10:00:00.000Z"
        assert payload["end"]["dateTime"] == "2025-01-15T11:00:00.000Z"
        assert payload["resourceId"] == "6422bced61d5854ab3fedd62"  # Boyle
        assert payload["team"] == "team123"
        assert payload["member"] == "member456"
        assert payload["summary"] == "Test Meeting"
        assert payload["timezone"] == "Europe/London"

    @responses.activate
    def test_sends_correct_headers(self) -> None:
        """Verify correct headers are sent."""
        responses.add(
            responses.POST,
            BOOKINGS_ENDPOINT,
            json={"bookingId": "new123"},
            status=201,
        )

        datetime_range: DatetimeRange = {
            "start_datetime": "2025-01-15T10:00:00.000Z",
            "end_datetime": "2025-01-15T11:00:00.000Z",
        }
        user_info: UserInfo = {
            "team_id": "team123",
            "member_id": "member456",
        }

        book_room(
            datetime_range=datetime_range,
            meeting_room_name="Boyle",
            user_info=user_info,
            cookie="connect.sid=my_cookie",
            summary="Test",
        )

        request = responses.calls[0].request
        assert request.headers["Cookie"] == "connect.sid=my_cookie"
        assert request.headers["Content-Type"] == "application/json"

    def test_raises_on_unknown_room(self) -> None:
        """Raise ValueError for unknown room name."""
        datetime_range: DatetimeRange = {
            "start_datetime": "2025-01-15T10:00:00.000Z",
            "end_datetime": "2025-01-15T11:00:00.000Z",
        }
        user_info: UserInfo = {
            "team_id": "team123",
            "member_id": "member456",
        }

        with pytest.raises(ValueError, match="Unknown meeting room"):
            book_room(
                datetime_range=datetime_range,
                meeting_room_name="NonExistentRoom",
                user_info=user_info,
                cookie="connect.sid=test",
                summary="Test",
            )

    @responses.activate
    def test_returns_response_on_success(self) -> None:
        """Return response object on success."""
        expected_data = {"bookingId": "success123", "reference": "REF001"}
        responses.add(
            responses.POST,
            BOOKINGS_ENDPOINT,
            json=expected_data,
            status=201,
        )

        datetime_range: DatetimeRange = {
            "start_datetime": "2025-01-15T10:00:00.000Z",
            "end_datetime": "2025-01-15T11:00:00.000Z",
        }
        user_info: UserInfo = {
            "team_id": "team123",
            "member_id": "member456",
        }

        response = book_room(
            datetime_range=datetime_range,
            meeting_room_name="Pankhurst",
            user_info=user_info,
            cookie="connect.sid=test",
            summary="Test",
        )

        assert response.status_code == 201
        assert response.json() == expected_data


class TestCancelBooking:
    """Tests for cancel_booking API function."""

    @responses.activate
    def test_sends_correct_url(self) -> None:
        """Verify correct URL is used."""
        booking_id = "booking_to_cancel"
        expected_url = get_cancel_booking_endpoint(booking_id)

        responses.add(
            responses.POST,
            expected_url,
            json={"cancelled": True},
            status=200,
        )

        cancel_booking(
            booking_id=booking_id,
            cookie="connect.sid=test",
        )

        assert len(responses.calls) == 1
        assert responses.calls[0].request.url.startswith(expected_url)

    @responses.activate
    def test_sends_correct_headers(self) -> None:
        """Verify correct headers are sent."""
        booking_id = "test123"
        responses.add(
            responses.POST,
            get_cancel_booking_endpoint(booking_id),
            json={"cancelled": True},
            status=200,
        )

        cancel_booking(
            booking_id=booking_id,
            cookie="connect.sid=my_session",
        )

        request = responses.calls[0].request
        assert request.headers["Cookie"] == "connect.sid=my_session"
        assert request.headers["Content-Type"] == "application/json"

    @responses.activate
    def test_skip_cancellation_policy_false(self) -> None:
        """Verify skipCancellationPolicy param when False."""
        booking_id = "test123"
        responses.add(
            responses.POST,
            get_cancel_booking_endpoint(booking_id),
            json={"cancelled": True},
            status=200,
        )

        cancel_booking(
            booking_id=booking_id,
            cookie="connect.sid=test",
            skip_cancellation_policy=False,
        )

        request = responses.calls[0].request
        assert "skipCancellationPolicy=false" in request.url

    @responses.activate
    def test_skip_cancellation_policy_true(self) -> None:
        """Verify skipCancellationPolicy param when True."""
        booking_id = "test123"
        responses.add(
            responses.POST,
            get_cancel_booking_endpoint(booking_id),
            json={"cancelled": True},
            status=200,
        )

        cancel_booking(
            booking_id=booking_id,
            cookie="connect.sid=test",
            skip_cancellation_policy=True,
        )

        request = responses.calls[0].request
        assert "skipCancellationPolicy=true" in request.url

    @responses.activate
    def test_returns_response_on_success(self) -> None:
        """Return response object on success."""
        booking_id = "test123"
        expected_data = {"cancelled": True, "bookingId": booking_id}
        responses.add(
            responses.POST,
            get_cancel_booking_endpoint(booking_id),
            json=expected_data,
            status=200,
        )

        response = cancel_booking(
            booking_id=booking_id,
            cookie="connect.sid=test",
        )

        assert response.status_code == 200
        assert response.json() == expected_data
