"""Textual-based operator surface for Cadiax."""

from __future__ import annotations

from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Footer, Header, OptionList, Static

from cadiax.core.config_doctor import get_config_status_data
from cadiax.core.path_layout import get_runtime_layout_snapshot


SCREEN_OPTIONS: list[tuple[str, str]] = [
    ("home", "Home"),
    ("paths", "Paths"),
    ("doctor", "Doctor"),
    ("channels", "Channels"),
]


class CadiaxTuiApp(App[None]):
    """Minimal TUI shell for local operator control."""

    TITLE = "Cadiax TUI"
    SUB_TITLE = "Backend Control Surface"
    CSS = """
    Screen {
        layout: vertical;
    }

    #shell {
        height: 1fr;
    }

    #nav {
        width: 26;
        min-width: 26;
        border: tall $primary;
    }

    #content-wrap {
        border: tall $accent;
        padding: 1 2;
    }

    #content {
        width: 1fr;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("1", "go_home", "Home"),
        ("2", "go_paths", "Paths"),
        ("3", "go_doctor", "Doctor"),
        ("4", "go_channels", "Channels"),
        ("r", "refresh_data", "Refresh"),
    ]

    def __init__(self, *, initial_screen: str = "home") -> None:
        super().__init__()
        self.initial_screen = initial_screen if initial_screen in dict(SCREEN_OPTIONS) else "home"
        self.status_data: dict[str, Any] = {}
        self.current_screen_name = self.initial_screen

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="shell"):
            yield OptionList(*[label for _, label in SCREEN_OPTIONS], id="nav")
            with VerticalScroll(id="content-wrap"):
                yield Static("", id="content")
        yield Footer()

    def on_mount(self) -> None:
        self._reload()
        nav = self.query_one("#nav", OptionList)
        nav.highlighted = self._screen_index(self.initial_screen)
        self._render_screen(self.initial_screen)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        screen_name = SCREEN_OPTIONS[event.option_index][0]
        self._render_screen(screen_name)

    def action_go_home(self) -> None:
        self._select_screen("home")

    def action_go_paths(self) -> None:
        self._select_screen("paths")

    def action_go_doctor(self) -> None:
        self._select_screen("doctor")

    def action_go_channels(self) -> None:
        self._select_screen("channels")

    def action_refresh_data(self) -> None:
        self._reload()
        self._render_screen(self.current_screen_name)

    def _reload(self) -> None:
        self.status_data = get_config_status_data()

    def _select_screen(self, screen_name: str) -> None:
        nav = self.query_one("#nav", OptionList)
        nav.highlighted = self._screen_index(screen_name)
        self._render_screen(screen_name)

    def _render_screen(self, screen_name: str) -> None:
        self.current_screen_name = screen_name
        content = self.query_one("#content", Static)
        if screen_name == "home":
            content.update(build_home_view(self.status_data))
            return
        if screen_name == "paths":
            content.update(build_paths_view(self.status_data))
            return
        if screen_name == "channels":
            content.update(build_channels_view(self.status_data))
            return
        content.update(build_doctor_view(self.status_data))

    @staticmethod
    def _screen_index(screen_name: str) -> int:
        for index, (name, _) in enumerate(SCREEN_OPTIONS):
            if name == screen_name:
                return index
        return 0


def build_home_view(data: dict[str, Any]) -> str:
    overall = data.get("overall", {})
    ai = data.get("ai", {})
    runtime = data.get("runtime", {})
    telegram = data.get("telegram", {})
    dashboard = data.get("dashboard", {})
    storage = data.get("storage", {})
    lines = [
        "Cadiax TUI",
        "",
        "[Overview]",
        f"status           : {overall.get('status', '-')}",
        f"path_mode        : {storage.get('path_mode', '-')}",
        f"provider         : {ai.get('provider', '-')}",
        f"ai_status        : {ai.get('status', '-')}",
        f"runtime_status   : {runtime.get('status', '-')}",
        f"telegram_status  : {telegram.get('status', '-')}",
        f"dashboard        : {'enabled' if dashboard.get('enabled') else 'disabled'}",
        "",
        "[Quick Paths]",
        f"config_file      : {storage.get('env_file', '-')}",
        f"state_dir        : {storage.get('state_dir', '-')}",
        f"workspace_root   : {data.get('workspace', {}).get('root', '-')}",
        f"dashboard_root   : {storage.get('dashboard_root', '-')}",
        "",
        "[Hints]",
        "- Tekan 1/2/3/4 untuk pindah layar",
        "- Tekan r untuk refresh snapshot",
        "- Tekan q untuk keluar",
    ]
    return "\n".join(lines)


def build_paths_view(data: dict[str, Any]) -> str:
    storage = data.get("storage", {})
    layout = get_runtime_layout_snapshot()
    lines = [
        "Runtime Paths",
        "",
        "[Mode]",
        f"path_mode        : {storage.get('path_mode', '-')}",
        f"command_kind     : {storage.get('command_kind', '-')}",
        f"command_on_path  : {storage.get('command_on_path', '-')}",
        f"command_detail   : {storage.get('command_detail', '-')}",
        "",
        "[Effective Layout]",
        f"config_file      : {layout.get('config_file', '-')}",
        f"config_dir       : {layout.get('config_dir', '-')}",
        f"state_dir        : {layout.get('state_dir', '-')}",
        f"workspace_root   : {layout.get('workspace_root', '-')}",
        f"app_root         : {layout.get('app_root', '-')}",
        f"dashboard_root   : {layout.get('dashboard_root', '-')}",
        f"python_exec      : {layout.get('python_executable', '-')}",
        f"venv_root        : {layout.get('venv_root') or '-'}",
    ]
    return "\n".join(lines)


def build_doctor_view(data: dict[str, Any]) -> str:
    issues = data.get("issues", [])
    ai = data.get("ai", {})
    workspace = data.get("workspace", {})
    routing = data.get("routing", {})
    privacy = data.get("privacy", {})
    lines = [
        "Doctor Snapshot",
        "",
        "[Core]",
        f"overall_status   : {data.get('overall', {}).get('status', '-')}",
        f"ai_status        : {ai.get('status', '-')}",
        f"workspace_status : {workspace.get('status', '-')}",
        f"privacy_status   : {privacy.get('status', '-')}",
        "",
        "[Routing]",
        f"builtin_routes   : {routing.get('builtin_routes_total', 0)}",
        f"direct_skill     : {routing.get('direct_skill_routes_total', 0)}",
        f"heuristic_routes : {routing.get('heuristic_routes_total', 0)}",
        f"ai_routes        : {routing.get('ai_routes_total', 0)}",
    ]
    if issues:
        lines.extend(["", "[Issues]"])
        lines.extend([f"- {issue}" for issue in issues])
    else:
        lines.extend(["", "[Issues]", "- none"])
    return "\n".join(lines)


def build_channels_view(data: dict[str, Any]) -> str:
    telegram = data.get("telegram", {})
    dashboard = data.get("dashboard", {})
    email = data.get("email", {})
    whatsapp = data.get("whatsapp", {})
    personality = data.get("personality", {})
    preference_profile = personality.get("preference_profile", {}) if isinstance(personality, dict) else {}
    preferred_channels = preference_profile.get("preferred_channels", []) if isinstance(preference_profile, dict) else []
    lines = [
        "Channels",
        "",
        "[Telegram]",
        f"enabled          : {'yes' if telegram.get('enabled') else 'no'}",
        f"status           : {telegram.get('status', '-')}",
        f"dm_policy        : {telegram.get('dm_policy', '-')}",
        f"group_policy     : {telegram.get('group_policy', '-')}",
        "",
        "[Dashboard]",
        f"enabled          : {'yes' if dashboard.get('enabled') else 'no'}",
        f"host             : {dashboard.get('host', '-')}",
        f"port             : {dashboard.get('port', '-')}",
        f"admin_api_url    : {dashboard.get('admin_api_url', '-')}",
        "",
        "[Email]",
        f"message_count    : {email.get('message_count', 0)}",
        f"latest_target    : {((email.get('latest_message') or {}).get('to_address', '-') if isinstance(email.get('latest_message'), dict) else '-')}",
        "global_setup     : none (configured per dispatch/API use)",
        "",
        "[WhatsApp]",
        f"message_count    : {whatsapp.get('message_count', 0)}",
        f"latest_target    : {((whatsapp.get('latest_message') or {}).get('phone_number', '-') if isinstance(whatsapp.get('latest_message'), dict) else '-')}",
        "global_setup     : none (configured per dispatch/API use)",
        "",
        "[Preference]",
        f"preferred_channels: {', '.join(preferred_channels) if preferred_channels else '-'}",
    ]
    return "\n".join(lines)


def run_tui(*, initial_screen: str = "home") -> None:
    """Start the Cadiax Textual app."""
    CadiaxTuiApp(initial_screen=initial_screen).run()
