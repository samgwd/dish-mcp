"""Utilities to extract and summarise room availability information."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from utils.constants import ROOM_ID_TO_NAME
from utils.type_defs import DatetimeRange

NO_BOOKINGS_NOTE = "No bookings found - room completely available"


def _iso_to_datetime(value: str) -> datetime:
    """Convert an ISO string to a timezone-aware datetime object.

    Args:
        value: The ISO string to convert.

    Returns:
        datetime: The timezone-aware datetime object (assumes UTC if no timezone).
    """
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    # If no timezone info, assume UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _calculate_range(start_date: str, end_date: str) -> tuple[datetime, datetime, int]:
    """Calculate the range and total minutes between two dates.

    Args:
        start_date: The start date.
        end_date: The end date.

    Returns:
        tuple[datetime, datetime, int]: The range and total minutes.
    """
    range_start = _iso_to_datetime(start_date)
    range_end = _iso_to_datetime(end_date)
    total_range_minutes = int((range_end - range_start).total_seconds() / 60)
    return range_start, range_end, total_range_minutes


def _full_range_entry(
    range_start: datetime,
    range_end: datetime,
    total_range_minutes: int,
    *,
    room_id: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    """Create a room availability entry representing complete availability for a time range.

    Args:
        range_start: The start of the range.
        range_end: The end of the range.
        total_range_minutes: The total range in minutes.
        room_id: The ID of the room.
        note: The note to add to the entry.

    Returns:
        dict[str, Any]: The room availability entry.
    """
    entry: dict[str, Any] = {
        "available_slots": [
            {
                "start": range_start.isoformat(),
                "end": range_end.isoformat(),
                "duration_minutes": total_range_minutes,
            }
        ],
        "booked_slots": [],
        "total_available_minutes": total_range_minutes,
        "total_booked_minutes": 0,
    }
    if note:
        entry["note"] = note
    if room_id:
        entry["room_id"] = room_id
    return entry


def _availability_for_empty_query(
    queried_room_ids: list[str] | None,
    range_start: datetime,
    range_end: datetime,
    total_range_minutes: int,
) -> dict[str, dict[str, Any]]:
    """Create availability entries for rooms when the API returns no bookings.

    Args:
        queried_room_ids: The IDs of the rooms to query.
        range_start: The start of the range.
        range_end: The end of the range.
        total_range_minutes: The total range in minutes.

    Returns:
        dict[str, dict[str, Any]]: The availability entries.
    """
    if not queried_room_ids:
        print("Warning: Empty bookings response and no queried_room_ids provided.")
        print("Cannot determine which rooms are available.")
        return {}

    availability: dict[str, dict[str, Any]] = {}
    for room_id in queried_room_ids:
        room_key = f"Room_{room_id}"
        availability[room_key] = _full_range_entry(
            range_start,
            range_end,
            total_range_minutes,
            room_id=room_id,
            note=NO_BOOKINGS_NOTE,
        )
    return availability


def _group_bookings(
    bookings: list[dict[str, Any]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, str], set[str]]:
    """Organise raw booking data by room and extract room metadata.

    Args:
        bookings: The bookings to group.

    Returns:
        tuple[dict[str, list[dict[str, Any]]], dict[str, str], set[str]]: The grouped bookings.
    """
    room_bookings: dict[str, list[dict[str, Any]]] = defaultdict(list)
    room_id_to_name = ROOM_ID_TO_NAME.copy()
    rooms_in_response: set[str] = set()

    for booking in bookings:
        room_name = str(booking["resourceId"]["name"])
        room_id = str(booking["resourceId"]["_id"])
        rooms_in_response.add(room_id)
        room_id_to_name[room_id] = room_name
        booking_id = str(booking["bookingId"])

        start_time = _iso_to_datetime(str(booking["start"]["dateTime"]))
        end_time = _iso_to_datetime(str(booking["end"]["dateTime"]))

        room_bookings[room_name].append(
            {
                "start": start_time,
                "end": end_time,
                "booking": booking,
                "room_id": room_id,
                "booking_id": booking_id,
            }
        )

    return room_bookings, room_id_to_name, rooms_in_response


def _build_available_slots(
    sorted_bookings: list[dict[str, Any]],
    range_start: datetime,
    range_end: datetime,
) -> list[dict[str, Any]]:
    """Calculate available time slots by finding gaps between bookings.

    Args:
        sorted_bookings: The sorted bookings.
        range_start: The start of the range.
        range_end: The end of the range.

    Returns:
        list[dict[str, Any]]: The available slots.
    """
    available_slots = []
    current_time = range_start

    for booking in sorted_bookings:
        booking_start: datetime = booking["start"]
        booking_end: datetime = booking["end"]
        if current_time < booking_start:
            available_slots.append(
                {
                    "start": current_time.isoformat(),
                    "end": booking_start.isoformat(),
                    "duration_minutes": int((booking_start - current_time).total_seconds() / 60),
                }
            )
        current_time = max(current_time, booking_end)

    if current_time < range_end:
        available_slots.append(
            {
                "start": current_time.isoformat(),
                "end": range_end.isoformat(),
                "duration_minutes": int((range_end - current_time).total_seconds() / 60),
            }
        )

    return available_slots


def _summarise_room(
    bookings_list: list[dict[str, Any]],
    range_start: datetime,
    range_end: datetime,
) -> dict[str, Any]:
    """Generate a comprehensive availability summary for a single room.

    Args:
        bookings_list: The bookings to summarise.
        range_start: The start of the range.
        range_end: The end of the range.

    Returns:
        dict[str, Any]: The availability summary.
    """
    sorted_bookings = sorted(bookings_list, key=lambda x: x["start"])
    available_slots = _build_available_slots(sorted_bookings, range_start, range_end)
    return {
        "available_slots": available_slots,
        "booked_slots": [
            {
                "start": booking["start"].isoformat(),
                "end": booking["end"].isoformat(),
                "summary": str(booking["booking"].get("summary", "")),
                "member": (
                    str(booking["booking"].get("member", {}).get("name", ""))
                    if booking["booking"].get("member")
                    else None
                ),
                "bookingId": booking["booking_id"],
            }
            for booking in sorted_bookings
        ],
        "total_available_minutes": sum(slot["duration_minutes"] for slot in available_slots),
        "total_booked_minutes": sum(
            int((booking["end"] - booking["start"]).total_seconds() / 60)
            for booking in sorted_bookings
        ),
    }


def _add_missing_rooms(
    availability: dict[str, dict[str, Any]],
    queried_room_ids: list[str] | None,
    rooms_in_response: set[str],
    room_id_to_name: dict[str, str],
    range_details: tuple[datetime, datetime, int],
) -> None:
    """Add availability entries for queried rooms that had no bookings in the API response.

    Args:
        availability: The availability to add to.
        queried_room_ids: The IDs of the rooms to query.
        rooms_in_response: The rooms in the response.
        room_id_to_name: The ID to name mapping.
        range_details: The range details.
    """
    if not queried_room_ids:
        return

    range_start, range_end, total_range_minutes = range_details

    for room_id in queried_room_ids:
        if room_id in rooms_in_response:
            continue
        room_name = room_id_to_name.get(room_id, f"Room_{room_id}")
        availability[room_name] = _full_range_entry(
            range_start,
            range_end,
            total_range_minutes,
            room_id=room_id,
            note=NO_BOOKINGS_NOTE,
        )


def extract_room_availability(
    bookings: list[dict[str, Any]],
    datetime_range: DatetimeRange,
    queried_room_ids: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Extract availability for each room from bookings data.

    Args:
        bookings: The bookings to extract availability from.
        datetime_range: The datetime range to extract availability for.
        queried_room_ids: The IDs of the rooms to query.

    Returns:
        dict[str, dict[str, Any]]: The availability.
    """
    range_details = _calculate_range(datetime_range.start_datetime, datetime_range.end_datetime)
    range_start, range_end, total_range_minutes = range_details

    if not bookings:
        return _availability_for_empty_query(
            queried_room_ids,
            range_start,
            range_end,
            total_range_minutes,
        )

    room_bookings, room_id_to_name, rooms_in_response = _group_bookings(bookings)

    availability = {
        room_name: _summarise_room(bookings_list, range_start, range_end)
        for room_name, bookings_list in room_bookings.items()
    }

    _add_missing_rooms(
        availability,
        queried_room_ids,
        rooms_in_response,
        room_id_to_name,
        range_details,
    )

    return availability


__all__ = ["extract_room_availability"]
