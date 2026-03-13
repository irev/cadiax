"""Textual-based operator surface for Cadiax."""

from __future__ import annotations

from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Footer, Header, OptionList, Static

from cadiax.core.config_doctor import get_config_status_data
from cadiax.core.path_layout import get_runtime_layout_snapshot
from cadiax.core.setup_wizard import persist_env_updates
from cadiax.platform import get_service_runtime_info, get_service_wrapper_output_dir, write_service_wrapper_artifacts
from cadiax.platform.dashboard_runtime import disable_dashboard, enable_dashboard


SCREEN_OPTIONS: list[tuple[str, str]] = [
    ("home", "Home"),
    ("paths", "Paths"),
    ("doctor", "Doctor"),
    ("channels", "Channels"),
    ("services", "Services"),
    ("setup", "Setup"),
]

SETUP_STEPS: list[tuple[str, str]] = [
    ("provider", "Provider"),
    ("workspace", "Workspace"),
    ("telegram", "Telegram"),
    ("dashboard", "Dashboard"),
    ("interfaces", "Interfaces"),
    ("summary", "Summary"),
]

PROVIDER_OPTIONS = ["openai", "claude", "ollama", "lmstudio"]


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
        ("5", "go_services", "Services"),
        ("6", "go_setup", "Setup"),
        ("n", "next_setup_step", "Next setup step"),
        ("p", "prev_setup_step", "Previous setup step"),
        ("d", "toggle_dashboard", "Toggle Dashboard"),
        ("t", "toggle_telegram", "Toggle Telegram"),
        ("e", "cycle_setup_field", "Edit Setup Field"),
        ("a", "alternate_setup_field", "Alternate Setup Field"),
        ("s", "save_setup_step", "Save Setup Step"),
        ("w", "write_service_wrappers", "Write Service Wrappers"),
        ("r", "refresh_data", "Refresh"),
    ]

    def __init__(self, *, initial_screen: str = "home") -> None:
        super().__init__()
        self.initial_screen = initial_screen if initial_screen in dict(SCREEN_OPTIONS) else "home"
        self.status_data: dict[str, Any] = {}
        self.current_screen_name = self.initial_screen
        self.current_setup_step = 0
        self.setup_draft: dict[str, Any] = {}

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

    def action_go_services(self) -> None:
        self._select_screen("services")

    def action_go_setup(self) -> None:
        self._select_screen("setup")

    def action_refresh_data(self) -> None:
        self._reload()
        self._render_screen(self.current_screen_name)

    def action_next_setup_step(self) -> None:
        if self.current_screen_name != "setup":
            return
        self.current_setup_step = min(self.current_setup_step + 1, len(SETUP_STEPS) - 1)
        self._render_screen("setup")

    def action_prev_setup_step(self) -> None:
        if self.current_screen_name != "setup":
            return
        self.current_setup_step = max(self.current_setup_step - 1, 0)
        self._render_screen("setup")

    def action_toggle_dashboard(self) -> None:
        if self.current_screen_name not in {"channels", "services", "setup"}:
            return
        dashboard = self.status_data.get("dashboard", {})
        if bool(dashboard.get("enabled")):
            disable_dashboard()
            persist_env_updates({"DASHBOARD_ENABLED": "false"})
            self.notify("Dashboard disabled", severity="information")
        else:
            enabled = enable_dashboard(
                host=str(dashboard.get("host") or "127.0.0.1"),
                port=int(dashboard.get("port") or 8795),
                admin_api_url=str(dashboard.get("admin_api_url") or "http://127.0.0.1:8787"),
                install=False,
                build=False,
            )
            persist_env_updates(
                {
                    "DASHBOARD_ENABLED": "true",
                    "DASHBOARD_HOST": str(enabled.get("host") or "127.0.0.1"),
                    "DASHBOARD_PORT": str(int(enabled.get("port") or 8795)),
                    "DASHBOARD_ADMIN_API_URL": str(enabled.get("admin_api_url") or "http://127.0.0.1:8787"),
                }
            )
            self.notify("Dashboard enabled", severity="information")
        self._reload()
        self._render_screen(self.current_screen_name)

    def action_toggle_telegram(self) -> None:
        if self.current_screen_name not in {"channels", "setup"}:
            return
        telegram = self.status_data.get("telegram", {})
        currently_enabled = bool(telegram.get("enabled"))
        persist_env_updates({"TELEGRAM_ENABLED": "false" if currently_enabled else "true"})
        self.notify(
            f"Telegram {'disabled' if currently_enabled else 'enabled'}",
            severity="information",
        )
        self._reload()
        self._render_screen(self.current_screen_name)

    def action_write_service_wrappers(self) -> None:
        if self.current_screen_name != "services":
            return
        written = write_service_wrapper_artifacts(target="cadiax")
        output_dir = get_service_wrapper_output_dir()
        self.notify(
            f"Service wrappers written: {len(written)} files -> {output_dir}",
            severity="information",
        )
        self._reload()
        self._render_screen(self.current_screen_name)

    def action_cycle_setup_field(self) -> None:
        if self.current_screen_name != "setup":
            return
        step_key = SETUP_STEPS[self.current_setup_step][0]
        if step_key == "provider":
            current = str(self.setup_draft.get("provider") or "openai")
            index = PROVIDER_OPTIONS.index(current) if current in PROVIDER_OPTIONS else 0
            self.setup_draft["provider"] = PROVIDER_OPTIONS[(index + 1) % len(PROVIDER_OPTIONS)]
            self.notify(f"Provider draft: {self.setup_draft['provider']}", severity="information")
        elif step_key == "dashboard":
            current_host = str(self.setup_draft.get("dashboard_host") or "127.0.0.1")
            self.setup_draft["dashboard_host"] = "0.0.0.0" if current_host == "127.0.0.1" else "127.0.0.1"
            self.notify(
                f"Dashboard access draft: {'public' if self.setup_draft['dashboard_host'] == '0.0.0.0' else 'local'}",
                severity="information",
            )
        self._render_screen("setup")

    def action_alternate_setup_field(self) -> None:
        if self.current_screen_name != "setup":
            return
        step_key = SETUP_STEPS[self.current_setup_step][0]
        if step_key == "workspace":
            current = str(self.setup_draft.get("workspace_access") or "ro")
            self.setup_draft["workspace_access"] = "rw" if current == "ro" else "ro"
            self.notify(f"Workspace access draft: {self.setup_draft['workspace_access']}", severity="information")
            self._render_screen("setup")

    def action_save_setup_step(self) -> None:
        if self.current_screen_name != "setup":
            return
        step_key = SETUP_STEPS[self.current_setup_step][0]
        if step_key == "provider":
            persist_env_updates({"AI_PROVIDER": str(self.setup_draft.get("provider") or "openai")})
            self.notify("Provider saved", severity="information")
        elif step_key == "workspace":
            persist_env_updates({"OTONOMASSIST_WORKSPACE_ACCESS": str(self.setup_draft.get("workspace_access") or "ro")})
            self.notify("Workspace access saved", severity="information")
        elif step_key == "dashboard":
            host = str(self.setup_draft.get("dashboard_host") or "127.0.0.1")
            dashboard = self.status_data.get("dashboard", {})
            if bool(dashboard.get("enabled")):
                enable_dashboard(
                    host=host,
                    port=int(dashboard.get("port") or 8795),
                    admin_api_url=str(dashboard.get("admin_api_url") or "http://127.0.0.1:8787"),
                    install=False,
                    build=False,
                )
            persist_env_updates({"DASHBOARD_HOST": host})
            self.notify("Dashboard access saved", severity="information")
        else:
            self.notify("No writable field on this step yet", severity="warning")
            return
        self._reload()
        self._render_screen("setup")

    def _reload(self) -> None:
        self.status_data = get_config_status_data()
        self._sync_setup_draft()

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
        if screen_name == "services":
            content.update(build_services_view(self.status_data))
            return
        if screen_name == "setup":
            content.update(build_setup_view(self.status_data, step_index=self.current_setup_step, draft=self.setup_draft))
            return
        content.update(build_doctor_view(self.status_data))

    def _sync_setup_draft(self) -> None:
        ai = self.status_data.get("ai", {})
        workspace = self.status_data.get("workspace", {})
        dashboard = self.status_data.get("dashboard", {})
        self.setup_draft = {
            "provider": str(ai.get("provider") or "openai"),
            "workspace_access": str(workspace.get("access") or "ro"),
            "dashboard_host": str(dashboard.get("host") or "127.0.0.1"),
        }

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
        "- Tekan 5/6 untuk layanan dan setup coverage",
        "- Saat di Setup, tekan n/p untuk pindah step",
        "- Tekan d/t untuk toggle dashboard atau Telegram pada layar terkait",
        "- Saat di Setup, tekan e/a/s untuk edit draft dan simpan step",
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


