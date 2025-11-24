import requests
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from collections import defaultdict


def get_room_availability(
    resource_ids: Union[str, List[str]],
    start_date: str,
    end_date: str,
    cookie: str,
    base_url: str = "https://dish-manchester.officernd.com/community/i/organizations/dish-manchester/user/bookings/occurrences",
    select: str = "$default",
    populate: Optional[str] = None,
) -> requests.Response:
    """
    Get room availability from the Dish Manchester API.

    Args:
        resource_ids: Room resource IDs as a comma-separated string or list of strings
        start_date: Start date/time in ISO format (e.g., "2025-11-18T16:00:00.000Z")
        end_date: End date/time in ISO format (e.g., "2025-11-18T17:00:00.000Z")
        cookie: Authentication cookie string (e.g., "connect.sid=...")
        base_url: Base URL for the API endpoint (optional)
        select: Select parameter for the API (default: "$default")
        populate: Populate parameter for the API. If None, uses default populate string

    Returns:
        requests.Response: The HTTP response object

    Raises:
        requests.RequestException: If the request fails
    """
    if isinstance(resource_ids, list):
        resource_id_str = ",".join(resource_ids)
    else:
        resource_id_str = resource_ids

    if populate is None:
        populate = "member._id,member.name,team._id,team.name,resourceId._id,resourceId.name,resourceId.office,resourceId.type,resourceId.rate,resourceId.room,resourceId.parents"

    params = {
        "resourceId": resource_id_str,
        "start": start_date,
        "end": end_date,
        "$select": select,
        "$populate": populate,
    }

    headers = {"Content-Type": "application/json", "Cookie": cookie}

    response = requests.get(base_url, params=params, headers=headers)
    response.raise_for_status()

    return response


