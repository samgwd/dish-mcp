"""Automated cookie retrieval for Dish using Playwright."""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.async_api import Page, Request, async_playwright


@dataclass
class DishCredentials:
    """Container for Dish authentication credentials."""

    cookie: str
    team_id: str | None = None
    member_id: str | None = None

    def to_env_format(self) -> str:
        """Format credentials as .env file content."""
        lines = [f'DISH_COOKIE="{self.cookie}"']
        if self.team_id:
            lines.append(f'TEAM_ID="{self.team_id}"')
        if self.member_id:
            lines.append(f'MEMBER_ID="{self.member_id}"')
        return "\n".join(lines)

    def to_dict(self) -> dict[str, str]:
        """Convert credentials to a dictionary of env variable names to values."""
        result = {"DISH_COOKIE": self.cookie}
        if self.team_id:
            result["TEAM_ID"] = self.team_id
        if self.member_id:
            result["MEMBER_ID"] = self.member_id
        return result


def _read_env_lines(env_path: Path) -> list[str]:
    """Read lines from an existing .env file.

    Args:
        env_path: Path to the .env file

    Returns:
        List of lines (without trailing newlines), or empty list if file doesn't exist
    """
    if not env_path.exists():
        return []

    with open(env_path) as f:
        return [line.rstrip("\n") for line in f]


def _merge_env_lines(existing_lines: list[str], new_values: dict[str, str]) -> list[str]:
    """Merge new values into existing .env lines, preserving comments and order.

    Args:
        existing_lines: Lines from the existing .env file
        new_values: Dict of key=value pairs to merge in

    Returns:
        Updated list of lines
    """
    updated_keys: set[str] = set()
    new_lines: list[str] = []

    for line in existing_lines:
        updated_line = _process_env_line(line, new_values, updated_keys)
        new_lines.append(updated_line)

    for key, value in new_values.items():
        if key not in updated_keys:
            new_lines.append(f'{key}="{value}"')

    return new_lines


def _process_env_line(line: str, new_values: dict[str, str], updated_keys: set[str]) -> str:
    """Process a single .env line, replacing value if key matches.

    Args:
        line: The original line
        new_values: Dict of new values to apply
        updated_keys: Set to track which keys have been updated (modified in place)

    Returns:
        The processed line (may be unchanged or updated)
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return line

    key = stripped.split("=", 1)[0]
    if key in new_values:
        updated_keys.add(key)
        return f'{key}="{new_values[key]}"'
    return line


def _update_env_file(credentials: DishCredentials, env_path: Path) -> None:
    """Update or create .env file with new credentials.

    This preserves existing variables in the .env file and only updates
    the credential-related ones.

    Args:
        credentials: The credentials to write
        env_path: Path to the .env file
    """
    existing_lines = _read_env_lines(env_path)
    new_values = credentials.to_dict()
    merged_lines = _merge_env_lines(existing_lines, new_values)

    with open(env_path, "w") as f:
        f.write("\n".join(merged_lines))
        if merged_lines:
            f.write("\n")


def _extract_ids_from_url(url: str) -> tuple[str | None, str | None]:
    """Extract team_id and member_id from URL query parameters.

    Args:
        url: The full request URL

    Returns:
        Tuple of (team_id, member_id), either may be None
    """
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        team_id = params.get("team", [None])[0]
        member_id = params.get("member", [None])[0]
        return team_id, member_id
    except Exception:
        return None, None


async def get_dish_credentials_interactive() -> DishCredentials:
    """Launch browser for user to login, then extract cookie, team_id, and member_id.

    This opens a browser window where the user can complete the login
    (including any SSO/2FA), then waits for confirmation before extracting credentials.

    Returns:
        DishCredentials containing cookie, team_id, and member_id
    """
    async with async_playwright() as p:
        # Use persistent context to remember login between runs
        user_data_dir = Path.home() / ".dish-mcp" / "browser-data"
        user_data_dir.mkdir(parents=True, exist_ok=True)

        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,  # Show browser for user interaction
        )

        page = browser.pages[0] if browser.pages else await browser.new_page()

        captured_ids: dict[str, str | None] = {"team_id": None, "member_id": None}

        def handle_request(request: Request) -> None:
            if "occurrences" in request.url and "team=" in request.url:
                team_id, member_id = _extract_ids_from_url(request.url)
                if team_id:
                    captured_ids["team_id"] = team_id
                if member_id:
                    captured_ids["member_id"] = member_id

        page.on("request", handle_request)

        await page.goto("https://dish-manchester.officernd.com/")

        _print_instructions()

        await _wait_for_dashboard(page)

        await asyncio.sleep(2)

        credentials = await _build_credentials(page, captured_ids)
        await browser.close()
        return credentials


async def _wait_for_dashboard(page: Page, timeout_seconds: int = 300) -> None:
    """Wait for the page URL to contain /dashboard, indicating successful login.

    Args:
        page: The playwright page object
        timeout_seconds: Maximum time to wait (default 5 minutes)

    Raises:
        TimeoutError: If dashboard is not reached within timeout
    """
    print("\nWaiting for login to complete...")

    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        current_url = page.url
        if "/dashboard" in current_url:
            print("✓ Login detected!")
            return
        await asyncio.sleep(0.5)

    raise TimeoutError(
        f"Login did not complete within {timeout_seconds} seconds. Please try again."
    )


def _print_instructions() -> None:
    """Print user instructions for the interactive login process."""
    print("\n" + "=" * 60)
    print("DISH CREDENTIALS RETRIEVAL")
    print("=" * 60)
    print("\nComplete the login in the browser window that just opened.")
    print("This script will automatically detect when you reach the dashboard.")
    print("\n" + "=" * 60)


async def _build_credentials(page: Page, captured_ids: dict[str, str | None]) -> DishCredentials:
    """Extract cookie and build DishCredentials object.

    Args:
        page: The playwright page object
        captured_ids: Dict containing captured team_id and member_id

    Returns:
        DishCredentials with all available credentials

    Raises:
        RuntimeError: If cookie extraction fails
    """
    cookie_value = await _extract_session_cookie(page)

    if not cookie_value:
        raise RuntimeError(
            "Could not find connect.sid cookie. Make sure you completed the login successfully."
        )

    print("\n✓ Successfully retrieved session cookie!")

    if captured_ids["team_id"] and captured_ids["member_id"]:
        print("✓ Successfully captured team_id and member_id!")
    else:
        print("⚠ Could not capture team_id/member_id automatically.")
        print("  The 'occurrences' request may not have been made yet.")
        print("  Extract them manually from the Network tab (see README).")

    return DishCredentials(
        cookie=f"connect.sid={cookie_value}",
        team_id=captured_ids["team_id"],
        member_id=captured_ids["member_id"],
    )


async def get_dish_cookie_interactive() -> str:
    """Launch browser for user to login, then extract connect.sid cookie.

    This opens a browser window where the user can complete the login
    (including any SSO/2FA), then waits for confirmation before extracting the cookie.

    Returns:
        The full cookie string in format "connect.sid=<value>"

    Note:
        For retrieving team_id and member_id as well, use get_dish_credentials_interactive()
    """
    credentials = await get_dish_credentials_interactive()
    return credentials.cookie


async def _extract_session_cookie(page: Page) -> str | None:
    """Extract the connect.sid cookie from the current page context.

    Args:
        page: The playwright page object

    Returns:
        The value of the connect.sid cookie, or None if not found
    """
    cookies = await page.context.cookies()

    for cookie in cookies:
        if cookie["name"] == "connect.sid":
            return str(cookie["value"])

    return None


async def get_dish_cookie_headless(email: str, password: str) -> str:
    """Attempt headless login with email/password (may not work with SSO).

    Args:
        email: User's email address
        password: User's password

    Returns:
        The full cookie string in format "connect.sid=<value>"

    Note:
        This only works if Dish uses simple email/password authentication.
        If they use SSO (Google/Microsoft), use get_dish_cookie_interactive() instead.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto("https://dish-manchester.officernd.com/login")

        # Wait for login form and fill credentials
        await page.wait_for_selector('input[type="email"], input[name="email"]')
        await page.fill('input[type="email"], input[name="email"]', email)
        await page.fill('input[type="password"], input[name="password"]', password)

        await page.click('button[type="submit"]')

        # Wait for navigation to complete after login
        await page.wait_for_load_state("networkidle")

        # Poll for the cookie to appear (may take a moment after login)
        cookie_value = await _wait_for_cookie_with_timeout(page, timeout_seconds=30)

        await browser.close()

        if cookie_value:
            return f"connect.sid={cookie_value}"

        raise RuntimeError("Login failed - cookie not received")