def build_services_view(data: dict[str, Any]) -> str:
    service_info = get_service_runtime_info()
    runtime = data.get("runtime", {})
    scheduler = data.get("scheduler", {})
    dashboard = data.get("dashboard", {})
    lines = [
        "Services",
        "",
        "[Runtime]",
        f"backend          : {service_info.get('backend', '-')}",
        f"status           : {service_info.get('status', '-')}",
        f"supervisor_ready : {'yes' if service_info.get('supervisor_ready') else 'no'}",
        f"recommended_mode : {service_info.get('recommended_mode', '-')}",
        f"runtime_status   : {runtime.get('status', '-')}",
        f"scheduler_status : {scheduler.get('status', '-')}",
        f"wrapper_output   : {service_info.get('wrapper_output_dir', '-')}",
        "",
        "[Targets]",
    ]
    for item in service_info.get("supported_targets", []):
        if not isinstance(item, dict):
            continue
        extra = ""
        if item.get("default_port") is not None:
            extra = f" port={item['default_port']}"
        elif item.get("default_interval_seconds"):
            extra = f" interval={item['default_interval_seconds']:.0f}s"
        lines.append(f"- {item.get('name', '-')}: {item.get('description', '-')}{extra}")
    lines.extend(
        [
            "",
            "[Integrated Channels]",
            f"- telegram_in_main_service: {'yes' if data.get('telegram', {}).get('enabled') else 'no'}",
            f"- dashboard_enabled       : {'yes' if dashboard.get('enabled') else 'no'}",
            "- note                    : Telegram ikut service `cadiax`; bukan service utama terpisah",
            "",
            "[Actions]",
            "- d                       : toggle dashboard enable/disable",
            "- w                       : write service wrapper artifacts for `cadiax`",
        ]
    )
    return "\n".join(lines)


