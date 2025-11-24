"""Shared type definitions for the Dish MCP server."""

from typing import TypedDict


class DatetimeRange(TypedDict):
    """Datetime range for booking."""

    start_datetime: str
    end_datetime: str


class UserInfo(TypedDict):
    """User and team information."""

    team_id: str
    member_id: str
