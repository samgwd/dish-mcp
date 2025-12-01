"""HTTP client helpers for room availability."""

from __future__ import annotations

from collections.abc import Iterable

import requests
from utils.constants import BOOKINGS_OCCURRENCES_ENDPOINT
from utils.type_defs import DatetimeRange


def _serialise_resource_ids(resource_ids: str | Iterable[str]) -> str:
    """Return a comma-separated string of resource identifiers."""
    if isinstance(resource_ids, str):
        return resource_ids
    return ",".join(resource_ids)


def get_room_availability(
    resource_ids: str | list[str],
    datetime_range: DatetimeRange,
    cookie: str,
    select: str = "$default",
    populate: str | None = None,
) -> requests.Response:
    """Get room availability from the Dish Manchester API.

    Args:
        resource_ids: Room resource IDs as a comma-separated string or list of strings
        datetime_range: Datetime range for the query
        cookie: Authentication cookie string (e.g., "connect.sid=...")
        select: Select parameter for the API (default: "$default")
        populate: Populate parameter for the API. If None, uses default populate string

    Returns:
        requests.Response: The HTTP response object

    Raises:
        requests.RequestException: If the request fails
    """
    resource_id_str = _serialise_resource_ids(resource_ids)

    if populate is None:
        populate = (
            "member._id,member.name,team._id,team.name,resourceId._id,resourceId.name,"
            "resourceId.office,resourceId.type,resourceId.rate,resourceId.room,resourceId.parents"
        )

    params = {
        "resourceId": resource_id_str,
        "start": datetime_range.start_datetime,
        "end": datetime_range.end_datetime,
        "$select": select,
        "$populate": populate,
    }

    headers = {"Content-Type": "application/json", "Cookie": cookie}

    response = requests.get(
        BOOKINGS_OCCURRENCES_ENDPOINT,
        params=params,
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()

    return response
