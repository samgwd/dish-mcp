"""Tests for mcp_server.py formatting helpers."""

from typing import Any

from mcp_server import (
    DEFAULT_RESOURCE_IDS,
    _format_availability_summary,
    _format_available_slot,
    _format_booked_slot,
    _format_room_section,
    _format_time,
    _resolve_resource_ids,
)


class TestResolveResourceIds:
    """Tests for _resolve_resource_ids function."""

    def test_return_provided_ids(self) -> None:
        """Return provided IDs when given."""
        custom_ids = ["id1", "id2", "id3"]
        result = _resolve_resource_ids(custom_ids)

        assert result == custom_ids

    def test_return_default_ids_when_none(self) -> None:
        """Return default IDs when None is provided."""
        result = _resolve_resource_ids(None)

        assert result == DEFAULT_RESOURCE_IDS

    def test_return_default_ids_when_empty_list(self) -> None:
        """Return default IDs when empty list is provided (falsy)."""
        result = _resolve_resource_ids([])

        assert result == DEFAULT_RESOURCE_IDS

    def test_default_ids_contains_known_rooms(self) -> None:
        """Verify default IDs contain the known room IDs."""
        assert "6422bced61d5854ab3fedd62" in DEFAULT_RESOURCE_IDS  # Boyle
        assert "6422bcd50340a914e68e661b" in DEFAULT_RESOURCE_IDS  # Pankhurst
        assert "6422bcff9814c9c32ed62d77" in DEFAULT_RESOURCE_IDS  # Turing


class TestFormatTime:
    """Tests for _format_time function."""

    def test_format_iso_timestamp(self) -> None:
        """Format ISO timestamp correctly."""
        result = _format_time("2025-01-15T10:30:00+00:00")

        assert result == "2025-01-15 10:30"

    def test_remove_timezone_suffix(self) -> None:
        """Remove +00:00 timezone suffix."""
        result = _format_time("2025-01-15T14:00:00+00:00")

        assert "+00:00" not in result
        assert result == "2025-01-15 14:00"

    def test_truncate_to_16_chars(self) -> None:
        """Truncate to 16 characters (date + space + HH:MM)."""
        result = _format_time("2025-01-15T10:30:45.123456+00:00")

        assert len(result) == 16
        assert result == "2025-01-15 10:30"

    def test_replace_t_separator(self) -> None:
        """Replace T with space."""
        result = _format_time("2025-01-15T09:00:00")

        assert "T" not in result
        assert " " in result


class TestFormatAvailableSlot:
    """Tests for _format_available_slot function."""

    def test_format_with_duration(self) -> None:
        """Format available slot with duration."""
        slot = {
            "start": "2025-01-15T09:00:00+00:00",
            "end": "2025-01-15T10:00:00+00:00",
            "duration_minutes": 60,
        }
        result = _format_available_slot(slot)

        assert "2025-01-15 09:00" in result
        assert "2025-01-15 10:00" in result
        assert "60 min" in result

    def test_format_multi_hour_slot(self) -> None:
        """Format slot spanning multiple hours."""
        slot = {
            "start": "2025-01-15T09:00:00+00:00",
            "end": "2025-01-15T17:00:00+00:00",
            "duration_minutes": 480,
        }
        result = _format_available_slot(slot)

        assert "480 min" in result

    def test_format_includes_indentation(self) -> None:
        """Verify slot format includes indentation."""
        slot = {
            "start": "2025-01-15T09:00:00+00:00",
            "end": "2025-01-15T10:00:00+00:00",
            "duration_minutes": 60,
        }
        result = _format_available_slot(slot)

        assert result.startswith("    ")  # 4 spaces indentation


class TestFormatBookedSlot:
    """Tests for _format_booked_slot function."""

    def test_format_with_all_fields(self) -> None:
        """Format booked slot with all fields present."""
        slot = {
            "start": "2025-01-15T10:00:00+00:00",
            "end": "2025-01-15T11:00:00+00:00",
            "summary": "Team standup",
            "member": "Alice Smith",
            "bookingId": "booking123",
        }
        result = _format_booked_slot(slot)

        assert "2025-01-15 10:00" in result
        assert "2025-01-15 11:00" in result
        assert "Alice Smith" in result
        assert "Team standup" in result
        assert "booking123" in result

    def test_format_without_member(self) -> None:
        """Format slot without member field."""
        slot = {
            "start": "2025-01-15T10:00:00+00:00",
            "end": "2025-01-15T11:00:00+00:00",
            "summary": "Anonymous meeting",
        }
        result = _format_booked_slot(slot)

        assert "Anonymous meeting" in result
        # Should not have empty parentheses
        assert "()" not in result

    def test_format_without_summary(self) -> None:
        """Format slot without summary field."""
        slot = {
            "start": "2025-01-15T10:00:00+00:00",
            "end": "2025-01-15T11:00:00+00:00",
            "member": "Bob Jones",
        }
        result = _format_booked_slot(slot)

        assert "Bob Jones" in result
        # Should not have extra dash
        assert " - " not in result or "Bob Jones" in result

    def test_format_without_booking_id(self) -> None:
        """Format slot without bookingId field."""
        slot = {
            "start": "2025-01-15T10:00:00+00:00",
            "end": "2025-01-15T11:00:00+00:00",
            "summary": "Meeting",
        }
        result = _format_booked_slot(slot)

        assert "booking ID" not in result

    def test_format_includes_indentation(self) -> None:
        """Verify slot format includes indentation."""
        slot = {
            "start": "2025-01-15T10:00:00+00:00",
            "end": "2025-01-15T11:00:00+00:00",
        }
        result = _format_booked_slot(slot)

        assert result.startswith("    ")


