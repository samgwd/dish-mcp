"""Constants for the Dish MCP server."""

# Base URL for the Dish Manchester API
BASE_URL = "https://dish-manchester.officernd.com/community/i/organizations/dish-manchester"

# API endpoints
BOOKINGS_ENDPOINT = f"{BASE_URL}/user/bookings"
BOOKINGS_OCCURRENCES_ENDPOINT = f"{BASE_URL}/user/bookings/occurrences"

# Room name to ID mappings
ROOM_NAME_TO_ID = {
    "Boyle": "6422bced61d5854ab3fedd62",
    "Pankhurst": "6422bcd50340a914e68e661b",
    "Turing": "6422bcff9814c9c32ed62d77",
}

# Room ID to name mappings (reverse of ROOM_NAME_TO_ID)
ROOM_ID_TO_NAME = {v: k for k, v in ROOM_NAME_TO_ID.items()}


def get_cancel_booking_endpoint(booking_id: str) -> str:
    """Get the cancel booking endpoint URL for a specific booking ID.

    Args:
        booking_id: The booking ID to cancel.

    Returns:
        The full URL for cancelling the booking.
    """
    return f"{BOOKINGS_ENDPOINT}/{booking_id}/cancel"
