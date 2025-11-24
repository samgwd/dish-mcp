"""Function to cancel a room booking."""

from typing import Any

import requests

from .utils.constants import ROOM_ID_TO_NAME, get_cancel_booking_endpoint


def cancel_booking(
    booking_id: str,
    cookie: str,
    skip_cancellation_policy: bool = False,
) -> requests.Response:
    """Cancel a room booking using the Dish Manchester API.

    Args:
        booking_id: The ID of the booking to cancel (e.g., "692192791c60f69c20311db3")
        cookie: Authentication cookie
        skip_cancellation_policy: Whether to skip cancellation policy (default: False)

    Returns:
        requests.Response: The HTTP response object
    """
    url = get_cancel_booking_endpoint(booking_id)

    params = {
        "skipCancellationPolicy": str(skip_cancellation_policy).lower(),
    }

    headers = {"Content-Type": "application/json", "Cookie": cookie}

    response = requests.post(url, params=params, headers=headers, timeout=30)

    return response


def _normalise_booking(response_data: dict[str, Any]) -> dict[str, Any]:
    """Return a dict booking payload or the appropriate fallback.

    Args:
        response_data: The JSON response from the cancellation API (dict).

    Returns:
        dict: The booking object with an added 'title' field.
    """
    if not response_data:
        return {"title": "Cancellation succeeded but no details were returned."}

    if not isinstance(response_data, dict):
        return {"title": "Cancellation succeeded but response format was unexpected."}

    return response_data.copy()


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
    """Build a title for a cancellation.

    Args:
        booking: The booking object.

    Returns:
        str: The title for the cancellation.
    """
    start_time = booking.get("start", {}).get("dateTime")
    end_time = booking.get("end", {}).get("dateTime")
    resource_id = booking.get("resourceId") or ""
    room_name = ROOM_ID_TO_NAME.get(resource_id, "Unknown room")
    cancelled = booking.get("cancelled", False)
    reference = booking.get("reference")

    action = "Cancelled" if cancelled else "Attempted to cancel"
    start_str = _clean_time(start_time)
    end_str = _clean_time(end_time)
    title = f"{action} booking for {room_name} from {start_str} to {end_str}"

    if reference:
        title = f"{title} (ref {reference})"

    return title


def format_cancellation_response(response_data: dict[str, Any]) -> dict[str, Any]:
    """Format the cancellation response to include a succinct, human readable summary.

    Args:
        response_data: The JSON response from the cancellation API (dict).

    Returns:
        dict: The booking object with an added 'title' field.
    """
    booking = _normalise_booking(response_data)

    if "title" in booking:
        return booking

    booking["title"] = _build_title(booking)
    return booking
