"""Web skill handler for HTTP requests and web scraping."""

import re
import urllib.request
import urllib.error
from typing import Any


def handle(args: str) -> str:
    """Handle web operations."""
    if not args:
        return "Usage: web <command> <args>\nCommands: get <url>, post <url> <data>"

    parts = args.strip().split(maxsplit=2)
    if len(parts) < 2:
        return "Usage: web <command> <url> [data]"

    command = parts[0].lower()
    url = parts[1]

    if command == "get":
        return _fetch_url(url)
    elif command == "post":
        if len(parts) < 3:
            return "POST requires data: web post <url> <data>"
        return _post_url(url, parts[2])
    else:
        return f"Unknown command: {command}. Use: get, post"


def _fetch_url(url: str) -> str:
    """Fetch content from URL."""
    try:
        # Add https:// if not present
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        req = urllib.request.Request(url, headers={"User-Agent": "OtonomAssist/1.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode("utf-8")
            # Truncate if too long
            if len(content) > 2000:
                return content[:2000] + "\n... (truncated)"
            return content
    except urllib.error.URLError as e:
        return f"Error fetching URL: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"


def _post_url(url: str, data: str) -> str:
    """POST data to URL."""
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        encoded_data = data.encode("utf-8")
        req = urllib.request.Request(
            url,
            data=encoded_data,
            headers={
                "User-Agent": "OtonomAssist/1.0",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return f"Status: {response.status}\nResponse: {response.read().decode('utf-8')}"
    except urllib.error.URLError as e:
        return f"Error posting to URL: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"
