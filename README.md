# DiSH MCP Server

This is a Model Context Protocol (MCP) server for the DiSH room booking website. This MCP had the following features:
- Check room availability
- Book a room
- Cancel a booking

## Prerequisites

- Python 3.10+
- `uv` (recommended for dependency management)

## Installation

1. Clone the repository.
2. Install dependencies:
   ```bash
   uv sync
   ```

## Usage

You can run the MCP server using `fastmcp`:

```bash
uv run fastmcp run src/mcp_server.py
```

## MCP Server Configuration

To use this MCP server with Cursor or Claude Desktop, you need to configure them with the correct command and environment variables.

### Environment Variables

The server requires a `DISH_COOKIE` environment variable to authenticate with the Dish MCP. To get this cookie:

1. **Open your browser** and navigate to the DiSH website
2. **Log in** to your account
3. **Open Developer Tools**:
   - **Chrome/Edge**: Press `F12` or `Cmd+Option+I` (Mac) / `Ctrl+Shift+I` (Windows/Linux)
   - **Firefox**: Press `F12` or `Cmd+Option+I` (Mac) / `Ctrl+Shift+I` (Windows/Linux)
4. **Go to the Application tab** (Chrome/Edge) or **Storage tab** (Firefox)
5. **In the left sidebar**, expand **Cookies**
6. **Click on the Dish website domain** (e.g., `app.dish.co` or similar)
7. **Find the `connect.sid` cookie** in the list
8. **Copy the cookie value** — it should look like:
   ```text
   s%3A6O3-ca7RRPse-Uw2YfxHSHODvvg1IbBn.rjqQh9E2x0isLpJq9%2Bmf3gxAAMr9OgQj%2BrgSnXRcz3c
   ```
9. **Use the full cookie string** in the format `connect.sid=<value>` for the `DISH_COOKIE` environment variable

> [!NOTE]
> The cookie expires periodically, so you may need to refresh it if authentication stops working.

### Cursor Configuration

Add the following to your Cursor MCP settings:

```json
"Dish MCP": {
  "command": "/Users/samgreenwood/code/personal_development/room-booking-bot/dish-mcp/.venv/bin/fastmcp",
  "args": [
    "run",
    "/Users/samgreenwood/code/personal_development/room-booking-bot/dish-mcp/src/mcp_server.py"
  ],
  "cwd": "/Users/samgreenwood/code/personal_development/room-booking-bot/dish-mcp",
  "env": {
    "DISH_COOKIE": "<YOUR_DISH_COOKIE>",
    "TEAM_ID":"<YOUR_TEAM_ID>",
    "MEMBER_ID":"<YOUR_MEMBER_ID>"
  },
  "transport": "stdio"
}
```

### Claude Desktop Configuration

Add the following to your `claude_desktop_config.json` (usually located at `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "Dish MCP": {
      "command": "/Users/samgreenwood/code/personal_development/room-booking-bot/dish-mcp/.venv/bin/fastmcp",
      "args": [
        "run",
        "/Users/samgreenwood/code/personal_development/room-booking-bot/dish-mcp/src/mcp_server.py"
      ],
      "cwd": "/Users/samgreenwood/code/personal_development/room-booking-bot/dish-mcp",
      "env": {
        "DISH_COOKIE": "<YOUR_DISH_COOKIE>",
        "TEAM_ID":"<YOUR_TEAM_ID>",
        "MEMBER_ID":"<YOUR_MEMBER_ID>"
      }
    }
  }
}
```

> [!NOTE]
> The paths in the configuration above are absolute paths specific to this environment. If you move the project, you will need to update these paths.