def build_setup_view(data: dict[str, Any], *, step_index: int = 0, draft: dict[str, Any] | None = None) -> str:
    ai = data.get("ai", {})
    workspace = data.get("workspace", {})
    telegram = data.get("telegram", {})
    dashboard = data.get("dashboard", {})
    personality = data.get("personality", {})
    preference_profile = personality.get("preference_profile", {}) if isinstance(personality, dict) else {}
    preferred_channels = preference_profile.get("preferred_channels", []) if isinstance(preference_profile, dict) else []
    draft = draft or {}
    step_index = max(0, min(step_index, len(SETUP_STEPS) - 1))
    step_key, step_label = SETUP_STEPS[step_index]
    lines = [
        "Setup Wizard",
        "",
        f"[Step] {step_index + 1}/{len(SETUP_STEPS)} - {step_label}",
        "",
        "Steps:",
    ]
    for index, (_, label) in enumerate(SETUP_STEPS, start=1):
        marker = ">" if index - 1 == step_index else "-"
        lines.append(f"{marker} {index}. {label}")
    lines.append("")
    if step_key == "provider":
        draft_provider = str(draft.get('provider') or ai.get('provider', '-') or "-")
        lines.extend(
            [
                "[Provider]",
                f"- provider               : {ai.get('provider', '-')}",
                f"- provider_draft         : {draft_provider}",
                f"- status                 : {ai.get('status', '-')}",
                "- setup global           : yes",
                "- mutable via wizard     : provider, model, base URL, secret preference",
                "- note                   : provider secret tetap dimask di doctor/TUI",
                "- quick action           : tekan e untuk cycle provider, s untuk save",
            ]
        )
    elif step_key == "workspace":
        lines.extend(
            [
                "[Workspace]",
                f"- workspace_root         : {workspace.get('root', '-')}",
                f"- workspace_access       : {workspace.get('access', '-')}",
                f"- workspace_access_draft : {draft.get('workspace_access') or workspace.get('access', '-')}",
                f"- root_exists            : {'yes' if workspace.get('root_exists') else 'no'}",
                "- setup global           : yes",
                "- mutable via wizard     : root, access mode, runtime docs bootstrap",
                "- quick action           : tekan a untuk toggle access, s untuk save",
            ]
        )
    elif step_key == "telegram":
        lines.extend(
            [
                "[Telegram]",
                f"- enabled                : {'yes' if telegram.get('enabled') else 'no'}",
                f"- dm_policy              : {telegram.get('dm_policy', '-')}",
                f"- group_policy           : {telegram.get('group_policy', '-')}",
                "- setup global           : yes",
                "- mutable via wizard     : token, owner IDs, DM/group policy, mention requirement",
                "- service integration    : ikut service `cadiax`, bukan target utama terpisah",
                "- quick action           : tekan t untuk toggle enabled",
            ]
        )
    elif step_key == "dashboard":
        lines.extend(
            [
                "[Dashboard]",
                f"- enabled                : {'yes' if dashboard.get('enabled') else 'no'}",
                f"- host                   : {dashboard.get('host', '-')}",
                f"- host_draft             : {draft.get('dashboard_host') or dashboard.get('host', '-')}",
                f"- port                   : {dashboard.get('port', '-')}",
                f"- admin_api_url          : {dashboard.get('admin_api_url', '-')}",
                "- setup global           : yes",
                "- mutable via wizard     : enable/disable, access mode, port, admin API URL",
                "- quick action           : tekan d untuk toggle enabled, e untuk cycle access, s untuk save",
            ]
        )
    elif step_key == "interfaces":
        lines.extend(
            [
                "[Per-Dispatch Interfaces]",
                "- email                  : no global credential form; configured per API/dispatch target",
                "- whatsapp               : no global credential form; configured per API/dispatch target",
                f"- preferred_channels     : {', '.join(preferred_channels) if preferred_channels else '-'}",
                "- setup global           : no",
                "- reason                 : current runtime stores messages/snapshots, not channel account credentials",
            ]
        )
    else:
        lines.extend(
            [
                "[Summary]",
                f"- provider/model         : {ai.get('provider', '-')}",
                f"- workspace_root         : {workspace.get('root', '-')}",
                f"- telegram_enabled       : {'yes' if telegram.get('enabled') else 'no'}",
                f"- dashboard_enabled      : {'yes' if dashboard.get('enabled') else 'no'}",
                f"- preferred_channels     : {', '.join(preferred_channels) if preferred_channels else '-'}",
                "",
                "[Current Boundary]",
                "- TUI sudah punya wizard step-by-step view",
                "- mutasi cepat yang sudah ada: toggle Telegram dan dashboard",
                "- `cadiax setup` tetap jadi jalur write penuh sampai phase T2",
            ]
        )
    return "\n".join(lines)


def run_tui(*, initial_screen: str = "home") -> None:
    """Start the Cadiax Textual app."""
    CadiaxTuiApp(initial_screen=initial_screen).run()