async def _wait_for_cookie_with_timeout(page: Page, timeout_seconds: int = 30) -> str | None:
    """Poll for the connect.sid cookie with a timeout.

    Args:
        page: The playwright page object
        timeout_seconds: Maximum time to wait for the cookie

    Returns:
        The cookie value, or None if not found within timeout
    """
    start_time = time.time()

    while time.time() - start_time < timeout_seconds:
        cookie_value = await _extract_session_cookie(page)
        if cookie_value:
            return cookie_value
        await asyncio.sleep(0.5)

    return None


def get_dish_cookie() -> str:
    """Synchronous wrapper for cookie retrieval.

    First checks for stored cookie, then attempts interactive login if needed.

    Returns:
        The full cookie string in format "connect.sid=<value>"

    Raises:
        RuntimeError: If the cookie cannot be retrieved
    """
    stored_cookie = os.getenv("DISH_COOKIE")
    if stored_cookie:
        return stored_cookie

    return asyncio.run(get_dish_cookie_interactive())


def get_dish_credentials() -> DishCredentials:
    """Synchronous wrapper for full credentials retrieval.

    First checks for stored credentials, then attempts interactive login if needed.

    Returns:
        DishCredentials containing cookie, team_id, and member_id
    """
    stored_cookie = os.getenv("DISH_COOKIE")
    stored_team_id = os.getenv("TEAM_ID")
    stored_member_id = os.getenv("MEMBER_ID")

    # If we have all credentials stored, return them
    if stored_cookie and stored_team_id and stored_member_id:
        return DishCredentials(
            cookie=stored_cookie,
            team_id=stored_team_id,
            member_id=stored_member_id,
        )

    # Otherwise, get fresh credentials interactively
    return asyncio.run(get_dish_credentials_interactive())


def save_credentials_to_env(credentials: DishCredentials, env_path: Path | None = None) -> Path:
    """Save credentials to .env file.

    Args:
        credentials: The credentials to save
        env_path: Optional path to .env file. Defaults to .env in current directory.

    Returns:
        The path to the .env file that was updated
    """
    if env_path is None:
        env_path = Path.cwd() / ".env"

    _update_env_file(credentials, env_path)
    return env_path


if __name__ == "__main__":
    creds = asyncio.run(get_dish_credentials_interactive())

    script_dir = Path(__file__).parent.parent  # Go up from src/ to dish-mcp/
    env_file = script_dir / ".env"

    save_credentials_to_env(creds, env_file)

    print("\n" + "=" * 60)
    print(f"✓ Credentials saved to: {env_file}")
    print("=" * 60 + "\n")
    print(creds.to_env_format())
    print("\n" + "=" * 60)
