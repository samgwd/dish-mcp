"""MCP server for booking rooms via DiSH."""

import os
from typing import Any

from fastmcp import Context, FastMCP

from .book_room import book_room as book_room_api
from .book_room import format_booking_response
from .cancel_booking import (
    cancel_booking as cancel_booking_api,
)
from .cancel_booking import (
    format_cancellation_response,
)
from .get_room_availability import extract_room_availability, get_room_availability
from .utils.type_defs import DatetimeRange, UserInfo

DEFAULT_RESOURCE_IDS = [
    "6422bced61d5854ab3fedd62",  # Boyle
    "6422bcd50340a914e68e661b",  # Pankhurst
    "6422bcff9814c9c32ed62d77",  # Turing
]

mcp = FastMCP("Dish MCP")


def _resolve_resource_ids(resource_ids: list[str] | None) -> list[str]:
    """Return provided resource ids or the default collection.

    Args:
        resource_ids: Optional list of room resource IDs to query.

    Returns:
        list[str]: The resource IDs to query.
    """
    return resource_ids or DEFAULT_RESOURCE_IDS


def _format_time(timestamp: str) -> str:
    """Normalise ISO timestamp for display.

    Args:
        timestamp: The ISO timestamp to normalise.

    Returns:
        str: The normalised timestamp.
    """
    return timestamp.replace("+00:00", "").replace("T", " ")[:16]


def _format_available_slot(slot: dict[str, Any]) -> str:
    """Create a friendly summary for an available slot.

    Args:
        slot: The available slot to format.

    Returns:
        str: The formatted available slot.
    """
    start = _format_time(slot["start"])
    end = _format_time(slot["end"])
    return f"    {start} - {end} ({slot['duration_minutes']} min)"


def _format_booked_slot(slot: dict[str, Any]) -> str:
    """Create a friendly summary for a booked slot.

    Args:
        slot: The booked slot to format.

    Returns:
        str: The formatted booked slot.
    """
    start = _format_time(slot["start"])
    end = _format_time(slot["end"])
    summary = f" - {slot['summary']}" if slot.get("summary") else ""
    member = f" ({slot['member']})" if slot.get("member") else ""
    booking_id = f" (booking ID: {slot['bookingId']})" if slot.get("bookingId") else ""
    return f"    {start} - {end}{member}{summary}{booking_id}"


def _format_room_section(room_name: str, room_data: dict[str, Any]) -> list[str]:
    """Build the report lines for a single room.

    Args:
        room_name: The name of the room.
        room_data: The data for the room.

    Returns:
        list[str]: The report lines for the room.
    """
    lines = [f"\n{room_name}:"]

    note = room_data.get("note")
    if note:
        lines.append(f"  Note: {note}")

    lines.append(f"  Total Available: {room_data['total_available_minutes']} minutes")
    lines.append(f"  Total Booked: {room_data['total_booked_minutes']} minutes")

    available_slots = room_data.get("available_slots") or []
    if available_slots:
        lines.append("  Available Time Slots:")
        lines.extend(_format_available_slot(slot) for slot in available_slots)

    booked_slots = room_data.get("booked_slots") or []
    if booked_slots:
        lines.append("  Booked Time Slots:")
        lines.extend(_format_booked_slot(slot) for slot in booked_slots)

    return lines


def _format_availability_summary(availability: dict[str, Any]) -> str:
    """Generate human readable availability summary.

    Args:
        availability: The availability to format.

    Returns:
        str: The formatted availability summary.
    """
    output: list[str] = ["ROOM AVAILABILITY SUMMARY", "=" * 30]

    for room_name, room_data in availability.items():
        output.extend(_format_room_section(room_name, room_data))

    return "\n".join(output)


