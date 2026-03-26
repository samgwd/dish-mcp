"""Integration tests for MCP tool functions."""

import os
from unittest.mock import patch

import responses
from get_credentials import DishCredentials
from mcp_server import book_room as book_room_tool
from mcp_server import cancel_booking as cancel_booking_tool
from mcp_server import (
    check_availability_and_list_bookings as check_availability_tool,
)
from utils.constants import (
    BOOKINGS_ENDPOINT,
    BOOKINGS_OCCURRENCES_ENDPOINT,
    get_cancel_booking_endpoint,
)
from utils.type_defs import DatetimeRange, UserInfo

# Access the underlying functions from FastMCP FunctionTool objects
check_availability_and_list_bookings = check_availability_tool.fn
book_room = book_room_tool.fn
cancel_booking = cancel_booking_tool.fn


class TestCheckAvailabilityAndListBookings:
    """Tests for check_availability_and_list_bookings MCP tool."""

    def test_returns_error_when_no_cookie_provided(self) -> None:
        """Return error when no cookie provided and env var not set."""
        datetime_range = DatetimeRange(
            start_datetime="2025-01-15T09:00:00Z",
            end_datetime="2025-01-15T17:00:00Z",
        )

        # Ensure env var is not set
        with patch.dict(os.environ, {}, clear=True):
            result = check_availability_and_list_bookings(datetime_range)

        assert "Error" in result
        assert "cookie" in result.lower()

    def test_uses_env_cookie_when_not_provided(self) -> None:
        """Use DISH_COOKIE environment variable when cookie not provided."""
        datetime_range = DatetimeRange(
            start_datetime="2025-01-15T09:00:00Z",
            end_datetime="2025-01-15T17:00:00Z",
        )

        with (
            patch.dict(os.environ, {"DISH_COOKIE": "connect.sid=env_cookie"}),
            responses.RequestsMock() as rsps,
        ):
            rsps.add(
                responses.GET,
                BOOKINGS_OCCURRENCES_ENDPOINT,
                json=[],
                status=200,
            )

            check_availability_and_list_bookings(datetime_range)

            assert len(rsps.calls) == 1
            assert rsps.calls[0].request.headers["Cookie"] == "connect.sid=env_cookie"

    def test_auto_authenticates_when_cookie_missing_but_login_creds_exist(self) -> None:
        """Populate a missing cookie automatically from stored login credentials."""
        datetime_range = DatetimeRange(
            start_datetime="2025-01-15T09:00:00Z",
            end_datetime="2025-01-15T17:00:00Z",
        )

        with (
            patch.dict(
                os.environ,
                {
                    "DISH_EMAIL": "user@example.com",
                    "DISH_PASSWORD": "password123",
                },
                clear=True,
            ),
            patch(
                "mcp_server.get_dish_credentials",
                return_value=DishCredentials(cookie="connect.sid=auto_cookie"),
            ) as mock_get_credentials,
            patch("mcp_server.save_credentials_to_env"),
            responses.RequestsMock() as rsps,
        ):
            rsps.add(
                responses.GET,
                BOOKINGS_OCCURRENCES_ENDPOINT,
                json=[],
                status=200,
            )

            check_availability_and_list_bookings(datetime_range)

            assert len(rsps.calls) == 1
            assert rsps.calls[0].request.headers["Cookie"] == "connect.sid=auto_cookie"
            assert os.environ["DISH_COOKIE"] == "connect.sid=auto_cookie"
            mock_get_credentials.assert_called_once_with(
                force_refresh=False,
                allow_interactive=False,
            )

    @responses.activate
    def test_returns_formatted_availability_on_success(self) -> None:
        """Return formatted availability summary on successful API call."""
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

        result = check_availability_and_list_bookings(
            datetime_range,
            cookie="connect.sid=test",
        )

        assert "ROOM AVAILABILITY SUMMARY" in result
        # Default rooms should be included
        assert "Boyle" in result or "Room_" in result

    @responses.activate
    def test_returns_error_on_api_failure(self) -> None:
        """Return error message on API failure."""
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

        result = check_availability_and_list_bookings(
            datetime_range,
            cookie="connect.sid=invalid",
        )

        assert "Error" in result

    def test_reauthenticates_after_unauthorised_response(self) -> None:
        """Retry once with a fresh cookie when the stored session has expired."""
        datetime_range = DatetimeRange(
            start_datetime="2025-01-15T09:00:00Z",
            end_datetime="2025-01-15T17:00:00Z",
        )

        with (
            patch.dict(
                os.environ,
                {
                    "DISH_COOKIE": "connect.sid=expired_cookie",
                    "DISH_EMAIL": "user@example.com",
                    "DISH_PASSWORD": "password123",
                },
                clear=True,
            ),
            patch(
                "mcp_server.get_dish_credentials",
                return_value=DishCredentials(cookie="connect.sid=fresh_cookie"),
            ) as mock_get_credentials,
            patch("mcp_server.save_credentials_to_env"),
            responses.RequestsMock() as rsps,
        ):
            rsps.add(
                responses.GET,
                BOOKINGS_OCCURRENCES_ENDPOINT,
                json={"error": "Unauthorised"},
                status=401,
            )
            rsps.add(
                responses.GET,
                BOOKINGS_OCCURRENCES_ENDPOINT,
                json=[],
                status=200,
            )

            result = check_availability_and_list_bookings(datetime_range)

            assert "ROOM AVAILABILITY SUMMARY" in result
            assert len(rsps.calls) == 2
            assert rsps.calls[0].request.headers["Cookie"] == "connect.sid=expired_cookie"
            assert rsps.calls[1].request.headers["Cookie"] == "connect.sid=fresh_cookie"
            mock_get_credentials.assert_called_once_with(
                force_refresh=True,
                allow_interactive=False,
            )

    @responses.activate
    def test_uses_custom_resource_ids(self) -> None:
        """Use custom resource IDs when provided."""
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
        custom_ids = ["custom_id_1", "custom_id_2"]

        check_availability_and_list_bookings(
            datetime_range,
            resource_ids=custom_ids,
            cookie="connect.sid=test",
        )

        request = responses.calls[0].request
        assert "custom_id_1" in request.url
        assert "custom_id_2" in request.url

    @responses.activate
    def test_formats_bookings_correctly(self) -> None:
        """Format bookings data into readable summary."""
        booking_data = [
            {
                "bookingId": "booking123",
                "resourceId": {
                    "_id": "6422bced61d5854ab3fedd62",
                    "name": "Boyle",
                },
                "start": {"dateTime": "2025-01-15T10:00:00Z"},
                "end": {"dateTime": "2025-01-15T11:00:00Z"},
                "summary": "Team standup",
                "member": {"name": "Alice Smith"},
            }
        ]
        responses.add(
            responses.GET,
            BOOKINGS_OCCURRENCES_ENDPOINT,
            json=booking_data,
            status=200,
        )

        datetime_range = DatetimeRange(
            start_datetime="2025-01-15T09:00:00Z",
            end_datetime="2025-01-15T17:00:00Z",
        )

        result = check_availability_and_list_bookings(
            datetime_range,
            cookie="connect.sid=test",
        )

        assert "Boyle" in result
        assert "Team standup" in result or "Alice Smith" in result


