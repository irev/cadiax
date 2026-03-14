"""Textual-based operator surface for Cadiax."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Input, OptionList, Static

from cadiax.core.config_doctor import get_config_status_data
from cadiax.core.event_bus import get_event_bus_snapshot
from cadiax.core.execution_history import load_execution_events
from cadiax.core.execution_metrics import get_execution_metrics_snapshot
from cadiax.core.job_runtime import get_job_queue_summary
from cadiax.core.path_layout import get_runtime_layout_snapshot
from cadiax.core.setup_wizard import persist_env_updates
from cadiax.core.workspace_bootstrap import ensure_workspace_skeleton
from cadiax.platform import get_service_runtime_info, get_service_wrapper_output_dir, write_service_wrapper_artifacts
from cadiax.platform.dashboard_runtime import disable_dashboard, enable_dashboard
from cadiax.services.personality.startup_document_service import StartupDocumentService


SCREEN_OPTIONS: list[tuple[str, str]] = [
    ("home", "Home"),
    ("paths", "Paths"),
    ("doctor", "Doctor"),
    ("privacy", "Privacy"),
    ("bootstrap", "Bootstrap"),
    ("channels", "Channels"),
    ("services", "Services"),
    ("worker", "Worker"),
    ("scheduler", "Scheduler"),
    ("startup", "Startup"),
    ("setup", "Setup"),
    ("jobs", "Jobs"),
    ("metrics", "Metrics"),
    ("history", "History"),
    ("events", "Events"),
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
TELEGRAM_DM_POLICY_OPTIONS = ["pairing", "owner", "open", "disabled"]


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
        ("v", "go_privacy", "Privacy"),
        ("k", "go_bootstrap", "Bootstrap"),
        ("4", "go_channels", "Channels"),
        ("5", "go_services", "Services"),
        ("u", "go_worker", "Worker"),
        ("y", "go_scheduler", "Scheduler"),
        ("o", "go_startup", "Startup"),
        ("6", "go_setup", "Setup"),
        ("7", "go_jobs", "Jobs"),
        ("8", "go_metrics", "Metrics"),
        ("9", "go_history", "History"),
        ("0", "go_events", "Events"),
        ("n", "next_setup_step", "Next setup step"),
        ("p", "prev_setup_step", "Previous setup step"),
        ("d", "toggle_dashboard", "Toggle Dashboard"),
        ("t", "toggle_telegram", "Toggle Telegram"),
        ("e", "cycle_setup_field", "Edit Setup Field"),
        ("a", "alternate_setup_field", "Alternate Setup Field"),
        ("i", "input_setup_field", "Input Setup Field"),
        ("s", "save_setup_step", "Save Setup Step"),
        ("b", "run_bootstrap_foundation", "Bootstrap Foundation"),
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

    def action_go_privacy(self) -> None:
        self._select_screen("privacy")

    def action_go_bootstrap(self) -> None:
        self._select_screen("bootstrap")

    def action_go_channels(self) -> None:
        self._select_screen("channels")

    def action_go_services(self) -> None:
        self._select_screen("services")

    def action_go_worker(self) -> None:
        self._select_screen("worker")

    def action_go_scheduler(self) -> None:
        self._select_screen("scheduler")

    def action_go_startup(self) -> None:
        self._select_screen("startup")

    def action_go_setup(self) -> None:
        self._select_screen("setup")

    def action_go_jobs(self) -> None:
        self._select_screen("jobs")

    def action_go_metrics(self) -> None:
        self._select_screen("metrics")

    def action_go_history(self) -> None:
        self._select_screen("history")

    def action_go_events(self) -> None:
        self._select_screen("events")

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

    def action_run_bootstrap_foundation(self) -> None:
        if self.current_screen_name != "bootstrap":
            return
        result = ensure_workspace_skeleton(
            force=False,
            only_if_workspace_empty=False,
            runtime_docs_only=True,
        )
        self.notify(
            "Foundation bootstrap written="
            f"{result.get('written_count', 0)} existing={result.get('existing_count', 0)}",
            severity="information",
        )
        self._reload()
        self._render_screen("bootstrap")

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
        elif step_key == "telegram":
            current = str(self.setup_draft.get("telegram_dm_policy") or "pairing")
            index = TELEGRAM_DM_POLICY_OPTIONS.index(current) if current in TELEGRAM_DM_POLICY_OPTIONS else 0
            self.setup_draft["telegram_dm_policy"] = TELEGRAM_DM_POLICY_OPTIONS[
                (index + 1) % len(TELEGRAM_DM_POLICY_OPTIONS)
            ]
            self.notify(
                f"Telegram DM policy draft: {self.setup_draft['telegram_dm_policy']}",
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
            return
        if step_key == "dashboard":
            current_port = int(self.setup_draft.get("dashboard_port") or 8795)
            self.setup_draft["dashboard_port"] = current_port + 1
            self.notify(f"Dashboard port draft: {self.setup_draft['dashboard_port']}", severity="information")
            self._render_screen("setup")
            return
        if step_key == "telegram":
            current = str(self.setup_draft.get("telegram_require_mention") or "true")
            self.setup_draft["telegram_require_mention"] = "false" if current == "true" else "true"
            self.notify(
                f"Telegram require mention draft: {self.setup_draft['telegram_require_mention']}",
                severity="information",
            )
            self._render_screen("setup")

    def action_save_setup_step(self) -> None:
        if self.current_screen_name != "setup":
            return
        step_key = SETUP_STEPS[self.current_setup_step][0]
        if step_key == "provider":
            persist_env_updates({"AI_PROVIDER": str(self.setup_draft.get("provider") or "openai")})
            self.notify("Provider saved", severity="information")
        elif step_key == "workspace":
            workspace_root = str(
                self.setup_draft.get("workspace_root")
                or self.status_data.get("workspace", {}).get("root")
                or ""
            ).strip()
            if not workspace_root:
                self.notify("Workspace root belum diisi", severity="warning")
                return
            persist_env_updates(
                {
                    "OTONOMASSIST_WORKSPACE_ROOT": workspace_root,
                    "OTONOMASSIST_WORKSPACE_ACCESS": str(self.setup_draft.get("workspace_access") or "ro"),
                }
            )
            ensure_workspace_skeleton(
                only_if_workspace_empty=False,
                runtime_docs_only=True,
                workspace_root=Path(workspace_root).expanduser().resolve(),
            )
            self.notify("Workspace access saved", severity="information")
        elif step_key == "dashboard":
            host = str(self.setup_draft.get("dashboard_host") or "127.0.0.1")
            port = int(self.setup_draft.get("dashboard_port") or 8795)
            admin_api_url = str(
                self.setup_draft.get("dashboard_admin_api_url")
                or self.status_data.get("dashboard", {}).get("admin_api_url")
                or "http://127.0.0.1:8787"
            ).strip()
            if not admin_api_url:
                self.notify("Dashboard admin API URL belum diisi", severity="warning")
                return
            dashboard = self.status_data.get("dashboard", {})
            if bool(dashboard.get("enabled")):
                enable_dashboard(
                    host=host,
                    port=port,
                    admin_api_url=admin_api_url,
                    install=False,
                    build=False,
                )
            persist_env_updates(
                {
                    "DASHBOARD_HOST": host,
                    "DASHBOARD_PORT": str(port),
                    "DASHBOARD_ADMIN_API_URL": admin_api_url,
                }
            )
            self.notify("Dashboard access saved", severity="information")
        elif step_key == "telegram":
            persist_env_updates(
                {
                    "TELEGRAM_DM_POLICY": str(self.setup_draft.get("telegram_dm_policy") or "pairing"),
                    "TELEGRAM_REQUIRE_MENTION": str(self.setup_draft.get("telegram_require_mention") or "true"),
                }
            )
            self.notify("Telegram settings saved", severity="information")
        else:
            self.notify("No writable field on this step yet", severity="warning")
            return
        self._reload()
        self._render_screen("setup")

    def action_input_setup_field(self) -> None:
        if self.current_screen_name != "setup":
            return
        step_key = SETUP_STEPS[self.current_setup_step][0]
        if step_key == "workspace":
            self.push_screen(
                SetupInputScreen(
                    title="Workspace root",
                    field_name="workspace_root",
                    value=str(self.setup_draft.get("workspace_root") or self.status_data.get("workspace", {}).get("root") or ""),
                ),
                self._handle_setup_input,
            )
            return
        if step_key == "dashboard":
            self.push_screen(
                SetupInputScreen(
                    title="Dashboard admin API URL",
                    field_name="dashboard_admin_api_url",
                    value=str(
                        self.setup_draft.get("dashboard_admin_api_url")
                        or self.status_data.get("dashboard", {}).get("admin_api_url")
                        or "http://127.0.0.1:8787"
                    ),
                ),
                self._handle_setup_input,
            )

    def _handle_setup_input(self, result: tuple[str, str] | None) -> None:
        if not result:
            return
        field_name, value = result
        cleaned = value.strip()
        if field_name == "dashboard_admin_api_url" and not cleaned:
            self.notify("Dashboard admin API URL tidak boleh kosong", severity="warning")
            return
        self.setup_draft[field_name] = cleaned
        self.notify(f"{field_name} draft updated", severity="information")
        self._render_screen("setup")

    def _reload(self) -> None:
        self.status_data = get_config_status_data()
        self.status_data["jobs"] = get_job_queue_summary()
        self.status_data["metrics"] = get_execution_metrics_snapshot()
        self.status_data["history"] = load_execution_events(limit=15)
        self.status_data["events"] = get_event_bus_snapshot(limit=20)
        self.status_data["startup"] = StartupDocumentService().get_snapshot(session_mode="main")
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
        if screen_name == "privacy":
            content.update(build_privacy_view(self.status_data))
            return
        if screen_name == "bootstrap":
            content.update(build_bootstrap_view(self.status_data))
            return
        if screen_name == "channels":
            content.update(build_channels_view(self.status_data))
            return
        if screen_name == "services":
            content.update(build_services_view(self.status_data))
            return
        if screen_name == "worker":
            content.update(build_worker_view(self.status_data))
            return
        if screen_name == "scheduler":
            content.update(build_scheduler_view(self.status_data))
            return
        if screen_name == "startup":
            content.update(build_startup_view(self.status_data))
            return
        if screen_name == "setup":
            content.update(build_setup_view(self.status_data, step_index=self.current_setup_step, draft=self.setup_draft))
            return
        if screen_name == "jobs":
            content.update(build_jobs_view(self.status_data))
            return
        if screen_name == "metrics":
            content.update(build_metrics_view(self.status_data))
            return
        if screen_name == "history":
            content.update(build_history_view(self.status_data))
            return
        if screen_name == "events":
            content.update(build_events_view(self.status_data))
            return
        content.update(build_doctor_view(self.status_data))

    def _sync_setup_draft(self) -> None:
        ai = self.status_data.get("ai", {})
        workspace = self.status_data.get("workspace", {})
        dashboard = self.status_data.get("dashboard", {})
        self.setup_draft = {
            "provider": str(ai.get("provider") or "openai"),
            "workspace_root": str(workspace.get("root") or ""),
            "workspace_access": str(workspace.get("access") or "ro"),
            "dashboard_host": str(dashboard.get("host") or "127.0.0.1"),
            "dashboard_port": int(dashboard.get("port") or 8795),
            "dashboard_admin_api_url": str(dashboard.get("admin_api_url") or "http://127.0.0.1:8787"),
            "telegram_dm_policy": str(self.status_data.get("telegram", {}).get("dm_policy") or "pairing"),
            "telegram_require_mention": "true"
            if bool(self.status_data.get("telegram", {}).get("require_mention", True))
            else "false",
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
        "- Tekan 5/u/y/o/6/7/8/9/0 untuk services, worker, scheduler, startup, setup, jobs, metrics, history, dan events",
        "- Saat di Setup, tekan n/p untuk pindah step",
        "- Tekan d/t untuk toggle dashboard atau Telegram pada layar terkait",
        "- Saat di Setup, tekan e/a/i/s untuk edit draft dan simpan step",
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


def build_privacy_view(data: dict[str, Any]) -> str:
    privacy = data.get("privacy", {})
    controls = data.get("privacy_controls", {})
    retention = controls.get("retention_candidates", {})
    scoped_controls = controls.get("scoped_controls", {})
    lines = [
        "Privacy Controls",
        "",
        "[Redaction]",
        f"status                    : {privacy.get('status', '-')}",
        f"redaction_enabled         : {'yes' if privacy.get('redaction_enabled') else 'no'}",
        f"replacement_label         : {privacy.get('replacement_label', '-')}",
        f"pattern_count             : {privacy.get('pattern_count', 0)}",
        "",
        "[Governance]",
        f"quiet_hours_enabled       : {'yes' if (controls.get('quiet_hours') or {}).get('enabled') else 'no'}",
        f"quiet_hours_window        : {((controls.get('quiet_hours') or {}).get('start') or '-')} -> {((controls.get('quiet_hours') or {}).get('end') or '-')}",
        f"quiet_hours_active        : {'yes' if controls.get('quiet_hours_active') else 'no'}",
        f"proactive_enabled         : {'yes' if controls.get('proactive_assistance_enabled') else 'no'}",
        f"consent_required          : {'yes' if controls.get('consent_required_for_proactive') else 'no'}",
        f"memory_retention_days     : {controls.get('memory_retention_days', '-')}",
        f"scope_count               : {controls.get('scope_count', 0)}",
        f"filter_scope              : {controls.get('filter_agent_scope') or '-'}",
        f"filter_roles              : {', '.join(controls.get('filter_roles', [])) or '-'}",
        "",
        "[Data Counts]",
        f"memory_entries            : {controls.get('memory_entry_count', 0)}",
        f"memory_summaries          : {controls.get('memory_summary_count', 0)}",
        f"notifications             : {controls.get('notification_count', 0)}",
        f"email_messages            : {controls.get('email_count', 0)}",
        f"whatsapp_messages         : {controls.get('whatsapp_count', 0)}",
        f"identity_count            : {controls.get('identity_count', 0)}",
        f"session_count             : {controls.get('session_count', 0)}",
        "",
        "[Retention Candidates]",
    ]
    if retention:
        for key, value in sorted(retention.items()):
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- none")
    lines.extend(["", "[Scoped Controls]"])
    if scoped_controls:
        for scope_name, payload in sorted(scoped_controls.items()):
            lines.append(
                f"- {scope_name}: proactive={'yes' if payload.get('proactive_assistance_enabled', True) else 'no'}, "
                f"consent={'yes' if payload.get('consent_required_for_proactive', True) else 'no'}, "
                f"roles={', '.join(payload.get('allowed_roles', [])) or '-'}"
            )
    else:
        lines.append("- none")
    return "\n".join(lines)


def build_bootstrap_view(data: dict[str, Any]) -> str:
    bootstrap = data.get("bootstrap", {})
    manifest = bootstrap.get("manifest", {})
    seeded_files = bootstrap.get("workspace_seeded_files", [])
    lines = [
        "Workspace Bootstrap",
        "",
        "[Summary]",
        f"bundled_template_dir      : {bootstrap.get('bundled_template_dir', '-')}",
        f"template_count            : {bootstrap.get('template_count', 0)}",
        f"active_runtime_templates  : {bootstrap.get('active_runtime_template_count', 0)}",
        f"workspace_seeded_count    : {bootstrap.get('workspace_seeded_count', 0)}",
        f"manifest_file             : {bootstrap.get('manifest_file', '-')}",
        "",
        "[Seeded Files]",
    ]
    if seeded_files:
        for name in seeded_files:
            lines.append(f"- {name}")
    else:
        lines.append("- belum ada file workspace yang diseed")
    lines.extend(
        [
            "",
            "[Last Manifest]",
            f"source                    : {manifest.get('source', '-')}",
            f"runtime_docs_only         : {'yes' if manifest.get('runtime_docs_only', True) else 'no'}",
            f"seeded_at                 : {manifest.get('seeded_at', '-')}",
            f"workspace_root            : {manifest.get('workspace_root', '-')}",
            f"written_count             : {len(manifest.get('written', [])) if isinstance(manifest.get('written'), list) else 0}",
            f"existing_count            : {len(manifest.get('existing', [])) if isinstance(manifest.get('existing'), list) else 0}",
            "",
            "[Action]",
            "- b                       : seed active runtime docs into workspace root",
        ]
    )
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
    lines.extend(["", "[Target Detail]"])
    for item in service_info.get("supported_targets", []):
        if not isinstance(item, dict):
            continue
        lines.append(f"- {item.get('name', '-')}")
        lines.append(f"  default_steps        : {item.get('default_steps', 0)}")
        lines.append(f"  default_interval     : {item.get('default_interval_seconds', 0)}")
        lines.append(f"  default_host         : {item.get('default_host') or '-'}")
        lines.append(f"  default_port         : {item.get('default_port') or '-'}")
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


def build_worker_view(data: dict[str, Any]) -> str:
    runtime = data.get("runtime", {})
    lines = [
        "Worker Runtime",
        "",
        "[Summary]",
        f"status             : {runtime.get('status', '-')}",
        f"last_worker_run_at : {runtime.get('last_worker_run_at', '-') or '-'}",
        f"last_worker_status : {runtime.get('last_worker_status', '-') or '-'}",
        f"last_processed     : {runtime.get('last_worker_processed', 0)}",
        f"last_trace_id      : {runtime.get('last_worker_trace_id', '-') or '-'}",
        "",
        "[Operator Note]",
        "- layar ini masih read-only",
        "- action worker loop akan ditambahkan pada wave berikutnya",
    ]
    return "\n".join(lines)


def build_scheduler_view(data: dict[str, Any]) -> str:
    scheduler = data.get("scheduler", {})
    lines = [
        "Scheduler Runtime",
        "",
        "[Summary]",
        f"status              : {scheduler.get('status', '-')}",
        f"last_run_at         : {scheduler.get('last_run_at', '-') or '-'}",
        f"last_status         : {scheduler.get('last_status', '-') or '-'}",
        f"last_cycles         : {scheduler.get('last_cycles', 0)}",
        f"last_processed      : {scheduler.get('last_processed', 0)}",
        f"last_trace_id       : {scheduler.get('last_trace_id', '-') or '-'}",
        f"last_heartbeat_mode : {scheduler.get('last_heartbeat_mode', '-') or '-'}",
        "",
        "[Operator Note]",
        "- layar ini masih read-only",
        "- action scheduler loop akan ditambahkan pada wave berikutnya",
    ]
    return "\n".join(lines)


def build_startup_view(data: dict[str, Any]) -> str:
    snapshot = data.get("startup", {})
    documents = snapshot.get("documents", [])
    lines = [
        "Startup Documents",
        "",
        "[Summary]",
        f"session_mode        : {snapshot.get('session_mode', '-')}",
        f"agent_scope         : {snapshot.get('agent_scope', '-')}",
        f"scope_declared      : {'yes' if snapshot.get('scope_declared', True) else 'no'}",
        f"request_roles       : {', '.join(snapshot.get('request_roles', [])) or '-'}",
    ]
    lines.extend(["", "[Documents]"])
    if documents:
        for item in documents:
            lines.append(
                f"- {item.get('name', '-')}: {item.get('availability', '-')} ({item.get('path', '-')})"
            )
    else:
        lines.append("- belum ada startup document")
    lines.extend(
        [
            "",
            "[Daily Notes]",
            snapshot.get("daily_notes") or "- belum ada daily notes",
            "",
            "[Curated Memory]",
            snapshot.get("curated_memory") or "- belum ada curated memory",
        ]
    )
    return "\n".join(lines)


def build_jobs_view(data: dict[str, Any]) -> str:
    summary = data.get("jobs", {})
    lines = [
        "Runtime Jobs",
        "",
        "[Summary]",
        f"total_jobs        : {summary.get('total_jobs', 0)}",
        f"queued_jobs       : {summary.get('queued_jobs', 0)}",
        f"leased_jobs       : {summary.get('leased_jobs', 0)}",
        f"done_jobs         : {summary.get('done_jobs', 0)}",
        f"failed_jobs       : {summary.get('failed_jobs', 0)}",
        f"requeued_jobs     : {summary.get('requeued_jobs', 0)}",
        f"last_worker_run   : {summary.get('last_worker_run_at', '-') or '-'}",
        f"last_worker_state : {summary.get('last_worker_status', '-') or '-'}",
        f"last_processed    : {summary.get('last_worker_processed', 0)}",
    ]
    return "\n".join(lines)


def build_metrics_view(data: dict[str, Any]) -> str:
    metrics = data.get("metrics", {})
    summary = metrics.get("summary", {})
    queue_depth = metrics.get("queue_depth", {})
    provider_latency = metrics.get("provider_latency", {})
    lines = [
        "Execution Metrics",
        "",
        "[Summary]",
        f"events_total      : {summary.get('events_total', 0)}",
        f"commands_total    : {summary.get('commands_total', 0)}",
        f"routes_total      : {summary.get('routes_total', 0)}",
        f"heuristic_routes  : {summary.get('heuristic_routes_total', 0)}",
        f"ai_routes         : {summary.get('ai_routes_total', 0)}",
        f"errors_total      : {summary.get('errors_total', 0)}",
        f"timeouts_total    : {summary.get('timeouts_total', 0)}",
        f"ai_requests_total : {summary.get('ai_requests_total', 0)}",
        f"ai_total_tokens   : {summary.get('ai_total_tokens', 0)}",
    ]
    lines.extend(["", "[Queue Depth]"])
    if queue_depth:
        for queue_name, queue_snapshot in sorted(queue_depth.items()):
            lines.append(
                f"- {queue_name}: current={queue_snapshot.get('current_depth', 0)}, "
                f"high_watermark={queue_snapshot.get('high_watermark', 0)}, "
                f"queued={queue_snapshot.get('queued', 0)}, leased={queue_snapshot.get('leased', 0)}"
            )
    else:
        lines.append("- belum ada snapshot queue depth")
    lines.extend(["", "[Provider Latency]"])
    if provider_latency:
        for _, latency in sorted(provider_latency.items()):
            lines.append(
                f"- {latency.get('provider') or '-'} / {latency.get('model') or '-'}: "
                f"avg_ms={latency.get('avg_ms', 0)}, max_ms={latency.get('max_ms', 0)}, last_ms={latency.get('last_ms', 0)}"
            )
    else:
        lines.append("- belum ada snapshot provider latency")
    return "\n".join(lines)


def build_history_view(data: dict[str, Any]) -> str:
    events = data.get("history", [])
    lines = [
        "Execution History",
        "",
        "[Summary]",
        f"returned_events   : {len(events)}",
    ]
    lines.extend(["", "[Events]"])
    if not events:
        lines.append("- belum ada execution history")
        return "\n".join(lines)
    for event in events:
        lines.append(
            f"- {event.get('timestamp')} {event.get('event_type')} "
            f"[trace={event.get('trace_id') or '-'}, status={event.get('status') or '-'}]"
        )
    return "\n".join(lines)


def build_events_view(data: dict[str, Any]) -> str:
    snapshot = data.get("events", {})
    topics = snapshot.get("topics", {})
    events = snapshot.get("events", [])
    lines = [
        "Internal Event Bus",
        "",
        "[Summary]",
        f"total_events      : {snapshot.get('total_events', 0)}",
        f"returned_events   : {snapshot.get('returned_events', 0)}",
        f"automation_events : {snapshot.get('automation_event_count', 0)}",
        f"policy_events     : {snapshot.get('policy_event_count', 0)}",
        f"external_events   : {snapshot.get('external_event_count', 0)}",
        f"last_event_topic  : {snapshot.get('last_event_topic', '-') or '-'}",
    ]
    lines.extend(["", "[Topics]"])
    if topics:
        for topic, count in sorted(topics.items()):
            lines.append(f"- {topic}: {count}")
    else:
        lines.append("- belum ada topic")
    lines.extend(["", "[Recent Events]"])
    if not events:
        lines.append("- belum ada event bus entry")
        return "\n".join(lines)
    for event in events[-10:]:
        lines.append(
            f"- {event.get('timestamp')} {event.get('topic')}::{event.get('event_type')} "
            f"[trace={event.get('trace_id') or '-'}]"
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
                f"- workspace_root_draft   : {draft.get('workspace_root') or workspace.get('root', '-')}",
                f"- workspace_access       : {workspace.get('access', '-')}",
                f"- workspace_access_draft : {draft.get('workspace_access') or workspace.get('access', '-')}",
                f"- root_exists            : {'yes' if workspace.get('root_exists') else 'no'}",
                "- setup global           : yes",
                "- mutable via wizard     : root, access mode, runtime docs bootstrap",
                "- quick action           : tekan i untuk edit root, a untuk toggle access, s untuk save",
            ]
        )
    elif step_key == "telegram":
        lines.extend(
            [
                "[Telegram]",
                f"- enabled                : {'yes' if telegram.get('enabled') else 'no'}",
                f"- dm_policy              : {telegram.get('dm_policy', '-')}",
                f"- dm_policy_draft        : {draft.get('telegram_dm_policy') or telegram.get('dm_policy', '-')}",
                f"- group_policy           : {telegram.get('group_policy', '-')}",
                f"- require_mention_draft  : {draft.get('telegram_require_mention') or '-'}",
                "- setup global           : yes",
                "- mutable via wizard     : token, owner IDs, DM/group policy, mention requirement",
                "- service integration    : ikut service `cadiax`, bukan target utama terpisah",
                "- quick action           : tekan t untuk toggle enabled, e/a untuk policy/mention, s untuk save",
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
                f"- port_draft             : {draft.get('dashboard_port') or dashboard.get('port', '-')}",
                f"- admin_api_url          : {dashboard.get('admin_api_url', '-')}",
                f"- admin_api_url_draft    : {draft.get('dashboard_admin_api_url') or dashboard.get('admin_api_url', '-')}",
                "- setup global           : yes",
                "- mutable via wizard     : enable/disable, access mode, port, admin API URL",
                "- quick action           : tekan d untuk toggle enabled, e/a untuk access/port, i untuk edit admin API URL, s untuk save",
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
                "- `cadiax setup` sekarang membuka TUI setup sebagai jalur konfigurasi utama",
                "- `cadiax setup --classic` tetap tersedia untuk wizard prompt lama",
            ]
        )
    return "\n".join(lines)


def run_tui(*, initial_screen: str = "home") -> None:
    """Start the Cadiax Textual app."""
    CadiaxTuiApp(initial_screen=initial_screen).run()


class SetupInputScreen(ModalScreen[tuple[str, str] | None]):
    """Simple modal input for editable setup fields."""

    CSS = """
    SetupInputScreen {
        align: center middle;
    }

    #setup-input-dialog {
        width: 80;
        height: auto;
        border: round $accent;
        padding: 1 2;
        background: $surface;
    }

    #setup-input-value {
        margin-top: 1;
    }
    """

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, *, title: str, field_name: str, value: str) -> None:
        super().__init__()
        self.title = title
        self.field_name = field_name
        self.value = value

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="setup-input-dialog"):
            yield Static(self.title)
            yield Static("Tekan Enter untuk simpan atau Esc untuk batal.")
            yield Input(value=self.value, id="setup-input-value")

    def on_mount(self) -> None:
        self.query_one("#setup-input-value", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss((self.field_name, event.value))

    def action_cancel(self) -> None:
        self.dismiss(None)
