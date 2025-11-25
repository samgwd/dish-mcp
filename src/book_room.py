"""Function to book a room."""

from typing import Any

import requests
from utils.constants import BOOKINGS_ENDPOINT, ROOM_ID_TO_NAME, ROOM_NAME_TO_ID
from utils.type_defs import DatetimeRange, UserInfo


def book_room(
    datetime_range: DatetimeRange,
    meeting_room_name: str,
    user_info: UserInfo,
    cookie: str,
    summary: str,
) -> requests.Response:
    """Book a room using the DiSH API.

    Args:
        datetime_range: Dict with 'start_datetime' and 'end_datetime' in ISO format
            (e.g., "2025-11-19T19:00:00.000Z")
        meeting_room_name: Name of the meeting room
        user_info: Dict with 'team_id' and 'member_id'
        cookie: Authentication cookie
        summary: Title of the booking

    Returns:
        requests.Response: The HTTP response object
    """
    start_datetime = datetime_range["start_datetime"]
    end_datetime = datetime_range["end_datetime"]
    team_id = user_info["team_id"]
    member_id = user_info["member_id"]

    # Get the resource ID for the meeting room
    resource_id = ROOM_NAME_TO_ID.get(meeting_room_name)
    if not resource_id:
        raise ValueError(f"Unknown meeting room: {meeting_room_name}")

    payload = {
        "start": {"dateTime": start_datetime},
        "end": {"dateTime": end_datetime},
        "dateTime": end_datetime,
        "resourceId": resource_id,
        "team": team_id,
        "member": member_id,
        "summary": summary,
        "source": "portal",
        "timezone": "Europe/London",
        "recurrence": {"rrule": None},
        "recurrenceEditMode": "single",
        "visitors": [],
        "members": [],
        "extras": {},
        "properties": {},
    }

    headers = {"Content-Type": "application/json", "Cookie": cookie}

    response = requests.post(BOOKINGS_ENDPOINT, json=payload, headers=headers, timeout=30)

    return response


def _normalise_booking(
    response_data: dict[str, Any] | list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Return a dict booking payload or the appropriate fallback.

    Args:
        response_data: The JSON response from the booking API (dict, list, or None).

    Returns:
        dict: The booking object or a dict with a 'title' field for fallback cases.
    """
    if not response_data:
        return {"title": "Booking succeeded but no details were returned."}

    if isinstance(response_data, list):
        if not response_data:
            return {"title": "Booking succeeded but no details were returned."}
        return response_data[0].copy()

    if isinstance(response_data, dict):
        return response_data.copy()

    return {"title": "Booking succeeded but response format was unexpected."}


def _clean_time(iso_str: str) -> str:
    """Clean a time string from an ISO format.

    Args:
        iso_str: The ISO time string to clean.

    Returns:
        str: The cleaned time string.
    """
    if not iso_str:
        return "?"
    # Keep only the date and time, discard subseconds/timezone as we already
    # expose the timezone elsewhere in the payload.
    return iso_str.replace("T", " ").split(".")[0]


def _build_title(booking: dict[str, Any]) -> str:
    """Build a title for a booking.

    Args:
        booking: The booking object.

    Returns:
        str: The title for the booking.
    """
    start_time = booking.get("start", {}).get("dateTime")
    end_time = booking.get("end", {}).get("dateTime")
    resource_id = booking.get("resourceId") or ""
    room_name = ROOM_ID_TO_NAME.get(resource_id, "Unknown room")
    reference = booking.get("reference")

    start_str = _clean_time(start_time)
    end_str = _clean_time(end_time)
    title = f"Booked {room_name} from {start_str} to {end_str}"

    if reference:
        title = f"{title} (ref {reference})"

    return title


def format_booking_response(
    response_data: dict[str, Any] | list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Format the booking response to include a succinct, human readable summary.

    Args:
        response_data: The JSON response from the booking API (dict or list).

    Returns:
        dict: The booking object with an added 'title' field.
    """
    booking = _normalise_booking(response_data)

    if "title" in booking:
        return booking

    booking["title"] = _build_title(booking)
    return booking