@mcp.tool
def check_availability_and_list_bookings(
    datetime_range: DatetimeRange,
    resource_ids: list[str] | None = None,
    cookie: str | None = None,
    ctx: Context | None = None,
) -> str:
    """Check room availability for the DiSH API and list bookings for a room and date range.

    Args:
        datetime_range: Datetime range for the query
        resource_ids: Optional list of room resource IDs to query.
        cookie: Authentication cookie. If not provided, looks for DISH_COOKIE env var.
        ctx: Context object.

    Returns:
        str: The availability summary.
    """
    if not cookie:
        cookie = os.environ.get("DISH_COOKIE")

    if not cookie:
        return (
            "Error: No authentication cookie provided. Please provide a cookie or set DISH_COOKIE"
            " environment variable."
        )

    resource_ids = _resolve_resource_ids(resource_ids)

    try:
        response = get_room_availability(
            resource_ids=resource_ids,
            datetime_range=datetime_range,
            cookie=cookie,
        )

        if response.status_code != 200:  # noqa: PLR2004
            return f"Error: API returned status {response.status_code}"

        bookings_data = response.json()
        availability = extract_room_availability(
            bookings_data, datetime_range, queried_room_ids=resource_ids
        )

        return _format_availability_summary(availability)

    except Exception as e:
        return f"Error checking availability: {str(e)}"


@mcp.tool
def book_room(
    datetime_range: DatetimeRange,
    meeting_room_name: str,
    user_info: UserInfo,
    cookie: str | None = None,
    summary: str = "Fuzzy Labs Meeting",
) -> str:
    """Book a room using the Dish Manchester API.

    Args:
        datetime_range: Datetime range for the booking
        meeting_room_name: Name of the meeting room
        user_info: User information
        cookie: Authentication cookie. If not provided, looks for DISH_COOKIE env var.
        summary: Title of the booking: default to "meeting"
    """
    if not cookie:
        cookie = os.environ.get("DISH_COOKIE")

    if not cookie:
        return (
            "Error: No authentication cookie provided. Please provide a cookie or set DISH_COOKIE"
            " environment variable."
        )

    try:
        response = book_room_api(
            datetime_range={
                "start_datetime": datetime_range["start_datetime"],
                "end_datetime": datetime_range["end_datetime"],
            },
            meeting_room_name=meeting_room_name,
            user_info={
                "team_id": user_info["team_id"],
                "member_id": user_info["member_id"],
            },
            cookie=cookie,
            summary=summary,
        )

        if response.status_code not in [200, 201]:
            return f"Error: API returned status {response.status_code}. Body: {response.text}"

        response_data = response.json()
        formatted_response = format_booking_response(response_data)

        return str(formatted_response["title"])

    except Exception as e:
        return f"Error booking room: {str(e)}"


@mcp.tool
def cancel_booking(
    booking_id: str,
    cookie: str | None = None,
    skip_cancellation_policy: bool = False,
) -> str:
    """Cancel a room booking using the DiSH API.

    To cancel a booking, you need to know the booking ID. You can get the booking ID by using the
    `check_availability` tool to get the bookings for a room and date range.

    Args:
        booking_id: The ID of the booking to cancel (e.g., "692192791c60f69c20311db3")
        cookie: Authentication cookie. If not provided, looks for DISH_COOKIE env var.
        skip_cancellation_policy: Whether to skip cancellation policy (default: False)
    """
    if not cookie:
        cookie = os.environ.get("DISH_COOKIE")

    if not cookie:
        return (
            "Error: No authentication cookie provided. Please provide a cookie or set DISH_COOKIE"
            " environment variable."
        )

    try:
        response = cancel_booking_api(
            booking_id=booking_id,
            cookie=cookie,
            skip_cancellation_policy=skip_cancellation_policy,
        )

        if response.status_code not in [200, 201]:
            return f"Error: API returned status {response.status_code}. Body: {response.text}"

        response_data = response.json()
        formatted_response = format_cancellation_response(response_data)

        return str(formatted_response["title"])

    except Exception as e:
        return f"Error cancelling booking: {str(e)}"
