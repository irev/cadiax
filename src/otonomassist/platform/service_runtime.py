"""Cross-platform service runtime helpers and wrapper generation."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time
from typing import Any, Literal

from otonomassist.core.execution_history import append_execution_event, new_trace_id
from otonomassist.core.execution_metrics import record_execution_metric
from otonomassist.core.job_runtime import process_job_queue
from otonomassist.core.scheduler_runtime import run_scheduler
from otonomassist.platform.dashboard_runtime import DEFAULT_DASHBOARD_HOST, DEFAULT_DASHBOARD_PORT, run_dashboard_service


PROJECT_ROOT = Path(__file__).resolve().parents[3]
STATE_ROOT = Path(
    os.getenv("OTONOMASSIST_STATE_DIR", str(PROJECT_ROOT / ".otonomassist"))
).expanduser().resolve()
SERVICE_WRAPPER_DIR = (STATE_ROOT / "service-wrappers").resolve()
ServiceRuntimeName = Literal["windows", "posix"]
SERVICE_TARGETS = ("worker", "scheduler", "admin-api", "conversation-api", "dashboard")


@dataclass(slots=True)
class ServiceArtifact:
    """One generated service wrapper artifact."""

    filename: str
    content: str
    kind: str


@dataclass(slots=True)
class ServiceTargetSpec:
    """Configuration for one runnable service target."""

    name: str
    description: str
    default_interval_seconds: float
    default_steps: int
    default_host: str | None = None
    default_port: int | None = None
    default_enqueue_first: bool = True
    default_until_idle: bool = True


def get_service_runtime_info() -> dict[str, object]:
    """Describe the current service-runtime capability for this OS."""
    runtime = _resolve_runtime_name()
    backend = "windows-runtime" if runtime == "windows" else "posix-runtime"
    return {
        "backend": backend,
        "supervisor_ready": True,
        "recommended_mode": "generated-service-wrapper",
        "status": "healthy",
        "detail": (
            "Service wrapper generator tersedia untuk worker, scheduler, "
            "admin API, conversation API, dan monitoring dashboard."
        ),
        "wrapper_output_dir": str(get_service_wrapper_output_dir()),
        "supported_targets": list_service_targets(),
    }


def list_service_targets() -> list[dict[str, object]]:
    """List supported long-running service targets."""
    return [
        {
            "name": spec.name,
            "description": spec.description,
            "default_interval_seconds": spec.default_interval_seconds,
            "default_steps": spec.default_steps,
            "default_host": spec.default_host,
            "default_port": spec.default_port,
        }
        for spec in _service_specs().values()
    ]


def render_service_runtime_status() -> str:
    """Render service runtime readiness and supported targets."""
    info = get_service_runtime_info()
    lines = [
        "Service Runtime",
        "",
        "[Summary]",
        f"- backend: {info['backend']}",
        f"- status: {info['status']}",
        f"- supervisor_ready: {'yes' if info['supervisor_ready'] else 'no'}",
        f"- recommended_mode: {info['recommended_mode']}",
        f"- wrapper_output_dir: {info['wrapper_output_dir']}",
        f"- detail: {info['detail']}",
        "",
        "[Targets]",
    ]
    for item in info["supported_targets"]:
        line = f"- {item['name']}: {item['description']}"
        if item["default_port"] is not None:
            line += f" (port={item['default_port']})"
        elif item["default_interval_seconds"] > 0:
            line += f" (interval={item['default_interval_seconds']:.0f}s)"
        lines.append(line)
    return "\n".join(lines)


def render_service_wrapper_artifacts(
    target: str,
    *,
    runtime: Literal["auto", "windows", "posix", "all"] = "auto",
    skills_dir: Path | None = None,
) -> str:
    """Render one target's service wrapper artifacts as text."""
    artifacts = build_service_wrapper_artifacts(target, runtime=runtime, skills_dir=skills_dir)
    lines = [f"Service Wrapper Artifacts: {target}"]
    for artifact in artifacts:
        lines.extend(["", f"[{artifact.filename}]", artifact.content])
    return "\n".join(lines)


