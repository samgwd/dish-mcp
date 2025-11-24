# Function to cancel a room booking
import requests

ROOM_ID_TO_NAME = {
    "6422bced61d5854ab3fedd62": "Boyle",
    "6422bcd50340a914e68e661b": "Pankhurst",
    "6422bcff9814c9c32ed62d77": "Turing",
}


def cancel_booking(
    booking_id: str,
    cookie: str,
    skip_cancellation_policy: bool = False,
) -> requests.Response:
    """
    Cancel a room booking using the Dish Manchester API.

    Args:
        booking_id: The ID of the booking to cancel (e.g., "692192791c60f69c20311db3")
        cookie: Authentication cookie
        skip_cancellation_policy: Whether to skip cancellation policy (default: False)

    Returns:
        requests.Response: The HTTP response object
    """
    url = f"https://dish-manchester.officernd.com/community/i/organizations/dish-manchester/user/bookings/{booking_id}/cancel"

    params = {
        "skipCancellationPolicy": str(skip_cancellation_policy).lower(),
    }

    headers = {"Content-Type": "application/json", "Cookie": cookie}

    response = requests.post(url, params=params, headers=headers)

    return response


def format_cancellation_response(response_data):
    """
    Format the cancellation response to include a succinct, human readable summary.

    Args:
        response_data: The JSON response from the cancellation API (dict).

    Returns:
        dict: The booking object with an added 'title' field.
    """
    if not response_data:
        return {"title": "Cancellation succeeded but no details were returned."}

    if not isinstance(response_data, dict):
        return {"title": "Cancellation succeeded but response format was unexpected."}

    booking = response_data

    start_time = booking.get("start", {}).get("dateTime")
    end_time = booking.get("end", {}).get("dateTime")
    resource_id = booking.get("resourceId")
    reference = booking.get("reference")
    canceled = booking.get("canceled", False)

    room_name = ROOM_ID_TO_NAME.get(resource_id, "Unknown room")

    def clean_time(iso_str):
        if not iso_str:
            return "?"
        # Keep only the date and time, discard subseconds/timezone as we already
        # expose the timezone elsewhere in the payload.
        return iso_str.replace("T", " ").split(".")[0]

    start_str = clean_time(start_time)
    end_str = clean_time(end_time)

    if canceled:
        title = f"Cancelled booking for {room_name} from {start_str} to {end_str}"
    else:
        title = (
            f"Attempted to cancel booking for {room_name} from {start_str} to {end_str}"
        )

    if reference:
        title = f"{title} (ref {reference})"

    booking["title"] = title

    return booking
