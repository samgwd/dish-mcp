"""Tests for room_availability/extraction.py."""

from datetime import datetime, timezone

from room_availability.extraction import (
    NO_BOOKINGS_NOTE,
    _availability_for_empty_query,
    _build_available_slots,
    _calculate_range,
    _full_range_entry,
    _group_bookings,
    _iso_to_datetime,
    _summarise_room,
    extract_room_availability,
)
from utils.type_defs import DatetimeRange


class TestIsoToDatetime:
    """Tests for _iso_to_datetime function."""

    def test_parse_iso_with_z_suffix(self) -> None:
        """Parse ISO string with 'Z' timezone suffix."""
        result = _iso_to_datetime("2025-01-15T09:00:00Z")
        expected = datetime(2025, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
        assert result == expected

    def test_parse_iso_with_utc_offset(self) -> None:
        """Parse ISO string with +00:00 timezone offset."""
        result = _iso_to_datetime("2025-01-15T09:00:00+00:00")
        expected = datetime(2025, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
        assert result == expected

    def test_parse_iso_with_positive_offset(self) -> None:
        """Parse ISO string with positive timezone offset."""
        result = _iso_to_datetime("2025-01-15T10:00:00+01:00")
        # Should preserve the timezone offset
        assert result.hour == 10
        assert result.utcoffset() is not None

    def test_parse_iso_with_negative_offset(self) -> None:
        """Parse ISO string with negative timezone offset."""
        result = _iso_to_datetime("2025-01-15T04:00:00-05:00")
        assert result.hour == 4
        assert result.utcoffset() is not None


class TestCalculateRange:
    """Tests for _calculate_range function."""

    def test_calculate_8_hour_range(self, sample_datetime_range: DatetimeRange) -> None:
        """Calculate range for an 8-hour period (9am-5pm)."""
        range_start, range_end, total_minutes = _calculate_range(
            sample_datetime_range["start_datetime"],
            sample_datetime_range["end_datetime"],
        )

        assert range_start == datetime(2025, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
        assert range_end == datetime(2025, 1, 15, 17, 0, 0, tzinfo=timezone.utc)
        assert total_minutes == 480  # 8 hours = 480 minutes

    def test_calculate_1_hour_range(self, sample_datetime_range_short: DatetimeRange) -> None:
        """Calculate range for a 1-hour period."""
        range_start, range_end, total_minutes = _calculate_range(
            sample_datetime_range_short["start_datetime"],
            sample_datetime_range_short["end_datetime"],
        )

        assert total_minutes == 60

    def test_calculate_multiday_range(self) -> None:
        """Calculate range spanning multiple days."""
        range_start, range_end, total_minutes = _calculate_range(
            "2025-01-15T09:00:00Z",
            "2025-01-16T17:00:00Z",
        )

        # 32 hours = 1920 minutes
        assert total_minutes == 1920

    def test_calculate_zero_minute_range(self) -> None:
        """Calculate range with same start and end time."""
        range_start, range_end, total_minutes = _calculate_range(
            "2025-01-15T09:00:00Z",
            "2025-01-15T09:00:00Z",
        )

        assert range_start == range_end
        assert total_minutes == 0


class TestFullRangeEntry:
    """Tests for _full_range_entry function."""

    def test_create_entry_basic(self, range_start: datetime, range_end: datetime) -> None:
        """Create a basic full range entry without optional fields."""
        entry = _full_range_entry(range_start, range_end, 480)

        assert entry["total_available_minutes"] == 480
        assert entry["total_booked_minutes"] == 0
        assert len(entry["available_slots"]) == 1
        assert entry["available_slots"][0]["duration_minutes"] == 480
        assert entry["booked_slots"] == []
        assert "note" not in entry
        assert "room_id" not in entry

    def test_create_entry_with_note(self, range_start: datetime, range_end: datetime) -> None:
        """Create entry with a note."""
        entry = _full_range_entry(range_start, range_end, 480, note="Test note")

        assert entry["note"] == "Test note"

    def test_create_entry_with_room_id(
        self, range_start: datetime, range_end: datetime, boyle_room_id: str
    ) -> None:
        """Create entry with a room ID."""
        entry = _full_range_entry(range_start, range_end, 480, room_id=boyle_room_id)

        assert entry["room_id"] == boyle_room_id

    def test_create_entry_with_all_optional_fields(
        self, range_start: datetime, range_end: datetime, boyle_room_id: str
    ) -> None:
        """Create entry with both note and room_id."""
        entry = _full_range_entry(
            range_start, range_end, 480, room_id=boyle_room_id, note="Complete entry"
        )

        assert entry["note"] == "Complete entry"
        assert entry["room_id"] == boyle_room_id
        assert entry["total_available_minutes"] == 480

    def test_available_slot_timestamps_are_iso(
        self, range_start: datetime, range_end: datetime
    ) -> None:
        """Verify available slot times are ISO formatted strings."""
        entry = _full_range_entry(range_start, range_end, 480)

        slot = entry["available_slots"][0]
        assert isinstance(slot["start"], str)
        assert isinstance(slot["end"], str)
        # Should be parseable as ISO
        datetime.fromisoformat(slot["start"])
        datetime.fromisoformat(slot["end"])


class TestAvailabilityForEmptyQuery:
    """Tests for _availability_for_empty_query function."""

    def test_returns_empty_when_no_room_ids(
        self, range_start: datetime, range_end: datetime
    ) -> None:
        """Return empty dict when no queried_room_ids provided."""
        result = _availability_for_empty_query(None, range_start, range_end, 480)

        assert result == {}

    def test_returns_empty_when_empty_room_ids_list(
        self, range_start: datetime, range_end: datetime
    ) -> None:
        """Return empty dict when queried_room_ids is empty list."""
        result = _availability_for_empty_query([], range_start, range_end, 480)

        assert result == {}

    def test_single_room_fully_available(
        self, range_start: datetime, range_end: datetime, boyle_room_id: str
    ) -> None:
        """Single room marked as fully available."""
        result = _availability_for_empty_query([boyle_room_id], range_start, range_end, 480)

        assert len(result) == 1
        room_key = f"Room_{boyle_room_id}"
        assert room_key in result
        assert result[room_key]["total_available_minutes"] == 480
        assert result[room_key]["total_booked_minutes"] == 0
        assert result[room_key]["note"] == NO_BOOKINGS_NOTE

    def test_multiple_rooms_fully_available(
        self, range_start: datetime, range_end: datetime, all_room_ids: list[str]
    ) -> None:
        """Multiple rooms all marked as fully available."""
        result = _availability_for_empty_query(all_room_ids, range_start, range_end, 480)

        assert len(result) == 3
        for room_id in all_room_ids:
            room_key = f"Room_{room_id}"
            assert room_key in result
            assert result[room_key]["note"] == NO_BOOKINGS_NOTE


class TestGroupBookings:
    """Tests for _group_bookings function."""

    def test_single_booking(self, sample_booking_boyle: dict) -> None:
        """Group a single booking."""
        room_bookings, room_id_to_name, rooms_in_response = _group_bookings([sample_booking_boyle])

        assert "Boyle" in room_bookings
        assert len(room_bookings["Boyle"]) == 1
        assert room_bookings["Boyle"][0]["booking_id"] == "booking123"
        assert sample_booking_boyle["resourceId"]["_id"] in rooms_in_response

    def test_multiple_bookings_same_room(
        self, sample_booking_boyle: dict, sample_booking_boyle_afternoon: dict
    ) -> None:
        """Group multiple bookings for the same room."""
        bookings = [sample_booking_boyle, sample_booking_boyle_afternoon]
        room_bookings, room_id_to_name, rooms_in_response = _group_bookings(bookings)

        assert len(room_bookings["Boyle"]) == 2

    def test_bookings_different_rooms(
        self, sample_booking_boyle: dict, sample_booking_pankhurst: dict
    ) -> None:
        """Group bookings for different rooms."""
        bookings = [sample_booking_boyle, sample_booking_pankhurst]
        room_bookings, room_id_to_name, rooms_in_response = _group_bookings(bookings)

        assert "Boyle" in room_bookings
        assert "Pankhurst" in room_bookings
        assert len(room_bookings["Boyle"]) == 1
        assert len(room_bookings["Pankhurst"]) == 1
        assert len(rooms_in_response) == 2

    def test_room_id_to_name_populated(
        self, sample_booking_boyle: dict, boyle_room_id: str
    ) -> None:
        """Verify room_id_to_name mapping is populated from bookings."""
        room_bookings, room_id_to_name, rooms_in_response = _group_bookings([sample_booking_boyle])

        assert room_id_to_name[boyle_room_id] == "Boyle"

    def test_booking_times_converted_to_datetime(self, sample_booking_boyle: dict) -> None:
        """Verify booking times are converted to datetime objects."""
        room_bookings, _, _ = _group_bookings([sample_booking_boyle])

        booking = room_bookings["Boyle"][0]
        assert isinstance(booking["start"], datetime)
        assert isinstance(booking["end"], datetime)


class TestBuildAvailableSlots:
    """Tests for _build_available_slots function."""

    def test_no_bookings_entire_range_available(
        self, range_start: datetime, range_end: datetime
    ) -> None:
        """No bookings means entire range is available."""
        slots = _build_available_slots([], range_start, range_end)

        assert len(slots) == 1
        assert slots[0]["duration_minutes"] == 480  # 8 hours

    def test_single_booking_in_middle(self, range_start: datetime, range_end: datetime) -> None:
        """Single booking in middle creates two available slots."""
        booking = {
            "start": datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
            "end": datetime(2025, 1, 15, 13, 0, 0, tzinfo=timezone.utc),
        }
        slots = _build_available_slots([booking], range_start, range_end)

        assert len(slots) == 2
        # Before booking: 9am-12pm = 180 minutes
        assert slots[0]["duration_minutes"] == 180
        # After booking: 1pm-5pm = 240 minutes
        assert slots[1]["duration_minutes"] == 240

    def test_booking_at_start_of_range(self, range_start: datetime, range_end: datetime) -> None:
        """Booking at start creates only one available slot after."""
        booking = {
            "start": datetime(2025, 1, 15, 9, 0, 0, tzinfo=timezone.utc),
            "end": datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        }
        slots = _build_available_slots([booking], range_start, range_end)

        assert len(slots) == 1
        # After booking: 10am-5pm = 420 minutes
        assert slots[0]["duration_minutes"] == 420

    def test_booking_at_end_of_range(self, range_start: datetime, range_end: datetime) -> None:
        """Booking at end creates only one available slot before."""
        booking = {
            "start": datetime(2025, 1, 15, 16, 0, 0, tzinfo=timezone.utc),
            "end": datetime(2025, 1, 15, 17, 0, 0, tzinfo=timezone.utc),
        }
        slots = _build_available_slots([booking], range_start, range_end)

        assert len(slots) == 1
        # Before booking: 9am-4pm = 420 minutes
        assert slots[0]["duration_minutes"] == 420

    def test_back_to_back_bookings_no_gap(self, range_start: datetime, range_end: datetime) -> None:
        """Back-to-back bookings leave no gap between them."""
        bookings = [
            {
                "start": datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 1, 15, 11, 0, 0, tzinfo=timezone.utc),
            },
            {
                "start": datetime(2025, 1, 15, 11, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
            },
        ]
        slots = _build_available_slots(bookings, range_start, range_end)

        assert len(slots) == 2
        # Before bookings: 9am-10am = 60 minutes
        assert slots[0]["duration_minutes"] == 60
        # After bookings: 12pm-5pm = 300 minutes
        assert slots[1]["duration_minutes"] == 300

    def test_full_day_booking_no_availability(
        self, range_start: datetime, range_end: datetime
    ) -> None:
        """Booking spanning entire range leaves no available slots."""
        booking = {
            "start": datetime(2025, 1, 15, 9, 0, 0, tzinfo=timezone.utc),
            "end": datetime(2025, 1, 15, 17, 0, 0, tzinfo=timezone.utc),
        }
        slots = _build_available_slots([booking], range_start, range_end)

        assert len(slots) == 0

    def test_multiple_bookings_with_gaps(self, range_start: datetime, range_end: datetime) -> None:
        """Multiple bookings with gaps creates multiple available slots."""
        bookings = [
            {
                "start": datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 1, 15, 11, 0, 0, tzinfo=timezone.utc),
            },
            {
                "start": datetime(2025, 1, 15, 14, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 1, 15, 15, 0, 0, tzinfo=timezone.utc),
            },
        ]
        slots = _build_available_slots(bookings, range_start, range_end)

        assert len(slots) == 3
        # 9am-10am = 60 min
        assert slots[0]["duration_minutes"] == 60
        # 11am-2pm = 180 min
        assert slots[1]["duration_minutes"] == 180
        # 3pm-5pm = 120 min
        assert slots[2]["duration_minutes"] == 120

    def test_slot_timestamps_are_iso_strings(
        self, range_start: datetime, range_end: datetime
    ) -> None:
        """Verify slot timestamps are ISO formatted strings."""
        slots = _build_available_slots([], range_start, range_end)

        assert isinstance(slots[0]["start"], str)
        assert isinstance(slots[0]["end"], str)


class TestSummariseRoom:
    """Tests for _summarise_room function."""

    def test_single_booking(
        self,
        range_start: datetime,
        range_end: datetime,
        sample_booking_boyle: dict,
        boyle_room_id: str,
    ) -> None:
        """Summarise a room with a single booking."""
        bookings_list = [
            {
                "start": datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 1, 15, 11, 0, 0, tzinfo=timezone.utc),
                "booking": sample_booking_boyle,
                "room_id": boyle_room_id,
                "booking_id": "booking123",
            }
        ]
        summary = _summarise_room(bookings_list, range_start, range_end)

        assert summary["total_booked_minutes"] == 60
        assert summary["total_available_minutes"] == 420  # 480 - 60
        assert len(summary["booked_slots"]) == 1
        assert len(summary["available_slots"]) == 2

    def test_booked_slots_include_metadata(
        self,
        range_start: datetime,
        range_end: datetime,
        sample_booking_boyle: dict,
        boyle_room_id: str,
    ) -> None:
        """Verify booked slots include member name, summary, and booking ID."""
        bookings_list = [
            {
                "start": datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 1, 15, 11, 0, 0, tzinfo=timezone.utc),
                "booking": sample_booking_boyle,
                "room_id": boyle_room_id,
                "booking_id": "booking123",
            }
        ]
        summary = _summarise_room(bookings_list, range_start, range_end)

        booked_slot = summary["booked_slots"][0]
        assert booked_slot["member"] == "Alice Smith"
        assert booked_slot["summary"] == "Team standup"
        assert booked_slot["bookingId"] == "booking123"

    def test_bookings_sorted_by_start_time(
        self,
        range_start: datetime,
        range_end: datetime,
        boyle_room_id: str,
    ) -> None:
        """Verify booked slots are sorted by start time."""
        # Create bookings in reverse order
        booking_late = {
            "summary": "Late meeting",
            "member": {"name": "Late Person"},
        }
        booking_early = {
            "summary": "Early meeting",
            "member": {"name": "Early Person"},
        }
        bookings_list = [
            {
                "start": datetime(2025, 1, 15, 14, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 1, 15, 15, 0, 0, tzinfo=timezone.utc),
                "booking": booking_late,
                "room_id": boyle_room_id,
                "booking_id": "late",
            },
            {
                "start": datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 1, 15, 11, 0, 0, tzinfo=timezone.utc),
                "booking": booking_early,
                "room_id": boyle_room_id,
                "booking_id": "early",
            },
        ]
        summary = _summarise_room(bookings_list, range_start, range_end)

        # Should be sorted: early meeting first
        assert summary["booked_slots"][0]["bookingId"] == "early"
        assert summary["booked_slots"][1]["bookingId"] == "late"

    def test_booking_without_member(
        self,
        range_start: datetime,
        range_end: datetime,
        sample_booking_no_member: dict,
        boyle_room_id: str,
    ) -> None:
        """Handle booking without member field gracefully."""
        bookings_list = [
            {
                "start": datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 1, 15, 11, 0, 0, tzinfo=timezone.utc),
                "booking": sample_booking_no_member,
                "room_id": boyle_room_id,
                "booking_id": "booking_no_member",
            }
        ]
        summary = _summarise_room(bookings_list, range_start, range_end)

        booked_slot = summary["booked_slots"][0]
        assert booked_slot["member"] is None


