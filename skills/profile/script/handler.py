"""Profile skill handler."""

from __future__ import annotations

from otonomassist.core.agent_context import ensure_agent_storage
from otonomassist.services.personality import PersonalityService


def handle(args: str) -> str:
    """Manage persistent agent profile."""
    ensure_agent_storage()
    service = PersonalityService()
    args = args.strip()
    if not args:
        return _usage()

    command, _, remainder = args.partition(" ")
    command = command.lower().strip()
    remainder = remainder.strip()

    if command == "show":
        return service.show_profile(max_chars=4000)
    if command == "set-purpose":
        if not remainder:
            return "Profile set-purpose membutuhkan isi."
        service.set_purpose(remainder)
        return "Purpose profile diperbarui."
    if command == "add-preference":
        if not remainder:
            return "Profile add-preference membutuhkan isi."
        service.add_preference(remainder)
        return "Preference ditambahkan ke profile."
    if command == "add-constraint":
        if not remainder:
            return "Profile add-constraint membutuhkan isi."
        service.add_constraint(remainder)
        return "Constraint ditambahkan ke profile."
    if command == "add-context":
        if not remainder:
            return "Profile add-context membutuhkan isi."
        service.add_context(remainder)
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