class TestFormatRoomSection:
    """Tests for _format_room_section function."""

    def test_section_with_note(self) -> None:
        """Format room section with note."""
        room_data: dict[str, Any] = {
            "note": "No bookings found",
            "total_available_minutes": 480,
            "total_booked_minutes": 0,
            "available_slots": [],
            "booked_slots": [],
        }
        result = _format_room_section("Boyle", room_data)

        assert any("Boyle:" in line for line in result)
        assert any("No bookings found" in line for line in result)

    def test_section_without_note(self) -> None:
        """Format room section without note."""
        room_data: dict[str, Any] = {
            "total_available_minutes": 420,
            "total_booked_minutes": 60,
            "available_slots": [],
            "booked_slots": [],
        }
        result = _format_room_section("Boyle", room_data)

        assert any("Boyle:" in line for line in result)
        assert not any("Note:" in line for line in result)

    def test_section_with_available_slots(self) -> None:
        """Format room section with available slots."""
        room_data: dict[str, Any] = {
            "total_available_minutes": 60,
            "total_booked_minutes": 420,
            "available_slots": [
                {
                    "start": "2025-01-15T09:00:00+00:00",
                    "end": "2025-01-15T10:00:00+00:00",
                    "duration_minutes": 60,
                }
            ],
            "booked_slots": [],
        }
        result = _format_room_section("Boyle", room_data)

        assert any("Available Time Slots:" in line for line in result)
        assert any("60 min" in line for line in result)

    def test_section_with_booked_slots(self) -> None:
        """Format room section with booked slots."""
        room_data: dict[str, Any] = {
            "total_available_minutes": 420,
            "total_booked_minutes": 60,
            "available_slots": [],
            "booked_slots": [
                {
                    "start": "2025-01-15T10:00:00+00:00",
                    "end": "2025-01-15T11:00:00+00:00",
                    "summary": "Meeting",
                    "member": "Alice",
                    "bookingId": "123",
                }
            ],
        }
        result = _format_room_section("Boyle", room_data)

        assert any("Booked Time Slots:" in line for line in result)
        assert any("Meeting" in line for line in result)

    def test_section_includes_totals(self) -> None:
        """Format room section includes total minutes."""
        room_data: dict[str, Any] = {
            "total_available_minutes": 360,
            "total_booked_minutes": 120,
            "available_slots": [],
            "booked_slots": [],
        }
        result = _format_room_section("Pankhurst", room_data)

        assert any("360 minutes" in line for line in result)
        assert any("120 minutes" in line for line in result)


class TestFormatAvailabilitySummary:
    """Tests for _format_availability_summary function."""

    def test_empty_availability(self) -> None:
        """Format empty availability dict."""
        result = _format_availability_summary({})

        assert "ROOM AVAILABILITY SUMMARY" in result
        assert "=" in result

    def test_single_room(self) -> None:
        """Format availability for single room."""
        availability: dict[str, dict[str, Any]] = {
            "Boyle": {
                "total_available_minutes": 480,
                "total_booked_minutes": 0,
                "available_slots": [
                    {
                        "start": "2025-01-15T09:00:00+00:00",
                        "end": "2025-01-15T17:00:00+00:00",
                        "duration_minutes": 480,
                    }
                ],
                "booked_slots": [],
            }
        }
        result = _format_availability_summary(availability)

        assert "ROOM AVAILABILITY SUMMARY" in result
        assert "Boyle:" in result
        assert "480 minutes" in result

    def test_multiple_rooms(self) -> None:
        """Format availability for multiple rooms."""
        availability: dict[str, dict[str, Any]] = {
            "Boyle": {
                "total_available_minutes": 420,
                "total_booked_minutes": 60,
                "available_slots": [],
                "booked_slots": [],
            },
            "Pankhurst": {
                "total_available_minutes": 480,
                "total_booked_minutes": 0,
                "available_slots": [],
                "booked_slots": [],
            },
        }
        result = _format_availability_summary(availability)

        assert "Boyle:" in result
        assert "Pankhurst:" in result

    def test_includes_header(self) -> None:
        """Verify summary includes header."""
        result = _format_availability_summary({})

        lines = result.split("\n")
        assert lines[0] == "ROOM AVAILABILITY SUMMARY"
        assert "=" * 30 in lines[1]