class TestExtractRoomAvailability:
    """Integration tests for extract_room_availability function."""

    def test_empty_bookings_with_room_ids(
        self, sample_datetime_range: DatetimeRange, all_room_ids: list[str]
    ) -> None:
        """Empty bookings with queried room IDs marks all rooms as available."""
        result = extract_room_availability([], sample_datetime_range, queried_room_ids=all_room_ids)

        assert len(result) == 3
        for room_id in all_room_ids:
            room_key = f"Room_{room_id}"
            assert room_key in result
            assert result[room_key]["total_available_minutes"] == 480
            assert result[room_key]["note"] == NO_BOOKINGS_NOTE

    def test_empty_bookings_without_room_ids(self, sample_datetime_range: DatetimeRange) -> None:
        """Empty bookings without queried room IDs returns empty result."""
        result = extract_room_availability([], sample_datetime_range)

        assert result == {}

    def test_single_room_single_booking(
        self,
        sample_datetime_range: DatetimeRange,
        sample_booking_boyle: dict,
        boyle_room_id: str,
    ) -> None:
        """Process single booking for single room."""
        result = extract_room_availability(
            [sample_booking_boyle],
            sample_datetime_range,
            queried_room_ids=[boyle_room_id],
        )

        assert "Boyle" in result
        assert result["Boyle"]["total_booked_minutes"] == 60
        assert result["Boyle"]["total_available_minutes"] == 420

    def test_multiple_rooms_with_bookings(
        self,
        sample_datetime_range: DatetimeRange,
        sample_booking_boyle: dict,
        sample_booking_pankhurst: dict,
        boyle_room_id: str,
        pankhurst_room_id: str,
    ) -> None:
        """Process bookings across multiple rooms."""
        bookings = [sample_booking_boyle, sample_booking_pankhurst]
        result = extract_room_availability(
            bookings,
            sample_datetime_range,
            queried_room_ids=[boyle_room_id, pankhurst_room_id],
        )

        assert "Boyle" in result
        assert "Pankhurst" in result
        assert result["Boyle"]["total_booked_minutes"] == 60
        assert result["Pankhurst"]["total_booked_minutes"] == 60

    def test_queried_room_not_in_response(
        self,
        sample_datetime_range: DatetimeRange,
        sample_booking_boyle: dict,
        boyle_room_id: str,
        turing_room_id: str,
    ) -> None:
        """Room in queried_room_ids but not in bookings is marked as fully available."""
        result = extract_room_availability(
            [sample_booking_boyle],
            sample_datetime_range,
            queried_room_ids=[boyle_room_id, turing_room_id],
        )

        assert "Boyle" in result
        # Turing should be marked as fully available (using name from constants)
        assert "Turing" in result
        assert result["Turing"]["total_available_minutes"] == 480
        assert result["Turing"]["note"] == NO_BOOKINGS_NOTE

    def test_multiple_bookings_same_room(
        self,
        sample_datetime_range: DatetimeRange,
        sample_booking_boyle: dict,
        sample_booking_boyle_afternoon: dict,
        boyle_room_id: str,
    ) -> None:
        """Process multiple bookings for the same room."""
        bookings = [sample_booking_boyle, sample_booking_boyle_afternoon]
        result = extract_room_availability(
            bookings,
            sample_datetime_range,
            queried_room_ids=[boyle_room_id],
        )

        assert result["Boyle"]["total_booked_minutes"] == 120  # 2 x 60 minutes
        # Available: 9-10am (60) + 11am-2pm (180) + 3pm-5pm (120) = 360
        assert result["Boyle"]["total_available_minutes"] == 360
        assert len(result["Boyle"]["booked_slots"]) == 2

    def test_back_to_back_bookings(
        self,
        sample_datetime_range: DatetimeRange,
        back_to_back_bookings: list[dict],
        boyle_room_id: str,
    ) -> None:
        """Back-to-back bookings create no gap between them."""
        result = extract_room_availability(
            back_to_back_bookings,
            sample_datetime_range,
            queried_room_ids=[boyle_room_id],
        )

        # Two 1-hour bookings = 120 minutes booked
        assert result["Boyle"]["total_booked_minutes"] == 120
        # Available: 9-10am (60) + 12pm-5pm (300) = 360
        assert result["Boyle"]["total_available_minutes"] == 360
        # Should have 2 available slots (before and after the back-to-back block)
        assert len(result["Boyle"]["available_slots"]) == 2

    def test_full_day_booking(
        self,
        sample_datetime_range: DatetimeRange,
        sample_booking_full_day: dict,
        boyle_room_id: str,
    ) -> None:
        """Full day booking leaves no availability."""
        result = extract_room_availability(
            [sample_booking_full_day],
            sample_datetime_range,
            queried_room_ids=[boyle_room_id],
        )

        assert result["Boyle"]["total_booked_minutes"] == 480
        assert result["Boyle"]["total_available_minutes"] == 0
        assert len(result["Boyle"]["available_slots"]) == 0

    def test_available_minutes_plus_booked_equals_total(
        self,
        sample_datetime_range: DatetimeRange,
        sample_booking_boyle: dict,
        sample_booking_boyle_afternoon: dict,
        boyle_room_id: str,
    ) -> None:
        """Verify available + booked minutes equals total range."""
        bookings = [sample_booking_boyle, sample_booking_boyle_afternoon]
        result = extract_room_availability(
            bookings,
            sample_datetime_range,
            queried_room_ids=[boyle_room_id],
        )

        total = result["Boyle"]["total_available_minutes"] + result["Boyle"]["total_booked_minutes"]
        assert total == 480  # 8 hours


