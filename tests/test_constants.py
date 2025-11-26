"""Tests for utils/constants.py."""

from utils.constants import (
    BASE_URL,
    BOOKINGS_ENDPOINT,
    BOOKINGS_OCCURRENCES_ENDPOINT,
    ROOM_ID_TO_NAME,
    ROOM_NAME_TO_ID,
    get_cancel_booking_endpoint,
)


class TestRoomMappings:
    """Tests for room ID/name mappings."""

    def test_room_name_to_id_contains_known_rooms(self) -> None:
        """Verify all known rooms are in ROOM_NAME_TO_ID."""
        assert "Boyle" in ROOM_NAME_TO_ID
        assert "Pankhurst" in ROOM_NAME_TO_ID
        assert "Turing" in ROOM_NAME_TO_ID

    def test_room_id_to_name_contains_known_rooms(self) -> None:
        """Verify all known room IDs are in ROOM_ID_TO_NAME."""
        assert "6422bced61d5854ab3fedd62" in ROOM_ID_TO_NAME
        assert "6422bcd50340a914e68e661b" in ROOM_ID_TO_NAME
        assert "6422bcff9814c9c32ed62d77" in ROOM_ID_TO_NAME

    def test_mappings_are_inverses(self) -> None:
        """Verify ROOM_NAME_TO_ID and ROOM_ID_TO_NAME are perfect inverses."""
        # Check every name maps to an ID that maps back to the same name
        for name, room_id in ROOM_NAME_TO_ID.items():
            assert ROOM_ID_TO_NAME[room_id] == name

        # Check every ID maps to a name that maps back to the same ID
        for room_id, name in ROOM_ID_TO_NAME.items():
            assert ROOM_NAME_TO_ID[name] == room_id

    def test_same_number_of_entries(self) -> None:
        """Verify both mappings have the same number of entries."""
        assert len(ROOM_NAME_TO_ID) == len(ROOM_ID_TO_NAME)

    def test_boyle_room_id(self) -> None:
        """Verify Boyle room has correct ID."""
        assert ROOM_NAME_TO_ID["Boyle"] == "6422bced61d5854ab3fedd62"

    def test_pankhurst_room_id(self) -> None:
        """Verify Pankhurst room has correct ID."""
        assert ROOM_NAME_TO_ID["Pankhurst"] == "6422bcd50340a914e68e661b"

    def test_turing_room_id(self) -> None:
        """Verify Turing room has correct ID."""
        assert ROOM_NAME_TO_ID["Turing"] == "6422bcff9814c9c32ed62d77"


class TestEndpoints:
    """Tests for API endpoint constants."""

    def test_base_url_is_dish_manchester(self) -> None:
        """Verify base URL points to Dish Manchester."""
        assert "dish-manchester" in BASE_URL
        assert "officernd.com" in BASE_URL

    def test_bookings_endpoint_uses_base_url(self) -> None:
        """Verify bookings endpoint uses base URL."""
        assert BOOKINGS_ENDPOINT.startswith(BASE_URL)
        assert "/user/bookings" in BOOKINGS_ENDPOINT

    def test_bookings_occurrences_endpoint_uses_base_url(self) -> None:
        """Verify bookings occurrences endpoint uses base URL."""
        assert BOOKINGS_OCCURRENCES_ENDPOINT.startswith(BASE_URL)
        assert "/user/bookings/occurrences" in BOOKINGS_OCCURRENCES_ENDPOINT


class TestGetCancelBookingEndpoint:
    """Tests for get_cancel_booking_endpoint function."""

    def test_returns_correct_url(self) -> None:
        """Return correct URL with booking ID."""
        booking_id = "abc123"
        result = get_cancel_booking_endpoint(booking_id)

        assert result == f"{BOOKINGS_ENDPOINT}/{booking_id}/cancel"

    def test_includes_booking_id(self) -> None:
        """Verify booking ID is included in URL."""
        booking_id = "692192791c60f69c20311db3"
        result = get_cancel_booking_endpoint(booking_id)

        assert booking_id in result
        assert "/cancel" in result

    def test_different_booking_ids(self) -> None:
        """Test with different booking IDs."""
        id1 = "id_one"
        id2 = "id_two"

        result1 = get_cancel_booking_endpoint(id1)
        result2 = get_cancel_booking_endpoint(id2)

        assert result1 != result2
        assert id1 in result1
        assert id2 in result2

    def test_url_format(self) -> None:
        """Verify URL follows expected format."""
        booking_id = "test123"
        result = get_cancel_booking_endpoint(booking_id)

        # Should end with /booking_id/cancel
        assert result.endswith(f"/{booking_id}/cancel")
        # Should contain bookings path
        assert "/user/bookings/" in result