def extract_room_availability(
    bookings: List[Dict[str, Any]],
    start_date: str,
    end_date: str,
    queried_room_ids: Optional[List[str]] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Extract availability for each room from bookings data.

    Note: The API only returns bookings that exist. If a room has no bookings
    during the time range, it won't appear in the response. Rooms with no
    bookings are completely available for the entire time range.

    Args:
        bookings: List of booking objects from the API response (empty if all rooms free)
        start_date: Start date of the query range (ISO format)
        end_date: End date of the query range (ISO format)
        queried_room_ids: Optional list of room IDs that were queried. If provided and
                         a room ID doesn't appear in bookings, it will be marked as
                         completely available. If None, only rooms with bookings are processed.

    Returns:
        Dictionary mapping room names to availability data including:
        - available_slots: List of free time periods
        - booked_slots: List of booked time periods
        - total_available_minutes: Total free time
        - total_booked_minutes: Total booked time
    """
    range_start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
    range_end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
    total_range_minutes = int((range_end - range_start).total_seconds() / 60)

    room_id_to_name = {
        "6422bced61d5854ab3fedd62": "Boyle",
        "6422bcd50340a914e68e661b": "Pankhurst",
        "6422bcff9814c9c32ed62d77": "Turing",
    }
    rooms_in_response = set()

    room_bookings: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    # Handle empty bookings response (all rooms are free)
    if not bookings:
        availability: Dict[str, Dict[str, Any]] = {}
        if queried_room_ids:
            for room_id in queried_room_ids:
                room_key = f"Room_{room_id}"
                availability[room_key] = {
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
                    "note": "No bookings found - room completely available",
                    "room_id": room_id,
                }
        else:
            print("Warning: Empty bookings response and no queried_room_ids provided.")
            print("Cannot determine which rooms are available.")
        return availability

    for booking in bookings:
        room_name = str(booking["resourceId"]["name"])
        room_id = str(booking["resourceId"]["_id"])
        rooms_in_response.add(room_id)
        room_id_to_name[room_id] = room_name
        booking_id = str(booking["bookingId"])

        start_time = datetime.fromisoformat(
            str(booking["start"]["dateTime"]).replace("Z", "+00:00")
        )
        end_time = datetime.fromisoformat(
            str(booking["end"]["dateTime"]).replace("Z", "+00:00")
        )

        room_bookings[room_name].append(
            {
                "start": start_time,
                "end": end_time,
                "booking": booking,
                "room_id": room_id,
                "booking_id": booking_id,
            }
        )

    availability = {}

    for room_name, bookings_list in room_bookings.items():
        sorted_bookings = sorted(bookings_list, key=lambda x: x["start"])  # type: ignore[arg-type]

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
                        "duration_minutes": int(
                            (booking_start - current_time).total_seconds() / 60
                        ),
                    }
                )

            current_time = max(current_time, booking_end)

        if current_time < range_end:
            available_slots.append(
                {
                    "start": current_time.isoformat(),
                    "end": range_end.isoformat(),
                    "duration_minutes": int(
                        (range_end - current_time).total_seconds() / 60
                    ),
                }
            )

        availability[room_name] = {
            "available_slots": available_slots,
            "booked_slots": [
                {
                    "start": b["start"].isoformat(),
                    "end": b["end"].isoformat(),
                    "summary": str(b["booking"].get("summary", "")),
                    "member": (
                        str(b["booking"].get("member", {}).get("name", ""))
                        if b["booking"].get("member")
                        else None
                    ),
                    "bookingId": b["booking_id"],
                }
                for b in sorted_bookings
            ],
            "total_available_minutes": sum(
                slot["duration_minutes"] for slot in available_slots
            ),
            "total_booked_minutes": sum(
                int((b["end"] - b["start"]).total_seconds() / 60)
                for b in sorted_bookings
            ),
        }

    if queried_room_ids:
        for room_id in queried_room_ids:
            if room_id not in rooms_in_response:
                room_name = room_id_to_name.get(room_id, f"Room_{room_id}")

                availability[room_name] = {
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
                    "note": "No bookings found - room completely available",
                    "room_id": room_id,
                }

    return availability


def display_room_availability(
    response: requests.Response,
    start_date: str,
    end_date: str,
    queried_room_ids: Optional[List[str]] = None,
    max_bookings_to_show: int = 5,
) -> Optional[Dict[str, Any]]:
    """
    Extract and display room availability from an API response.

    Args:
        response: The HTTP response object from get_room_availability()
        start_date: Start date/time in ISO format (e.g., "2025-11-18T16:00:00.000Z")
        end_date: End date/time in ISO format (e.g., "2025-11-18T17:00:00.000Z")
        queried_room_ids: Optional list of room IDs that were queried
        max_bookings_to_show: Maximum number of booked slots to display per room (default: 5)

    Returns:
        Dictionary mapping room names to availability data, or None if response status is not 200
    """
    if response.status_code != 200:
        print("Error: Could not fetch bookings data")
        return None

    bookings_data = response.json()

    availability: Dict[str, Dict[str, Any]] = extract_room_availability(
        bookings_data, start_date, end_date, queried_room_ids=queried_room_ids
    )

    print("=" * 80)
    print("ROOM AVAILABILITY SUMMARY")
    print("=" * 80)

    if not availability:
        print("\nNo rooms found in response.")
        if queried_room_ids:
            print(
                f"\nNote: {len(queried_room_ids)} room(s) were queried but none appear in bookings."
            )
            print("This likely means all rooms are completely free for the time range.")
            print(f"\nQueried room IDs: {', '.join(queried_room_ids)}")

    for room_name, room_data in availability.items():
        print(f"\n{room_name}:")

        if "note" in room_data:
            print(f"  Note: {room_data['note']}")

        print(f"  Total Available: {room_data['total_available_minutes']} minutes")
        print(f"  Total Booked: {room_data['total_booked_minutes']} minutes")
        print(f"  Available Slots: {len(room_data['available_slots'])}")
        print(f"  Booked Slots: {len(room_data['booked_slots'])}")

        if room_data["available_slots"]:
            print("\n  Available Time Slots:")
            for slot in room_data["available_slots"]:
                start = datetime.fromisoformat(slot["start"].replace("+00:00", ""))
                end = datetime.fromisoformat(slot["end"].replace("+00:00", ""))
                print(
                    f"    {start.strftime('%Y-%m-%d %H:%M')} - {end.strftime('%H:%M')} ({slot['duration_minutes']} min)"
                )

        if room_data["booked_slots"]:
            print("\n  Booked Time Slots:")
            for slot in room_data["booked_slots"][:max_bookings_to_show]:
                start = datetime.fromisoformat(slot["start"].replace("+00:00", ""))
                end = datetime.fromisoformat(slot["end"].replace("+00:00", ""))
                member_info = f" ({slot['member']})" if slot["member"] else ""
                summary_info = f" - {slot['summary']}" if slot["summary"] else ""
                booking_id_info = (
                    f" (booking ID: {slot['bookingId']})" if slot["bookingId"] else ""
                )
                print(
                    f"    {start.strftime('%Y-%m-%d %H:%M')} - {end.strftime('%H:%M')}{member_info}{summary_info}{booking_id_info}"
                )

            if len(room_data["booked_slots"]) > max_bookings_to_show:
                print(
                    f"    ... and {len(room_data['booked_slots']) - max_bookings_to_show} more bookings"
                )

    return availability
