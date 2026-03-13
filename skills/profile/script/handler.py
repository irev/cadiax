"""Profile skill handler."""

from __future__ import annotations

from cadiax.core.agent_context import ensure_agent_storage
from cadiax.services.personality import PersonalityService


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
    if command == "show-structured":
        structured = service.get_structured_profile()
        lines = ["Structured Preference Profile"]
        if structured.get("preferred_channels"):
            lines.append(f"- preferred_channels: {', '.join(structured['preferred_channels'])}")
        if structured.get("preferred_brevity"):
            lines.append(f"- preferred_brevity: {structured['preferred_brevity']}")
        if structured.get("formality"):
            lines.append(f"- formality: {structured['formality']}")
        if structured.get("proactive_mode"):
            lines.append(f"- proactive_mode: {structured['proactive_mode']}")
        if structured.get("summary_style"):
            lines.append(f"- summary_style: {structured['summary_style']}")
        if len(lines) == 1:
            lines.append("- belum ada profil preferensi terstruktur")
        return "\n".join(lines)
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
    if command == "remove-preference":
        if not remainder:
            return "Profile remove-preference membutuhkan isi."
        removed = service.remove_preference(remainder)
        return "Preference dihapus dari profile." if removed else "Preference tidak ditemukan."
    if command == "reset-preferences":
        service.reset_preferences()
        return "Structured preferences direset."
    if command == "set-formality":
        if not remainder:
            return "Profile set-formality membutuhkan isi."
        service.update_structured_profile(formality=remainder)
        return "Formality preference diperbarui."
    if command == "set-brevity":
        if not remainder:
            return "Profile set-brevity membutuhkan isi."
        service.update_structured_profile(preferred_brevity=remainder)
        return "Brevity preference diperbarui."
    if command == "set-proactive-mode":
        if not remainder:
            return "Profile set-proactive-mode membutuhkan isi."
        service.update_structured_profile(proactive_mode=remainder)
        return "Proactive mode preference diperbarui."
    if command == "set-summary-style":
        if not remainder:
            return "Profile set-summary-style membutuhkan isi."
        service.update_structured_profile(summary_style=remainder)
        return "Summary style preference diperbarui."
    if command == "set-channels":
        channels = [item.strip() for item in remainder.split(",") if item.strip()]
        if not channels:
            return "Profile set-channels membutuhkan daftar channel dipisah koma."
        service.update_structured_profile(preferred_channels=channels)
        return "Preferred channels diperbarui."
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
        "Usage: profile <show|show-structured|set-purpose|add-preference|remove-preference|reset-preferences|set-formality|set-brevity|set-proactive-mode|set-summary-style|set-channels|add-constraint|add-context> ...\n"
        "Examples:\n"
        "- profile set-purpose bangun private ai internal\n"
        "- profile add-preference jawaban ringkas\n"
        "- profile set-channels telegram,email\n"
        "- profile show"
    )
