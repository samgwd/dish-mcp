"""Shared pytest fixtures for dish-mcp tests."""

from datetime import datetime, timezone

import pytest
from utils.type_defs import DatetimeRange


@pytest.fixture
def sample_datetime_range() -> DatetimeRange:
    """A standard datetime range for testing (9am-5pm on a single day)."""
    return {
        "start_datetime": "2025-01-15T09:00:00Z",
        "end_datetime": "2025-01-15T17:00:00Z",
    }


@pytest.fixture
def sample_datetime_range_short() -> DatetimeRange:
    """A short datetime range for testing (1 hour)."""
    return {
        "start_datetime": "2025-01-15T10:00:00Z",
        "end_datetime": "2025-01-15T11:00:00Z",
    }


@pytest.fixture
def range_start() -> datetime:
    """Start of the sample datetime range as a datetime object."""
    return datetime(2025, 1, 15, 9, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def range_end() -> datetime:
    """End of the sample datetime range as a datetime object."""
    return datetime(2025, 1, 15, 17, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def boyle_room_id() -> str:
    """Room ID for the Boyle meeting room."""
    return "6422bced61d5854ab3fedd62"


@pytest.fixture
def pankhurst_room_id() -> str:
    """Room ID for the Pankhurst meeting room."""
    return "6422bcd50340a914e68e661b"


@pytest.fixture
def turing_room_id() -> str:
    """Room ID for the Turing meeting room."""
    return "6422bcff9814c9c32ed62d77"


@pytest.fixture
def all_room_ids(boyle_room_id: str, pankhurst_room_id: str, turing_room_id: str) -> list[str]:
    """List of all room IDs."""
    return [boyle_room_id, pankhurst_room_id, turing_room_id]


@pytest.fixture
def sample_booking_boyle(boyle_room_id: str) -> dict:
    """A sample booking for the Boyle room (10am-11am)."""
    return {
        "bookingId": "booking123",
        "resourceId": {
            "_id": boyle_room_id,
            "name": "Boyle",
        },
        "start": {"dateTime": "2025-01-15T10:00:00Z"},
        "end": {"dateTime": "2025-01-15T11:00:00Z"},
        "summary": "Team standup",
        "member": {"name": "Alice Smith"},
    }


@pytest.fixture
def sample_booking_boyle_afternoon(boyle_room_id: str) -> dict:
    """A sample booking for the Boyle room in afternoon (2pm-3pm)."""
    return {
        "bookingId": "booking456",
        "resourceId": {
            "_id": boyle_room_id,
            "name": "Boyle",
        },
        "start": {"dateTime": "2025-01-15T14:00:00Z"},
        "end": {"dateTime": "2025-01-15T15:00:00Z"},
        "summary": "Project review",
        "member": {"name": "Bob Jones"},
    }


@pytest.fixture
def sample_booking_pankhurst(pankhurst_room_id: str) -> dict:
    """A sample booking for the Pankhurst room (11am-12pm)."""
    return {
        "bookingId": "booking789",
        "resourceId": {
            "_id": pankhurst_room_id,
            "name": "Pankhurst",
        },
        "start": {"dateTime": "2025-01-15T11:00:00Z"},
        "end": {"dateTime": "2025-01-15T12:00:00Z"},
        "summary": "Client call",
        "member": {"name": "Charlie Brown"},
    }


@pytest.fixture
def sample_booking_no_member(boyle_room_id: str) -> dict:
    """A sample booking without a member field."""
    return {
        "bookingId": "booking_no_member",
        "resourceId": {
            "_id": boyle_room_id,
            "name": "Boyle",
        },
        "start": {"dateTime": "2025-01-15T10:00:00Z"},
        "end": {"dateTime": "2025-01-15T11:00:00Z"},
        "summary": "Anonymous booking",
    }


@pytest.fixture
def sample_booking_at_range_start(boyle_room_id: str) -> dict:
    """A booking that starts at the beginning of the range (9am-10am)."""
    return {
        "bookingId": "booking_start",
        "resourceId": {
            "_id": boyle_room_id,
            "name": "Boyle",
        },
        "start": {"dateTime": "2025-01-15T09:00:00Z"},
        "end": {"dateTime": "2025-01-15T10:00:00Z"},
        "summary": "Early meeting",
        "member": {"name": "Early Bird"},
    }


@pytest.fixture
def sample_booking_at_range_end(boyle_room_id: str) -> dict:
    """A booking that ends at the end of the range (4pm-5pm)."""
    return {
        "bookingId": "booking_end",
        "resourceId": {
            "_id": boyle_room_id,
            "name": "Boyle",
        },
        "start": {"dateTime": "2025-01-15T16:00:00Z"},
        "end": {"dateTime": "2025-01-15T17:00:00Z"},
        "summary": "Late meeting",
        "member": {"name": "Night Owl"},
    }


@pytest.fixture
def sample_booking_full_day(boyle_room_id: str) -> dict:
    """A booking that spans the entire range (9am-5pm)."""
    return {
        "bookingId": "booking_full",
        "resourceId": {
            "_id": boyle_room_id,
            "name": "Boyle",
        },
        "start": {"dateTime": "2025-01-15T09:00:00Z"},
        "end": {"dateTime": "2025-01-15T17:00:00Z"},
        "summary": "All day workshop",
        "member": {"name": "Workshop Leader"},
    }


@pytest.fixture
def back_to_back_bookings(boyle_room_id: str) -> list[dict]:
    """Two back-to-back bookings with no gap (10am-11am, 11am-12pm)."""
    return [
        {
            "bookingId": "booking_b2b_1",
            "resourceId": {
                "_id": boyle_room_id,
                "name": "Boyle",
            },
            "start": {"dateTime": "2025-01-15T10:00:00Z"},
            "end": {"dateTime": "2025-01-15T11:00:00Z"},
            "summary": "Meeting 1",
            "member": {"name": "Person A"},
        },
        {
            "bookingId": "booking_b2b_2",
            "resourceId": {
                "_id": boyle_room_id,
                "name": "Boyle",
            },
            "start": {"dateTime": "2025-01-15T11:00:00Z"},
            "end": {"dateTime": "2025-01-15T12:00:00Z"},
            "summary": "Meeting 2",
            "member": {"name": "Person B"},
        },
    ]