def write_service_wrapper_artifacts(
    *,
    target: str | None = None,
    output_dir: Path | None = None,
    runtime: Literal["auto", "windows", "posix", "all"] = "auto",
    skills_dir: Path | None = None,
) -> list[Path]:
    """Write generated service wrapper files to disk."""
    root = (output_dir or get_service_wrapper_output_dir()).resolve()
    root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    targets = [target] if target else list(SERVICE_TARGETS)
    for name in targets:
        for artifact in build_service_wrapper_artifacts(name, runtime=runtime, skills_dir=skills_dir):
            path = root / artifact.filename
            path.write_text(artifact.content, encoding="utf-8")
            written.append(path)
    return written


def build_service_wrapper_artifacts(
    target: str,
    *,
    runtime: Literal["auto", "windows", "posix", "all"] = "auto",
    skills_dir: Path | None = None,
) -> list[ServiceArtifact]:
    """Build generated wrapper artifacts for one service target."""
    spec = _get_service_spec(target)
    skills_dir = (skills_dir or Path("skills")).resolve()
    runtimes = _expand_runtime(runtime)
    artifacts: list[ServiceArtifact] = []
    for runtime_name in runtimes:
        args = _build_service_run_args(spec, skills_dir)
        if runtime_name == "posix":
            artifacts.extend(_build_posix_artifacts(spec, args))
        else:
            artifacts.extend(_build_windows_artifacts(spec, args))
    return artifacts


def get_service_wrapper_output_dir() -> Path:
    """Return the default output directory for generated wrappers."""
    return SERVICE_WRAPPER_DIR


def run_worker_service(
    *,
    skills_dir: Path,
    interval_seconds: float = 5.0,
    steps: int = 5,
    enqueue_first: bool = True,
    until_idle: bool = True,
    max_loops: int = 0,
) -> dict[str, Any]:
    """Run the worker as a foreground service loop."""
    from otonomassist.core.assistant import Assistant

    service_trace_id = new_trace_id()
    service_started = time.perf_counter()
    assistant = Assistant(skills_dir=skills_dir)
    assistant.initialize()
    loops = 0
    total_processed = 0
    lines = [
        (
            f"Worker service loop starting "
            f"(interval={max(0.0, interval_seconds):.2f}s, steps={max(1, steps)}, "
            f"until_idle={'yes' if until_idle else 'no'}, enqueue_first={'yes' if enqueue_first else 'no'}):"
        )
    ]
    append_execution_event(
        "service_run_started",
        trace_id=service_trace_id,
        status="started",
        source="worker-service",
        command="service run worker",
        data={
            "interval_seconds": max(0.0, interval_seconds),
            "steps": max(1, steps),
            "max_loops": max(0, max_loops),
        },
    )
    try:
        while max_loops <= 0 or loops < max_loops:
            loops += 1
            loop_trace_id = new_trace_id()
            loop_started = time.perf_counter()
            append_execution_event(
                "service_cycle_started",
                trace_id=loop_trace_id,
                status="started",
                source="worker-service",
                command="service run worker",
                data={
                    "parent_trace_id": service_trace_id,
                    "target": "worker",
                    "loop_index": loops,
                },
            )
            result = process_job_queue(
                assistant,
                max_jobs=max(1, steps),
                enqueue_first=enqueue_first,
                until_idle=until_idle,
                trace_id=loop_trace_id,
                source="worker-service",
                cycle_label=f"worker-service-loop-{loops}",
            )
            total_processed += int(result["processed"])
            lines.append(
                f"- loop {loops}: processed={result['processed']} status={'idle' if result['idle'] else 'active'}"
            )
            loop_status = "idle" if result["idle"] else "active"
            loop_duration_ms = int((time.perf_counter() - loop_started) * 1000)
            append_execution_event(
                "service_cycle_completed",
                trace_id=loop_trace_id,
                status=loop_status,
                source="worker-service",
                command="service run worker",
                duration_ms=loop_duration_ms,
                data={
                    "parent_trace_id": service_trace_id,
                    "target": "worker",
                    "loop_index": loops,
                    "processed": int(result["processed"]),
                },
            )
            record_execution_metric(
                "service_cycle_completed",
                status=loop_status,
                source="worker-service",
                duration_ms=loop_duration_ms,
            )
            if max_loops > 0 and loops >= max_loops:
                break
            time.sleep(max(0.0, interval_seconds))
    except KeyboardInterrupt:
        lines.append("- signal: stopped by operator")
    total_duration_ms = int((time.perf_counter() - service_started) * 1000)
    append_execution_event(
        "service_run_completed",
        trace_id=service_trace_id,
        status="completed",
        source="worker-service",
        command="service run worker",
        duration_ms=total_duration_ms,
        data={
            "target": "worker",
            "total_loops": loops,
            "total_processed": total_processed,
        },
    )
    record_execution_metric(
        "service_run_completed",
        status="completed",
        source="worker-service",
        duration_ms=total_duration_ms,
    )
    lines.append(f"- total_loops: {loops}")
    lines.append(f"- total_processed: {total_processed}")
    return {
        "loops": loops,
        "processed": total_processed,
        "trace_id": service_trace_id,
        "output": "\n".join(lines),
    }


