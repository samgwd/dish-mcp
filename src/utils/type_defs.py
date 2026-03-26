"""Shared type definitions for the Dish MCP server."""

import ast
import json
from typing import Any

from pydantic import BaseModel, model_validator


def _parse_string_to_dict(data: str) -> Any:
    """Try to parse a string as JSON or Python dict literal."""
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        pass

    try:
        result = ast.literal_eval(data)
        if isinstance(result, dict):
            return result
    except (ValueError, SyntaxError):
        pass

    return data


class DatetimeRange(BaseModel):
    """Datetime range for booking."""

    start_datetime: str
    end_datetime: str

    @model_validator(mode="before")
    @classmethod
    def parse_string_input(cls, data: Any) -> Any:
        """Parse JSON or Python dict string input into a dictionary."""
        if isinstance(data, str):
            return _parse_string_to_dict(data)
        return data


class UserInfo(BaseModel):
    """User and team information."""

    team_id: str
    member_id: str

    @model_validator(mode="before")
    @classmethod
    def parse_string_input(cls, data: Any) -> Any:
        """Parse JSON or Python dict string input into a dictionary."""
        if isinstance(data, str):
            return _parse_string_to_dict(data)
        return data
