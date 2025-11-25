"""Pretty-print helpers for room availability."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import requests
from room_availability.extraction import extract_room_availability
from utils.type_defs import DatetimeRange


def _print_summary_header() -> None:
    """Print the static header shown above every availability summary."""
    print("=" * 80)
    print("ROOM AVAILABILITY SUMMARY")
    print("=" * 80)


def _handle_empty_availability(
    availability: dict[str, dict[str, Any]],
    queried_room_ids: list[str] | None,
) -> bool:
    """Report that no rooms were returned and note queried IDs if present."""
    if availability:
        return False

    print("\nNo rooms found in response.")
    if queried_room_ids:
        print(f"\nNote: {len(queried_room_ids)} room(s) were queried but none appear in bookings.")
        print("This likely means all rooms are completely free for the time range.")
        print(f"\nQueried room IDs: {', '.join(queried_room_ids)}")
    return True


def _print_room_summary(
    room_name: str,
    room_data: dict[str, Any],
    max_bookings_to_show: int,
) -> None:
    """Print aggregate metrics plus booked/available slots for a single room."""
    print(f"\n{room_name}:")
    if "note" in room_data:
        print(f"  Note: {room_data['note']}")

    print(f"  Total Available: {room_data['total_available_minutes']} minutes")
    print(f"  Total Booked: {room_data['total_booked_minutes']} minutes")
    print(f"  Available Slots: {len(room_data['available_slots'])}")
    print(f"  Booked Slots: {len(room_data['booked_slots'])}")

    _print_available_slots(room_data["available_slots"])
    _print_booked_slots(room_data["booked_slots"], max_bookings_to_show)


def _print_available_slots(slots: list[dict[str, Any]]) -> None:
    """Print the human-friendly details for all available slots."""
    if not slots:
        return

    print("\n  Available Time Slots:")
    for slot in slots:
        start_fmt, end_fmt = _format_slot_times(slot)
        duration = slot["duration_minutes"]
        print(f"    {start_fmt} - {end_fmt} ({duration} min)")


def _print_booked_slots(slots: list[dict[str, Any]], max_bookings_to_show: int) -> None:
    """Print booked slots, truncating the list when there are many entries."""
    if not slots:
        return

    print("\n  Booked Time Slots:")
    for slot in slots[:max_bookings_to_show]:
        start_fmt, end_fmt = _format_slot_times(slot)
        member_info = f" ({slot['member']})" if slot["member"] else ""
        summary_info = f" - {slot['summary']}" if slot["summary"] else ""
        booking_id_info = f" (booking ID: {slot['bookingId']})" if slot["bookingId"] else ""
        booking_line = f"    {start_fmt} - {end_fmt}{member_info}{summary_info}{booking_id_info}"
        print(booking_line)

    if len(slots) > max_bookings_to_show:
        extra_bookings = len(slots) - max_bookings_to_show
        print(f"    ... and {extra_bookings} more bookings")


def _format_slot_times(slot: dict[str, Any]) -> tuple[str, str]:
    """Convert slot start/end ISO strings into user-friendly display strings."""
    start = datetime.fromisoformat(slot["start"].replace("+00:00", ""))
    end = datetime.fromisoformat(slot["end"].replace("+00:00", ""))
    return start.strftime("%Y-%m-%d %H:%M"), end.strftime("%H:%M")


def display_room_availability(
    response: requests.Response,
    datetime_range: DatetimeRange,
    queried_room_ids: list[str] | None = None,
    max_bookings_to_show: int = 5,
) -> dict[str, Any] | None:
    """Extract and display room availability from an API response."""
    if response.status_code != 200:  # noqa: PLR2004
        print("Error: Could not fetch bookings data")
        return None

    bookings_data = response.json()

    availability: dict[str, dict[str, Any]] = extract_room_availability(
        bookings_data,
        datetime_range,
        queried_room_ids=queried_room_ids,
    )

    _print_summary_header()

    if _handle_empty_availability(availability, queried_room_ids):
        return availability

    for room_name, room_data in availability.items():
        _print_room_summary(room_name, room_data, max_bookings_to_show)

    return availability


__all__ = ["display_room_availability"]
