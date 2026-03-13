"""Standalone subprocess runner for workspace-managed external skills."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import importlib.util
import inspect
import io
import json
import os
from pathlib import Path
import sys
from typing import Any


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one external skill handler in an isolated subprocess.")
    parser.add_argument("--handler", required=True, help="Path to script/handler.py")
    parser.add_argument("--skill-dir", required=True, help="Path to the external skill directory")
    parser.add_argument("--args", default="", help="Arguments passed to the handler")
    return parser


def _load_module(handler_path: Path):
    module_name = f"external_skill_{abs(hash(str(handler_path.resolve())))}"
    spec = importlib.util.spec_from_file_location(module_name, handler_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Tidak bisa memuat handler dari {handler_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_handle(handle: Any, args: str) -> Any:
    result = handle(args)
    if inspect.isawaitable(result):
        return asyncio.run(result)
    return result


def _normalize_result(result: Any) -> Any:
    if result is None or isinstance(result, (str, int, float, bool, list, dict)):
        return result
    return str(result)


def main() -> int:
    parsed = _build_parser().parse_args()
    handler_path = Path(parsed.handler).resolve()
    skill_dir = Path(parsed.skill_dir).resolve()
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()

    try:
        sys.path.insert(0, str(skill_dir))
        sys.path.insert(0, str(handler_path.parent))
        module = _load_module(handler_path)
        handle = getattr(module, "handle", None)
        if not callable(handle):
            raise RuntimeError("Handler eksternal tidak memiliki fungsi handle(args).")

        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            result = _run_handle(handle, parsed.args)

        payload = {
            "ok": True,
            "result": _normalize_result(result),
            "stdout": stdout_buffer.getvalue(),
            "stderr": stderr_buffer.getvalue(),
            "pid": os.getpid(),
        }
        print(json.dumps(payload, ensure_ascii=True))
        return 0
    except Exception as exc:
        payload = {
            "ok": False,
            "error": str(exc),
            "stdout": stdout_buffer.getvalue(),
            "stderr": stderr_buffer.getvalue(),
            "pid": os.getpid(),
        }
        print(json.dumps(payload, ensure_ascii=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
