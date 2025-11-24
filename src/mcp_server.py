from fastmcp import FastMCP, Context
from typing import List, Optional
import os
import sys


# Ensure we can import from src if running from root or directly
try:
    from .get_room_availability import get_room_availability, extract_room_availability
    from .book_room import book_room as book_room_api, format_booking_response
    from .cancel_booking import (
        cancel_booking as cancel_booking_api,
        format_cancellation_response,
    )
except ImportError:
    try:
        from get_room_availability import (
            get_room_availability,
            extract_room_availability,
        )
        from book_room import book_room as book_room_api, format_booking_response
        from cancel_booking import (
            cancel_booking as cancel_booking_api,
            format_cancellation_response,
        )
    except ImportError:
        # If running from root, we might need to add src to path
        sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
        from src.get_room_availability import (
            get_room_availability,
            extract_room_availability,
        )
        from src.book_room import book_room as book_room_api, format_booking_response
        from src.cancel_booking import (
            cancel_booking as cancel_booking_api,
            format_cancellation_response,
        )

mcp = FastMCP("Dish MCP")


@mcp.tool
def check_availability_and_list_bookings(
    start_date: str,
    end_date: str,
    resource_ids: Optional[List[str]] = None,
    cookie: Optional[str] = None,
    ctx: Context = None,
) -> str:
    """
    Check room availability for the Dish Manchester API and list bookings for a room and date range.

    Args:
        start_date: Start date/time in ISO format (e.g., "2025-11-18T16:00:00.000Z")
        end_date: End date/time in ISO format (e.g., "2025-11-18T17:00:00.000Z")
        resource_ids: Optional list of room resource IDs to query.
        cookie: Authentication cookie. If not provided, looks for DISH_COOKIE env var.
    """
    if not cookie:
        cookie = os.environ.get("DISH_COOKIE")

    if not cookie:
        return "Error: No authentication cookie provided. Please provide a cookie or set DISH_COOKIE environment variable."

    if not resource_ids:
        # Default room IDs from the notebook/code
        resource_ids = [
            "6422bced61d5854ab3fedd62",  # Boyle
            "6422bcd50340a914e68e661b",  # Pankhurst
            "6422bcff9814c9c32ed62d77",  # Turing
        ]

    try:
        response = get_room_availability(
            resource_ids=resource_ids,
            start_date=start_date,
            end_date=end_date,
            cookie=cookie,
        )

        if response.status_code != 200:
            return f"Error: API returned status {response.status_code}"

        bookings_data = response.json()
        availability = extract_room_availability(
            bookings_data, start_date, end_date, queried_room_ids=resource_ids
        )

        # Format the output as a string
        output = []
        output.append("ROOM AVAILABILITY SUMMARY")
        output.append("=" * 30)

        for room_name, room_data in availability.items():
            output.append(f"\n{room_name}:")
            if "note" in room_data:
                output.append(f"  Note: {room_data['note']}")

            output.append(
                f"  Total Available: {room_data['total_available_minutes']} minutes"
            )
            output.append(
                f"  Total Booked: {room_data['total_booked_minutes']} minutes"
            )

            if room_data["available_slots"]:
                output.append("  Available Time Slots:")
                for slot in room_data["available_slots"]:
                    start = slot["start"].replace("+00:00", "").replace("T", " ")[:16]
                    end = slot["end"].replace("+00:00", "").replace("T", " ")[:16]
                    output.append(
                        f"    {start} - {end} ({slot['duration_minutes']} min)"
                    )

            if room_data["booked_slots"]:
                output.append("  Booked Time Slots:")
                for slot in room_data["booked_slots"]:
                    start = slot["start"].replace("+00:00", "").replace("T", " ")[:16]
                    end = slot["end"].replace("+00:00", "").replace("T", " ")[:16]
                    summary = f" - {slot['summary']}" if slot.get("summary") else ""
                    member = f" ({slot['member']})" if slot.get("member") else ""
                    booking_id = (
                        f" (booking ID: {slot['bookingId']})"
                        if slot.get("bookingId")
                        else ""
                    )
                    output.append(f"    {start} - {end}{member}{summary}{booking_id}")

        return "\n".join(output)

    except Exception as e:
        return f"Error checking availability: {str(e)}"


@mcp.tool
def book_room(
    start_date: str,
    end_date: str,
    meeting_room_name: str,
    team_id: Optional[str] = None,
    member_id: Optional[str] = None,
    cookie: Optional[str] = None,
    summary: str = "Fuzzy Labs Meeting",
) -> str:
    """
    Book a room using the Dish Manchester API.

    Args:
        start_date: Start date/time in ISO format (e.g., "2025-11-18T16:00:00.000Z")
        end_date: End date/time in ISO format (e.g., "2025-11-18T17:00:00.000Z")
        meeting_room_name: Name of the meeting room
        team_id: Team ID
        member_id: Member ID
        cookie: Authentication cookie. If not provided, looks for DISH_COOKIE env var.
        summary: Title of the booking: default to "meeting"
    """
    if not cookie:
        cookie = os.environ.get("DISH_COOKIE")
    if not team_id:
        team_id = os.environ.get("TEAM_ID")
    if not member_id:
        member_id = os.environ.get("MEMBER_ID")

    if not cookie:
        return "Error: No authentication cookie provided. Please provide a cookie or set DISH_COOKIE environment variable."

    try:
        response = book_room_api(
            start_datetime=start_date,
            end_datetime=end_date,
            meeting_room_name=meeting_room_name,
            team_id=team_id,
            member_id=member_id,
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
    cookie: Optional[str] = None,
    skip_cancellation_policy: bool = False,
) -> str:
    """
    Cancel a room booking using the Dish Manchester API. To cancel a booking, you need to know the
    booking ID. You can get the booking ID by using the `check_availability` tool to get the
    bookings for a room and date range.

    Args:
        booking_id: The ID of the booking to cancel (e.g., "692192791c60f69c20311db3")
        cookie: Authentication cookie. If not provided, looks for DISH_COOKIE env var.
        skip_cancellation_policy: Whether to skip cancellation policy (default: False)
    """
    if not cookie:
        cookie = os.environ.get("DISH_COOKIE")

    if not cookie:
        return "Error: No authentication cookie provided. Please provide a cookie or set DISH_COOKIE environment variable."

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