def run_scheduler_service(
    *,
    skills_dir: Path,
    interval_seconds: float = 60.0,
    steps: int = 5,
    enqueue_first: bool = True,
    until_idle: bool = True,
    max_loops: int = 0,
) -> dict[str, Any]:
    """Run the scheduler as a foreground service loop."""
    from otonomassist.core.assistant import Assistant

    service_trace_id = new_trace_id()
    service_started = time.perf_counter()
    assistant = Assistant(skills_dir=skills_dir)
    assistant.initialize()
    loops = 0
    total_processed = 0
    lines = [
        (
            f"Scheduler service loop starting "
            f"(interval={max(0.0, interval_seconds):.2f}s, steps={max(1, steps)}, "
            f"until_idle={'yes' if until_idle else 'no'}, enqueue_first={'yes' if enqueue_first else 'no'}):"
        )
    ]
    append_execution_event(
        "service_run_started",
        trace_id=service_trace_id,
        status="started",
        source="scheduler-service",
        command="service run scheduler",
        data={
            "interval_seconds": max(0.0, interval_seconds),
            "steps": max(1, steps),
            "max_loops": max(0, max_loops),
        },
    )
    try:
        while max_loops <= 0 or loops < max_loops:
            loops += 1
            loop_trace_id = new_trace_id()
            loop_started = time.perf_counter()
            append_execution_event(
                "service_cycle_started",
                trace_id=loop_trace_id,
                status="started",
                source="scheduler-service",
                command="service run scheduler",
                data={
                    "parent_trace_id": service_trace_id,
                    "target": "scheduler",
                    "loop_index": loops,
                },
            )
            result = run_scheduler(
                assistant,
                cycles=1,
                interval_seconds=0.0,
                max_jobs_per_cycle=max(1, steps),
                enqueue_first=enqueue_first,
                until_idle=until_idle,
                trace_id=loop_trace_id,
                source="scheduler-service",
            )
            total_processed += int(result["processed"])
            lines.append(
                f"- loop {loops}: processed={result['processed']} status={result['status']}"
            )
            loop_duration_ms = int((time.perf_counter() - loop_started) * 1000)
            append_execution_event(
                "service_cycle_completed",
                trace_id=loop_trace_id,
                status=str(result["status"]),
                source="scheduler-service",
                command="service run scheduler",
                duration_ms=loop_duration_ms,
                data={
                    "parent_trace_id": service_trace_id,
                    "target": "scheduler",
                    "loop_index": loops,
                    "processed": int(result["processed"]),
                },
            )
            record_execution_metric(
                "service_cycle_completed",
                status=str(result["status"]),
                source="scheduler-service",
                duration_ms=loop_duration_ms,
            )
            if max_loops > 0 and loops >= max_loops:
                break
            time.sleep(max(0.0, interval_seconds))
    except KeyboardInterrupt:
        lines.append("- signal: stopped by operator")
    total_duration_ms = int((time.perf_counter() - service_started) * 1000)
    append_execution_event(
        "service_run_completed",
        trace_id=service_trace_id,
        status="completed",
        source="scheduler-service",
        command="service run scheduler",
        duration_ms=total_duration_ms,
        data={
            "target": "scheduler",
            "total_loops": loops,
            "total_processed": total_processed,
        },
    )
    record_execution_metric(
        "service_run_completed",
        status="completed",
        source="scheduler-service",
        duration_ms=total_duration_ms,
    )
    lines.append(f"- total_loops: {loops}")
    lines.append(f"- total_processed: {total_processed}")
    return {
        "loops": loops,
        "processed": total_processed,
        "trace_id": service_trace_id,
        "output": "\n".join(lines),
    }


