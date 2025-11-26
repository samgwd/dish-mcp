# DiSH MCP Server

A Model Context Protocol (MCP) server for the DiSH room booking site. It exposes tools to check availability, book rooms, and cancel bookings so assistants like Cursor or Claude can manage your reservations.

## What it can do
- Search room availability across your DiSH locations
- Create bookings on your behalf
- Cancel or reschedule existing bookings
- Pair with calendar tools (e.g., [Google Calendar MCP](https://github.com/nspady/google-calendar-mcp)) to coordinate bookings with your calendar availability.

Example prompts:
- "Book meeting rooms for all my standups this week."
- "Reschedule my 1-1 with John to tomorrow afternoon when we’re both free and a room is open."
- "Book a meeting room for all my customer demos for the next 2 months."

## Requirements
- Python 3.10+
- [`uv`](https://github.com/astral-sh/uv) for dependency management

## Setup
```bash
uv sync
```

## Configuration
The server needs three environment variables:
- `DISH_COOKIE` — your DiSH `connect.sid` session cookie
- `TEAM_ID` — your DiSH team ID
- `MEMBER_ID` — your DiSH member ID

### Getting your `connect.sid` cookie
1. Log in to DiSH in your browser.
2. Open Developer Tools (F12 / Cmd+Option+I).
3. In Application/Storage > Cookies, select the DiSH domain.
4. Copy the `connect.sid` value (looks like `s%3A...`).
5. In your `.env` file, set `DISH_COOKIE` to `connect.sid=<value>`.

### Getting your team and member IDs
1. Log in to DiSH in your browser.
2. Open Developer Tools (F12 / Cmd+Option+I).
3. In Network tab, find the request labelled `booking-policy`
4. In the request payload, look for the `team_id` and `member_id` values.
5. Copy the `team_id` and `member_id` values (looks like `653ftv2a3l25h39b9k40e1029` and `9732dtgt60312dghe6`).
6. In your `.env` file, set `TEAM_ID` to `team_id=<value>` and `MEMBER_ID` to `member_id=<value>`.

**Keep this secret.** Do not commit cookies, team IDs or member IDs, or .env files to source control; regenerate the cookie if it stops working or was ever exposed.

## Run the MCP server
```bash
uv run fastmcp run src/mcp_server.py
```

## Configure your client

### Cursor
```json
"Dish MCP": {
  "command": "<PATH_TO_VENV>/bin/fastmcp",
  "args": ["run", "<PATH_TO_REPO>/src/mcp_server.py"],
  "cwd": "<PATH_TO_REPO>",
  "env": {
    "DISH_COOKIE": "<connect.sid=...>",
    "TEAM_ID": "<YOUR_TEAM_ID>",
    "MEMBER_ID": "<YOUR_MEMBER_ID>"
  },
  "transport": "stdio"
}
```

### Claude Desktop
Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "Dish MCP": {
      "command": "<PATH_TO_VENV>/bin/fastmcp",
      "args": ["run", "<PATH_TO_REPO>/src/mcp_server.py"],
      "cwd": "<PATH_TO_REPO>",
      "env": {
        "DISH_COOKIE": "<connect.sid=...>",
        "TEAM_ID": "<YOUR_TEAM_ID>",
        "MEMBER_ID": "<YOUR_MEMBER_ID>"
      }
    }
  }
}
```

> The cookie expires periodically; grab a fresh value if authentication fails.
