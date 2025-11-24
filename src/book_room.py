# Function to book a room
import requests

ROOM_NAME_TO_ID = {
    "Boyle": "6422bced61d5854ab3fedd62",
    "Pankhurst": "6422bcd50340a914e68e661b",
    "Turing": "6422bcff9814c9c32ed62d77",
}

ROOM_ID_TO_NAME = {v: k for k, v in ROOM_NAME_TO_ID.items()}


def book_room(
    start_datetime,
    end_datetime,
    meeting_room_name,
    team_id,
    member_id,
    cookie,
    summary,
):
    """
    Book a room using the Dish Manchester API.

    Args:
        start_datetime: Start datetime in ISO format (e.g., "2025-11-19T19:00:00.000Z")
        end_datetime: End datetime in ISO format (e.g., "2025-11-19T20:00:00.000Z")
        meeting_room_name: Name of the meeting room
        team_id: Team ID
        member_id: Member ID
        cookie: Cookie
        summary: Title of the booking

    Returns:
        requests.Response: The HTTP response object
    """
    url = "https://dish-manchester.officernd.com/community/i/organizations/dish-manchester/user/bookings"

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

    response = requests.post(url, json=payload, headers=headers)

    return response


def format_booking_response(response_data):
    """
    Format the booking response to include a succinct, human readable summary.

    Args:
        response_data: The JSON response from the booking API (dict or list).

    Returns:
        dict: The booking object with an added 'title' field.
    """
    if not response_data:
        return {"title": "Booking succeeded but no details were returned."}

    if isinstance(response_data, list):
        if not response_data:
            return {"title": "Booking succeeded but no details were returned."}
        booking = response_data[0]
    elif isinstance(response_data, dict):
        booking = response_data
    else:
        return {"title": "Booking succeeded but response format was unexpected."}

    start_time = booking.get("start", {}).get("dateTime")
    end_time = booking.get("end", {}).get("dateTime")
    resource_id = booking.get("resourceId")
    reference = booking.get("reference")

    room_name = ROOM_ID_TO_NAME.get(resource_id, "Unknown room")

    def clean_time(iso_str):
        if not iso_str:
            return "?"
        # Keep only the date and time, discard subseconds/timezone as we already
        # expose the timezone elsewhere in the payload.
        return iso_str.replace("T", " ").split(".")[0]

    start_str = clean_time(start_time)
    end_str = clean_time(end_time)

    title = f"Booked {room_name} from {start_str} to {end_str}"
    if reference:
        title = f"{title} (ref {reference})"

    booking["title"] = title

    return booking
