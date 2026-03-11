"""Profile skill handler."""

from __future__ import annotations

from otonomassist.core.agent_context import (
    PROFILE_FILE,
    append_markdown_bullet,
    ensure_agent_storage,
    load_markdown,
    replace_section,
)


def handle(args: str) -> str:
    """Manage persistent agent profile."""
    ensure_agent_storage()
    args = args.strip()
    if not args:
        return _usage()

    command, _, remainder = args.partition(" ")
    command = command.lower().strip()
    remainder = remainder.strip()

    if command == "show":
        return load_markdown(PROFILE_FILE, max_chars=4000)
    if command == "set-purpose":
        if not remainder:
            return "Profile set-purpose membutuhkan isi."
        replace_section(PROFILE_FILE, "Purpose", remainder)
        return "Purpose profile diperbarui."
    if command == "add-preference":
        if not remainder:
            return "Profile add-preference membutuhkan isi."
        append_markdown_bullet(PROFILE_FILE, "Preferences", remainder)
        return "Preference ditambahkan ke profile."
    if command == "add-constraint":
        if not remainder:
            return "Profile add-constraint membutuhkan isi."
        append_markdown_bullet(PROFILE_FILE, "Constraints", remainder)
        return "Constraint ditambahkan ke profile."
    if command == "add-context":
        if not remainder:
            return "Profile add-context membutuhkan isi."
        append_markdown_bullet(PROFILE_FILE, "Long-term Context", remainder)
        return "Long-term context ditambahkan ke profile."

    return _usage()


def _usage() -> str:
    return (
        "Usage: profile <show|set-purpose|add-preference|add-constraint|add-context> ...\n"
        "Examples:\n"
        "- profile set-purpose bangun private ai internal\n"
        "- profile add-preference jawaban ringkas\n"
        "- profile show"
    )