class TestBookRoomTool:
    """Tests for book_room MCP tool."""

    def test_returns_error_when_no_cookie_provided(self) -> None:
        """Return error when no cookie provided and env var not set."""
        datetime_range = DatetimeRange(
            start_datetime="2025-01-15T10:00:00.000Z",
            end_datetime="2025-01-15T11:00:00.000Z",
        )
        user_info = UserInfo(
            team_id="team123",
            member_id="member456",
        )

        with patch.dict(os.environ, {}, clear=True):
            result = book_room(
                datetime_range=datetime_range,
                meeting_room_name="Boyle",
                user_info=user_info,
            )

        assert "Error" in result
        assert "cookie" in result.lower()

    def test_uses_env_cookie_when_not_provided(self) -> None:
        """Use DISH_COOKIE environment variable when cookie not provided."""
        datetime_range = DatetimeRange(
            start_datetime="2025-01-15T10:00:00.000Z",
            end_datetime="2025-01-15T11:00:00.000Z",
        )
        user_info = UserInfo(
            team_id="team123",
            member_id="member456",
        )

        with (
            patch.dict(os.environ, {"DISH_COOKIE": "connect.sid=env_cookie"}),
            responses.RequestsMock() as rsps,
        ):
            rsps.add(
                responses.POST,
                BOOKINGS_ENDPOINT,
                json={
                    "start": {"dateTime": "2025-01-15T10:00:00.000Z"},
                    "end": {"dateTime": "2025-01-15T11:00:00.000Z"},
                    "resourceId": "6422bced61d5854ab3fedd62",
                },
                status=201,
            )

            book_room(
                datetime_range=datetime_range,
                meeting_room_name="Boyle",
                user_info=user_info,
            )

            assert len(rsps.calls) == 1
            assert rsps.calls[0].request.headers["Cookie"] == "connect.sid=env_cookie"

    @responses.activate
    def test_returns_formatted_success_message(self) -> None:
        """Return formatted success message on successful booking."""
        responses.add(
            responses.POST,
            BOOKINGS_ENDPOINT,
            json={
                "start": {"dateTime": "2025-01-15T10:00:00.000Z"},
                "end": {"dateTime": "2025-01-15T11:00:00.000Z"},
                "resourceId": "6422bced61d5854ab3fedd62",
                "reference": "REF123",
            },
            status=201,
        )

        datetime_range = DatetimeRange(
            start_datetime="2025-01-15T10:00:00.000Z",
            end_datetime="2025-01-15T11:00:00.000Z",
        )
        user_info = UserInfo(
            team_id="team123",
            member_id="member456",
        )

        result = book_room(
            datetime_range=datetime_range,
            meeting_room_name="Boyle",
            user_info=user_info,
            cookie="connect.sid=test",
        )

        assert "Booked" in result
        assert "Boyle" in result

    @responses.activate
    def test_returns_error_on_api_failure(self) -> None:
        """Return error message on API failure."""
        responses.add(
            responses.POST,
            BOOKINGS_ENDPOINT,
            json={"error": "Room not available"},
            status=409,
        )

        datetime_range = DatetimeRange(
            start_datetime="2025-01-15T10:00:00.000Z",
            end_datetime="2025-01-15T11:00:00.000Z",
        )
        user_info = UserInfo(
            team_id="team123",
            member_id="member456",
        )

        result = book_room(
            datetime_range=datetime_range,
            meeting_room_name="Boyle",
            user_info=user_info,
            cookie="connect.sid=test",
        )

        assert "Error" in result
        assert "409" in result

    def test_reauthenticates_after_booking_cookie_expires(self) -> None:
        """Retry booking once with a refreshed cookie after auth failure."""
        datetime_range = DatetimeRange(
            start_datetime="2025-01-15T10:00:00.000Z",
            end_datetime="2025-01-15T11:00:00.000Z",
        )
        user_info = UserInfo(
            team_id="team123",
            member_id="member456",
        )

        with (
            patch.dict(
                os.environ,
                {
                    "DISH_COOKIE": "connect.sid=expired_cookie",
                    "DISH_EMAIL": "user@example.com",
                    "DISH_PASSWORD": "password123",
                },
                clear=True,
            ),
            patch(
                "mcp_server.get_dish_credentials",
                return_value=DishCredentials(cookie="connect.sid=fresh_cookie"),
            ) as mock_get_credentials,
            patch("mcp_server.save_credentials_to_env"),
            responses.RequestsMock() as rsps,
        ):
            rsps.add(
                responses.POST,
                BOOKINGS_ENDPOINT,
                json={"error": "Unauthorised"},
                status=401,
            )
            rsps.add(
                responses.POST,
                BOOKINGS_ENDPOINT,
                json={
                    "start": {"dateTime": "2025-01-15T10:00:00.000Z"},
                    "end": {"dateTime": "2025-01-15T11:00:00.000Z"},
                    "resourceId": "6422bced61d5854ab3fedd62",
                },
                status=201,
            )

            result = book_room(
                datetime_range=datetime_range,
                meeting_room_name="Boyle",
                user_info=user_info,
            )

            assert "Booked Boyle" in result
            assert len(rsps.calls) == 2
            assert rsps.calls[0].request.headers["Cookie"] == "connect.sid=expired_cookie"
            assert rsps.calls[1].request.headers["Cookie"] == "connect.sid=fresh_cookie"
            mock_get_credentials.assert_called_once_with(
                force_refresh=True,
                allow_interactive=False,
            )

    def test_returns_error_on_unknown_room(self) -> None:
        """Return error for unknown room name."""
        datetime_range = DatetimeRange(
            start_datetime="2025-01-15T10:00:00.000Z",
            end_datetime="2025-01-15T11:00:00.000Z",
        )
        user_info = UserInfo(
            team_id="team123",
            member_id="member456",
        )

        result = book_room(
            datetime_range=datetime_range,
            meeting_room_name="NonExistentRoom",
            user_info=user_info,
            cookie="connect.sid=test",
        )

        assert "Error" in result
        assert "Unknown meeting room" in result

    @responses.activate
    def test_uses_custom_summary(self) -> None:
        """Use custom summary when provided."""
        responses.add(
            responses.POST,
            BOOKINGS_ENDPOINT,
            json={
                "start": {"dateTime": "2025-01-15T10:00:00.000Z"},
                "end": {"dateTime": "2025-01-15T11:00:00.000Z"},
                "resourceId": "6422bced61d5854ab3fedd62",
            },
            status=201,
        )

        datetime_range = DatetimeRange(
            start_datetime="2025-01-15T10:00:00.000Z",
            end_datetime="2025-01-15T11:00:00.000Z",
        )
        user_info = UserInfo(
            team_id="team123",
            member_id="member456",
        )

        book_room(
            datetime_range=datetime_range,
            meeting_room_name="Boyle",
            user_info=user_info,
            cookie="connect.sid=test",
            summary="Custom Meeting Title",
        )

        import json

        request = responses.calls[0].request
        payload = json.loads(request.body)
        assert payload["summary"] == "Custom Meeting Title"


