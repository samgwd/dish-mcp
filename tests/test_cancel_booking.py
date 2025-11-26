"""Tests for cancel_booking.py formatting functions."""

import pytest
from cancel_booking import (
    _build_title,
    _clean_time,
    _normalise_booking,
    format_cancellation_response,
)


class TestNormaliseBooking:
    """Tests for _normalise_booking function (cancellation version)."""

    def test_none_response(self) -> None:
        """Handle None response with fallback message."""
        result = _normalise_booking(None)  # type: ignore[arg-type]

        assert "title" in result
        assert "succeeded" in result["title"].lower()

    def test_non_dict_response(self) -> None:
        """Handle non-dict response with fallback message."""
        result = _normalise_booking("unexpected string")  # type: ignore[arg-type]

        assert "title" in result
        assert "unexpected" in result["title"].lower()

    def test_valid_dict_response(self) -> None:
        """Return copy of valid dict response."""
        booking = {"resourceId": "room123", "cancelled": True}
        result = _normalise_booking(booking)

        assert result["resourceId"] == "room123"
        assert result["cancelled"] is True
        # Should be a copy, not the same object
        assert result is not booking

    def test_empty_dict_response(self) -> None:
        """Handle empty dict (falsy but valid type)."""
        result = _normalise_booking({})

        assert "title" in result
        assert "succeeded" in result["title"].lower()


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
        """Clean ISO string with timezone."""
        result = _clean_time("2025-01-15T10:00:00.000Z")

        assert result == "2025-01-15 10:00:00"

    def test_empty_string(self) -> None:
        """Handle empty string with fallback."""
        result = _clean_time("")

        assert result == "?"


class TestBuildTitle:
    """Tests for _build_title function (cancellation version)."""

    def test_build_title_cancelled_true(self, boyle_room_id: str) -> None:
        """Build title for successfully cancelled booking."""
        booking = {
            "start": {"dateTime": "2025-01-15T10:00:00.000Z"},
            "end": {"dateTime": "2025-01-15T11:00:00.000Z"},
            "resourceId": boyle_room_id,
            "cancelled": True,
            "reference": "REF123",
        }
        result = _build_title(booking)

        assert "Cancelled" in result
        assert "Attempted" not in result
        assert "Boyle" in result
        assert "REF123" in result

    def test_build_title_cancelled_false(self, boyle_room_id: str) -> None:
        """Build title for non-cancelled booking (attempted cancellation)."""
        booking = {
            "start": {"dateTime": "2025-01-15T10:00:00.000Z"},
            "end": {"dateTime": "2025-01-15T11:00:00.000Z"},
            "resourceId": boyle_room_id,
            "cancelled": False,
            "reference": "REF123",
        }
        result = _build_title(booking)

        assert "Attempted to cancel" in result
        assert "Boyle" in result

    def test_build_title_cancelled_missing(self, boyle_room_id: str) -> None:
        """Build title when cancelled field is missing (defaults to False)."""
        booking = {
            "start": {"dateTime": "2025-01-15T10:00:00.000Z"},
            "end": {"dateTime": "2025-01-15T11:00:00.000Z"},
            "resourceId": boyle_room_id,
        }
        result = _build_title(booking)

        assert "Attempted to cancel" in result

    def test_build_title_without_reference(self, boyle_room_id: str) -> None:
        """Build title without reference field."""
        booking = {
            "start": {"dateTime": "2025-01-15T10:00:00.000Z"},
            "end": {"dateTime": "2025-01-15T11:00:00.000Z"},
            "resourceId": boyle_room_id,
            "cancelled": True,
        }
        result = _build_title(booking)

        assert "ref" not in result.lower()

    def test_build_title_with_unknown_room(self) -> None:
        """Build title with unknown room ID."""
        booking = {
            "start": {"dateTime": "2025-01-15T10:00:00.000Z"},
            "end": {"dateTime": "2025-01-15T11:00:00.000Z"},
            "resourceId": "unknown_room_id",
            "cancelled": True,
        }
        result = _build_title(booking)

        assert "Unknown room" in result

    def test_build_title_with_missing_times(self) -> None:
        """Build title when start/end times are missing."""
        booking: dict = {
            "resourceId": "6422bced61d5854ab3fedd62",
            "cancelled": True,
        }
        result = _build_title(booking)

        assert "?" in result  # Fallback for missing times


class TestFormatCancellationResponse:
    """Tests for format_cancellation_response function."""

    def test_response_already_has_title(self) -> None:
        """Return response as-is when it already has a title."""
        booking = {"title": "Existing title", "cancelled": True}
        result = format_cancellation_response(booking)

        assert result["title"] == "Existing title"

    def test_response_needs_title_generated(self, boyle_room_id: str) -> None:
        """Generate title when response doesn't have one."""
        booking = {
            "start": {"dateTime": "2025-01-15T10:00:00.000Z"},
            "end": {"dateTime": "2025-01-15T11:00:00.000Z"},
            "resourceId": boyle_room_id,
            "cancelled": True,
            "reference": "REF456",
        }
        result = format_cancellation_response(booking)

        assert "title" in result
        assert "Cancelled" in result["title"]
        assert "Boyle" in result["title"]

    def test_original_fields_preserved(self, boyle_room_id: str) -> None:
        """Original booking fields are preserved in result."""
        booking = {
            "start": {"dateTime": "2025-01-15T10:00:00.000Z"},
            "end": {"dateTime": "2025-01-15T11:00:00.000Z"},
            "resourceId": boyle_room_id,
            "cancelled": True,
            "reference": "REF789",
            "customField": "custom_value",
        }
        result = format_cancellation_response(booking)

        assert result["reference"] == "REF789"
        assert result["customField"] == "custom_value"
        assert result["cancelled"] is True


# Fixtures used by tests in this file
@pytest.fixture
def boyle_room_id() -> str:
    """Room ID for the Boyle meeting room."""
    return "6422bced61d5854ab3fedd62"