def run_named_service_target(
    target: str,
    *,
    skills_dir: Path,
    host: str = "127.0.0.1",
    port: int | None = None,
    interval_seconds: float | None = None,
    steps: int | None = None,
    enqueue_first: bool = True,
    until_idle: bool = True,
    max_loops: int = 0,
) -> dict[str, Any] | None:
    """Run one named service target in the foreground."""
    spec = _get_service_spec(target)
    if target == "worker":
        return run_worker_service(
            skills_dir=skills_dir,
            interval_seconds=interval_seconds if interval_seconds is not None else spec.default_interval_seconds,
            steps=steps if steps is not None else spec.default_steps,
            enqueue_first=enqueue_first,
            until_idle=until_idle,
            max_loops=max_loops,
        )
    if target == "scheduler":
        return run_scheduler_service(
            skills_dir=skills_dir,
            interval_seconds=interval_seconds if interval_seconds is not None else spec.default_interval_seconds,
            steps=steps if steps is not None else spec.default_steps,
            enqueue_first=enqueue_first,
            until_idle=until_idle,
            max_loops=max_loops,
        )
    if target == "admin-api":
        from otonomassist.core.admin_api import run_admin_api

        run_admin_api(host=host, port=port or spec.default_port or 8787)
        return None
    if target == "dashboard":
        run_dashboard_service(
            host=host or spec.default_host or DEFAULT_DASHBOARD_HOST,
            port=port or spec.default_port or DEFAULT_DASHBOARD_PORT,
            install_if_missing=True,
            build_if_needed=True,
        )
        return None

    from otonomassist.core.assistant import Assistant
    from otonomassist.services.interactions import ConversationService
    from otonomassist.services.interactions import run_conversation_api

    assistant = Assistant(skills_dir=skills_dir)
    assistant.initialize()
    service = ConversationService(assistant)
    run_conversation_api(service, host=host, port=port or spec.default_port or 8788)
    return None


def _resolve_runtime_name() -> ServiceRuntimeName:
    return "windows" if os.name == "nt" else "posix"


def _expand_runtime(runtime: Literal["auto", "windows", "posix", "all"]) -> tuple[ServiceRuntimeName, ...]:
    if runtime == "all":
        return ("posix", "windows")
    if runtime == "auto":
        return (_resolve_runtime_name(),)
    return (runtime,)


def _service_specs() -> dict[str, ServiceTargetSpec]:
    return {
        "worker": ServiceTargetSpec(
            name="worker",
            description="Background runtime job processor",
            default_interval_seconds=5.0,
            default_steps=5,
        ),
        "scheduler": ServiceTargetSpec(
            name="scheduler",
            description="Autonomous scheduler cycle runner",
            default_interval_seconds=60.0,
            default_steps=5,
        ),
        "admin-api": ServiceTargetSpec(
            name="admin-api",
            description="Read-only operational admin API",
            default_interval_seconds=0.0,
            default_steps=0,
            default_host="127.0.0.1",
            default_port=8787,
        ),
        "conversation-api": ServiceTargetSpec(
            name="conversation-api",
            description="Conversational interaction API",
            default_interval_seconds=0.0,
            default_steps=0,
            default_host="127.0.0.1",
            default_port=8788,
        ),
        "dashboard": ServiceTargetSpec(
            name="dashboard",
            description="Monitoring dashboard web service",
            default_interval_seconds=0.0,
            default_steps=0,
            default_host=DEFAULT_DASHBOARD_HOST,
            default_port=DEFAULT_DASHBOARD_PORT,
        ),
    }