class TestEdgeCases:
    """Edge case tests for extraction module."""

    def test_unknown_room_id_uses_fallback_name(self, sample_datetime_range: DatetimeRange) -> None:
        """Unknown room ID in queried_room_ids uses Room_<id> as name."""
        unknown_id = "unknown_room_123"
        result = extract_room_availability(
            [],
            sample_datetime_range,
            queried_room_ids=[unknown_id],
        )

        expected_key = f"Room_{unknown_id}"
        assert expected_key in result

    def test_booking_with_timezone_offset(self, boyle_room_id: str) -> None:
        """Handle bookings with non-UTC timezone offsets."""
        booking = {
            "bookingId": "tz_booking",
            "resourceId": {
                "_id": boyle_room_id,
                "name": "Boyle",
            },
            "start": {"dateTime": "2025-01-15T10:00:00+01:00"},
            "end": {"dateTime": "2025-01-15T11:00:00+01:00"},
            "summary": "TZ test",
        }
        datetime_range: DatetimeRange = {
            "start_datetime": "2025-01-15T09:00:00+01:00",
            "end_datetime": "2025-01-15T17:00:00+01:00",
        }

        result = extract_room_availability(
            [booking],
            datetime_range,
            queried_room_ids=[boyle_room_id],
        )

        assert "Boyle" in result
        assert result["Boyle"]["total_booked_minutes"] == 60

    def test_very_short_datetime_range(self, boyle_room_id: str) -> None:
        """Handle very short datetime ranges (1 minute)."""
        datetime_range: DatetimeRange = {
            "start_datetime": "2025-01-15T10:00:00Z",
            "end_datetime": "2025-01-15T10:01:00Z",
        }

        result = extract_room_availability(
            [],
            datetime_range,
            queried_room_ids=[boyle_room_id],
        )

        room_key = f"Room_{boyle_room_id}"
        assert result[room_key]["total_available_minutes"] == 1
