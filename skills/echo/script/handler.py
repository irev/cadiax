"""Echo skill handler."""


def handle(args: str) -> str:
    """Handle echo requests."""
    if not args:
        return "Usage: echo <text>"
    return args