class TestCancelBookingTool:
    """Tests for cancel_booking MCP tool."""

    def test_returns_error_when_no_cookie_provided(self) -> None:
        """Return error when no cookie provided and env var not set."""
        with patch.dict(os.environ, {}, clear=True):
            result = cancel_booking(booking_id="booking123")

        assert "Error" in result
        assert "cookie" in result.lower()

    def test_uses_env_cookie_when_not_provided(self) -> None:
        """Use DISH_COOKIE environment variable when cookie not provided."""
        booking_id = "test_booking"

        with (
            patch.dict(os.environ, {"DISH_COOKIE": "connect.sid=env_cookie"}),
            responses.RequestsMock() as rsps,
        ):
            rsps.add(
                responses.POST,
                get_cancel_booking_endpoint(booking_id),
                json={
                    "cancelled": True,
                    "start": {"dateTime": "2025-01-15T10:00:00.000Z"},
                    "end": {"dateTime": "2025-01-15T11:00:00.000Z"},
                    "resourceId": "6422bced61d5854ab3fedd62",
                },
                status=200,
            )

            cancel_booking(booking_id=booking_id)

            assert len(rsps.calls) == 1
            assert rsps.calls[0].request.headers["Cookie"] == "connect.sid=env_cookie"

    @responses.activate
    def test_returns_formatted_success_message(self) -> None:
        """Return formatted success message on successful cancellation."""
        booking_id = "booking_to_cancel"
        responses.add(
            responses.POST,
            get_cancel_booking_endpoint(booking_id),
            json={
                "cancelled": True,
                "start": {"dateTime": "2025-01-15T10:00:00.000Z"},
                "end": {"dateTime": "2025-01-15T11:00:00.000Z"},
                "resourceId": "6422bced61d5854ab3fedd62",
                "reference": "REF456",
            },
            status=200,
        )

        result = cancel_booking(
            booking_id=booking_id,
            cookie="connect.sid=test",
        )

        assert "Cancelled" in result
        assert "Boyle" in result

    @responses.activate
    def test_returns_error_on_api_failure(self) -> None:
        """Return error message on API failure."""
        booking_id = "invalid_booking"
        responses.add(
            responses.POST,
            get_cancel_booking_endpoint(booking_id),
            json={"error": "Booking not found"},
            status=404,
        )

        result = cancel_booking(
            booking_id=booking_id,
            cookie="connect.sid=test",
        )

        assert "Error" in result
        assert "404" in result

    @responses.activate
    def test_skip_cancellation_policy_passed(self) -> None:
        """Verify skip_cancellation_policy is passed to API."""
        booking_id = "test_booking"
        responses.add(
            responses.POST,
            get_cancel_booking_endpoint(booking_id),
            json={
                "cancelled": True,
                "start": {"dateTime": "2025-01-15T10:00:00.000Z"},
                "end": {"dateTime": "2025-01-15T11:00:00.000Z"},
                "resourceId": "6422bced61d5854ab3fedd62",
            },
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
    def test_handles_exception_gracefully(self) -> None:
        """Handle exceptions gracefully and return error message."""
        booking_id = "test_booking"

        # Simulate a connection error by not adding a response
        with patch("cancel_booking.requests.post") as mock_post:
            mock_post.side_effect = Exception("Connection refused")

            result = cancel_booking(
                booking_id=booking_id,
                cookie="connect.sid=test",
            )

        assert "Error" in result
        assert "Connection refused" in result
