"""Tests for book_room.py formatting functions."""

import pytest
from book_room import (
    _build_title,
    _clean_time,
    _normalise_booking,
    format_booking_response,
)


class TestNormaliseBooking:
    """Tests for _normalise_booking function."""

    def test_none_response(self) -> None:
        """Handle None response with fallback message."""
        result = _normalise_booking(None)

        assert "title" in result
        assert "succeeded" in result["title"].lower()

    def test_empty_list_response(self) -> None:
        """Handle empty list response with fallback message."""
        result = _normalise_booking([])

        assert "title" in result
        assert "succeeded" in result["title"].lower()

    def test_single_item_list_response(self) -> None:
        """Extract first item from single-item list response."""
        booking = {"resourceId": "room123", "reference": "REF001"}
        result = _normalise_booking([booking])

        assert result["resourceId"] == "room123"
        assert result["reference"] == "REF001"

    def test_multi_item_list_response(self) -> None:
        """Extract first item from multi-item list response."""
        bookings = [
            {"resourceId": "room1", "reference": "REF001"},
            {"resourceId": "room2", "reference": "REF002"},
        ]
        result = _normalise_booking(bookings)

        assert result["resourceId"] == "room1"
        assert result["reference"] == "REF001"

    def test_dict_response(self) -> None:
        """Return copy of dict response."""
        booking = {"resourceId": "room123", "reference": "REF001"}
        result = _normalise_booking(booking)

        assert result["resourceId"] == "room123"
        assert result["reference"] == "REF001"
        # Should be a copy, not the same object
        assert result is not booking

    def test_unexpected_type_response(self) -> None:
        """Handle unexpected response type with fallback message."""
        result = _normalise_booking("unexpected string")  # type: ignore[arg-type]

        assert "title" in result
        assert "unexpected" in result["title"].lower()


class TestCleanTime:
    """Tests for _clean_time function."""

    def test_clean_iso_with_t_separator(self) -> None:
        """Clean ISO string by replacing T with space."""
        result = _clean_time("2025-01-15T10:00:00")

        assert result == "2025-01-15 10:00:00"

    def test_clean_iso_with_subseconds(self) -> None:
        """Clean ISO string by removing subseconds."""
        result = _clean_time("2025-01-15T10:00:00.123456")

        assert result == "2025-01-15 10:00:00"

    def test_clean_iso_with_timezone(self) -> None:
        """Clean ISO string with timezone (subseconds split removes it)."""
        result = _clean_time("2025-01-15T10:00:00.000Z")

        assert result == "2025-01-15 10:00:00"

    def test_empty_string(self) -> None:
        """Handle empty string with fallback."""
        result = _clean_time("")

        assert result == "?"

    def test_none_like_empty(self) -> None:
        """Handle falsy value with fallback."""
        result = _clean_time(None)  # type: ignore[arg-type]

        assert result == "?"


class TestBuildTitle:
    """Tests for _build_title function."""

    def test_build_title_with_all_fields(self, boyle_room_id: str) -> None:
        """Build title with all fields present."""
        booking = {
            "start": {"dateTime": "2025-01-15T10:00:00.000Z"},
            "end": {"dateTime": "2025-01-15T11:00:00.000Z"},
            "resourceId": boyle_room_id,
            "reference": "REF123",
        }
        result = _build_title(booking)

        assert "Boyle" in result
        assert "2025-01-15 10:00:00" in result
        assert "2025-01-15 11:00:00" in result
        assert "REF123" in result
        assert "Booked" in result

    def test_build_title_without_reference(self, boyle_room_id: str) -> None:
        """Build title without reference field."""
        booking = {
            "start": {"dateTime": "2025-01-15T10:00:00.000Z"},
            "end": {"dateTime": "2025-01-15T11:00:00.000Z"},
            "resourceId": boyle_room_id,
        }
        result = _build_title(booking)

        assert "Boyle" in result
        assert "ref" not in result.lower()

    def test_build_title_with_unknown_room(self) -> None:
        """Build title with unknown room ID."""
        booking = {
            "start": {"dateTime": "2025-01-15T10:00:00.000Z"},
            "end": {"dateTime": "2025-01-15T11:00:00.000Z"},
            "resourceId": "unknown_room_id",
        }
        result = _build_title(booking)

        assert "Unknown room" in result

    def test_build_title_with_missing_resource_id(self) -> None:
        """Build title when resourceId is missing."""
        booking = {
            "start": {"dateTime": "2025-01-15T10:00:00.000Z"},
            "end": {"dateTime": "2025-01-15T11:00:00.000Z"},
        }
        result = _build_title(booking)

        assert "Unknown room" in result

    def test_build_title_with_missing_times(self) -> None:
        """Build title when start/end times are missing."""
        booking: dict = {
            "resourceId": "6422bced61d5854ab3fedd62",
        }
        result = _build_title(booking)

        assert "?" in result  # Fallback for missing times


class TestFormatBookingResponse:
    """Tests for format_booking_response function."""

    def test_response_already_has_title(self) -> None:
        """Return response as-is when it already has a title."""
        booking = {"title": "Existing title", "resourceId": "room123"}
        result = format_booking_response(booking)

        assert result["title"] == "Existing title"

    def test_response_needs_title_generated(self, boyle_room_id: str) -> None:
        """Generate title when response doesn't have one."""
        booking = {
            "start": {"dateTime": "2025-01-15T10:00:00.000Z"},
            "end": {"dateTime": "2025-01-15T11:00:00.000Z"},
            "resourceId": boyle_room_id,
            "reference": "REF456",
        }
        result = format_booking_response(booking)

        assert "title" in result
        assert "Booked" in result["title"]
        assert "Boyle" in result["title"]

    def test_list_response_first_item_used(self, boyle_room_id: str) -> None:
        """Use first item from list response."""
        bookings = [
            {
                "start": {"dateTime": "2025-01-15T10:00:00.000Z"},
                "end": {"dateTime": "2025-01-15T11:00:00.000Z"},
                "resourceId": boyle_room_id,
            },
        ]
        result = format_booking_response(bookings)

        assert "title" in result
        assert "Boyle" in result["title"]

    def test_none_response_returns_fallback(self) -> None:
        """Return fallback title for None response."""
        result = format_booking_response(None)

        assert "title" in result
        assert "succeeded" in result["title"].lower()

    def test_original_fields_preserved(self, boyle_room_id: str) -> None:
        """Original booking fields are preserved in result."""
        booking = {
            "start": {"dateTime": "2025-01-15T10:00:00.000Z"},
            "end": {"dateTime": "2025-01-15T11:00:00.000Z"},
            "resourceId": boyle_room_id,
            "reference": "REF789",
            "customField": "custom_value",
        }
        result = format_booking_response(booking)

        assert result["reference"] == "REF789"
        assert result["customField"] == "custom_value"
        assert "title" in result


# Fixtures used by tests in this file
@pytest.fixture
def boyle_room_id() -> str:
    """Room ID for the Boyle meeting room."""
    return "6422bced61d5854ab3fedd62"