def _get_service_spec(target: str) -> ServiceTargetSpec:
    normalized = target.strip().lower()
    specs = _service_specs()
    if normalized not in specs:
        supported = ", ".join(sorted(specs))
        raise ValueError(f"Unknown service target `{target}`. Supported: {supported}")
    return specs[normalized]


def _build_service_run_args(spec: ServiceTargetSpec, skills_dir: Path) -> list[str]:
    if spec.name == "dashboard":
        args = [
            sys.executable,
            "-m",
            "otonomassist.cli",
            "dashboard",
            "run",
            "--install-if-missing",
            "--build-if-needed",
        ]
        if spec.default_host is not None:
            args.extend(["--host", spec.default_host])
        if spec.default_port is not None:
            args.extend(["--port", str(spec.default_port)])
        return args
    args = [
        sys.executable,
        "-m",
        "otonomassist.cli",
        "service",
        "run",
        spec.name,
    ]
    if spec.name in {"worker", "scheduler", "conversation-api"}:
        args.extend(["--skills-dir", str(skills_dir)])
    if spec.name in {"worker", "scheduler"}:
        args.extend(
            [
                "--interval",
                _format_number(spec.default_interval_seconds),
                "--steps",
                str(spec.default_steps),
                "--max-loops",
                "0",
            ]
        )
        if spec.default_enqueue_first:
            args.append("--enqueue-first")
        if spec.default_until_idle:
            args.append("--until-idle")
    if spec.default_host is not None:
        args.extend(["--host", spec.default_host])
    if spec.default_port is not None:
        args.extend(["--port", str(spec.default_port)])
    return args


def _build_posix_artifacts(spec: ServiceTargetSpec, args: list[str]) -> list[ServiceArtifact]:
    command = shlex.join(args)
    launcher = "\n".join(
        [
            "#!/usr/bin/env sh",
            "set -eu",
            f'cd "{PROJECT_ROOT}"',
            f"exec {command}",
            "",
        ]
    )
    unit = "\n".join(
        [
            "[Unit]",
            f"Description=OtonomAssist {spec.name} service",
            "After=network.target",
            "",
            "[Service]",
            "Type=simple",
            f"WorkingDirectory={PROJECT_ROOT}",
            f"ExecStart={command}",
            "Restart=always",
            "RestartSec=5",
            "Environment=PYTHONUNBUFFERED=1",
            "",
            "[Install]",
            "WantedBy=multi-user.target",
            "",
        ]
    )
    prefix = f"otonomassist-{spec.name}"
    return [
        ServiceArtifact(filename=f"{prefix}.sh", content=launcher, kind="launcher"),
        ServiceArtifact(filename=f"{prefix}.service", content=unit, kind="systemd-unit"),
    ]


def _build_windows_artifacts(spec: ServiceTargetSpec, args: list[str]) -> list[ServiceArtifact]:
    command = subprocess.list2cmdline(args)
    cmd = "\r\n".join(
        [
            "@echo off",
            f'cd /d "{PROJECT_ROOT}"',
            command,
            "",
        ]
    )
    ps_args = _powershell_quote(command)
    install = "\n".join(
        [
            f"$TaskName = 'OtonomAssist-{spec.name}'",
            f"$LauncherCommand = 'cd /d \"{_powershell_quote(str(PROJECT_ROOT), quoted=False)}\" && {ps_args[1:-1]}'",
            "$Action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument \"/c $LauncherCommand\"",
            "$Trigger = New-ScheduledTaskTrigger -AtStartup",
            "$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -RestartCount 999 "
            "-RestartInterval (New-TimeSpan -Minutes 1)",
            "Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger "
            "-Settings $Settings -Description 'OtonomAssist generated service wrapper' -Force",
            "",
        ]
    )
    prefix = f"otonomassist-{spec.name}"
    return [
        ServiceArtifact(filename=f"{prefix}.cmd", content=cmd, kind="launcher"),
        ServiceArtifact(filename=f"{prefix}-install.ps1", content=install, kind="scheduled-task"),
    ]


def _powershell_quote(value: str, *, quoted: bool = True) -> str:
    escaped = value.replace("'", "''")
    return f"'{escaped}'" if quoted else escaped


def _format_number(value: float) -> str:
    if int(value) == value:
        return str(int(value))
    return str(value)
