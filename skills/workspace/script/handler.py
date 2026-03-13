"""Workspace skill handler."""

from __future__ import annotations

import re
from pathlib import Path

from otonomassist.core.result_builder import build_result
from otonomassist.core.workspace_guard import get_workspace_root, resolve_workspace_path, should_skip_path
MAX_LINES = 80


def _project_root() -> Path:
    """Return the effective workspace root at call time."""
    return get_workspace_root()


def handle(args: str) -> str:
    """Inspect the local workspace."""
    args = args.strip()
    if not args:
        return _usage()

    inferred = _infer_natural_language(args)
    if inferred:
        args = inferred

    command, _, remainder = args.partition(" ")
    command = command.lower().strip()
    remainder = remainder.strip()

    if command == "tree":
        return _tree(remainder or ".")
    if command == "read":
        return _read_file(remainder)
    if command == "find":
        return _find_text(remainder)
    if command == "files":
        return _list_files(remainder or "*")
    if command == "summary":
        return _summary(remainder or ".")

    return _usage()


def _usage() -> str:
    return (
        "Usage: workspace <tree|read|find|files|summary> ...\n"
        "Examples:\n"
        "- workspace tree src\n"
        "- workspace read README.md\n"
        "- workspace find OPENAI_MODEL"
    )


def _resolve_path(path_text: str) -> Path:
    return resolve_workspace_path(path_text)


def _tree(path_text: str) -> str:
    path_text = _normalize_tree_target(path_text)
    path = _resolve_path(path_text)
    project_root = _project_root()
    if not path.exists():
        return f"Path tidak ditemukan: {path_text}"

    root_label = str(path.relative_to(project_root))
    entries: list[dict[str, str | int]] = []
    if path.is_file():
        entries.append({"name": path.name, "relative_path": root_label, "depth": 0, "kind": "file"})
        return _wrap_result(
            result_type="workspace_tree",
            data={
                "root": root_label,
                "count": 1,
                "items": entries,
                "summary": f"Tree untuk {root_label} berisi 1 item file.",
            },
            default_view="table",
        )

    for item in sorted(path.rglob("*")):
        if should_skip_path(item, path):
            continue
        relative = item.relative_to(path)
        entries.append(
            {
                "name": relative.name,
                "relative_path": str(relative),
                "depth": len(relative.parts) - 1,
                "kind": "dir" if item.is_dir() else "file",
            }
        )
        if len(entries) >= MAX_LINES - 1:
            break
    truncated = len(entries) >= MAX_LINES - 1
    return _wrap_result(
        result_type="workspace_tree",
        data={
            "root": root_label,
            "count": len(entries),
            "truncated": truncated,
            "items": entries,
            "summary": f"Tree untuk {root_label} memuat {len(entries)} item{' (truncated)' if truncated else ''}.",
        },
        default_view="table",
    )


def _read_file(path_text: str) -> str:
    if not path_text:
        return "Workspace read membutuhkan path file."

    path_text = _normalize_read_target(path_text)

    path = _resolve_path(path_text)
    project_root = _project_root()
    if not path.exists() or not path.is_file():
        return f"File tidak ditemukan: {path_text}"

    content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    relative = str(path.relative_to(project_root))
    lines = []
    for index, line in enumerate(content[:MAX_LINES], start=1):
        lines.append({"line": str(index), "text": line})
    return _wrap_result(
        result_type="workspace_read",
        data={
            "path": relative,
            "line_count": len(content),
            "truncated": len(content) > MAX_LINES,
            "content": "\n".join(content[:MAX_LINES]) + ("\n... (truncated)" if len(content) > MAX_LINES else ""),
            "lines": lines,
            "summary": f"File {relative} dibaca, {min(len(content), MAX_LINES)} dari {len(content)} baris ditampilkan.",
        },
        default_view="summary",
    )


def _find_text(query: str) -> str:
    if not query:
        return "Workspace find membutuhkan query."

    project_root = _project_root()
    matches: list[dict[str, str]] = []
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    for file_path in project_root.rglob("*"):
        if not file_path.is_file():
            continue
        if should_skip_path(file_path, project_root):
            continue
        try:
            for line_no, line in enumerate(
                file_path.read_text(encoding="utf-8", errors="replace").splitlines(),
                start=1,
            ):
                if pattern.search(line):
                    matches.append(
                        {
                            "path": str(file_path.relative_to(project_root)),
                            "line": str(line_no),
                            "text": line.strip(),
                        }
                    )
                    if len(matches) >= 20:
                        return _wrap_result(
                            result_type="workspace_find",
                            data={
                                "query": query,
                                "match_count": len(matches),
                                "truncated": True,
                                "matches": matches,
                                "summary": f"Ditemukan minimal {len(matches)} hasil untuk '{query}'.",
                            },
                            default_view="table",
                        )
        except OSError:
            continue

    if not matches:
        return f"Tidak ada hasil untuk '{query}'."
    return _wrap_result(
        result_type="workspace_find",
        data={
            "query": query,
            "match_count": len(matches),
            "truncated": False,
            "matches": matches,
            "summary": f"Ditemukan {len(matches)} hasil untuk '{query}'.",
        },
        default_view="table",
    )


def _list_files(glob_text: str) -> str:
    project_root = _project_root()
    matches: list[dict[str, str]] = []
    for file_path in project_root.rglob(glob_text):
        if should_skip_path(file_path, project_root):
            continue
        matches.append({"path": str(file_path.relative_to(project_root))})
        if len(matches) >= MAX_LINES:
            break

    if not matches:
        return f"Tidak ada file yang cocok untuk pattern '{glob_text}'."
    return _wrap_result(
        result_type="workspace_files",
        data={
            "pattern": glob_text,
            "count": len(matches),
            "truncated": len(matches) >= MAX_LINES,
            "items": matches,
            "summary": f"Ditemukan {len(matches)} file untuk pattern '{glob_text}'.",
        },
        default_view="table",
    )


def _summary(path_text: str) -> str:
    path_text = _normalize_tree_target(path_text)
    path = _resolve_path(path_text)
    project_root = _project_root()
    if not path.exists():
        return f"Path tidak ditemukan: {path_text}"

    if path.is_file():
        relative = str(path.relative_to(project_root))
        return _wrap_result(
            result_type="workspace_summary",
            data={
                "path": relative,
                "kind": "file",
                "size_bytes": path.stat().st_size,
                "summary": f"File {relative} berukuran {path.stat().st_size} bytes.",
            },
            default_view="summary",
        )

    file_count = 0
    dir_count = 0
    for item in path.rglob("*"):
        if should_skip_path(item, path):
            continue
        relative = item.relative_to(path)
        if item.is_dir():
            dir_count += 1
        else:
            file_count += 1

    relative = str(path.relative_to(project_root) if path != project_root else ".")
    return _wrap_result(
        result_type="workspace_summary",
        data={
            "path": relative,
            "kind": "directory",
            "directories": dir_count,
            "files": file_count,
            "summary": f"{relative} memiliki {dir_count} direktori dan {file_count} file.",
        },
        default_view="summary",
    )


def _infer_natural_language(args: str) -> str | None:
    lowered = args.lower().strip()
    if not lowered:
        return None

    if lowered == "tree" or lowered.startswith("tree "):
        return None
    if lowered == "read" or lowered.startswith("read "):
        return None
    if lowered == "find" or lowered.startswith("find "):
        return None
    if lowered == "files" or lowered.startswith("files "):
        return None
    if lowered == "summary" or lowered.startswith("summary "):
        return None

    if any(phrase in lowered for phrase in {"struktur", "tree", "hierarki"}):
        return "tree ."
    if lowered in {"workspace", "repo", "project", "file yang ada", "yang ada"}:
        return "tree ."
    if lowered.startswith("baca ") or lowered.startswith("read "):
        _, _, remainder = args.partition(" ")
        if remainder.strip():
            return f"read {_normalize_read_target(remainder)}"
    if lowered.endswith(".md") or lowered.endswith(".py") or lowered.endswith(".json") or lowered.endswith(".txt"):
        return f"read {_normalize_read_target(args)}"
    if lowered.startswith("cari ") or lowered.startswith("find "):
        _, _, remainder = args.partition(" ")
        if remainder.strip():
            return f"find {remainder.strip()}"
    if "ringkas" in lowered or "summary" in lowered:
        return "summary ."
    return None


def _normalize_tree_target(path_text: str) -> str:
    lowered = path_text.strip().lower()
    if not lowered or lowered in {".", "workspace", "repo", "project"}:
        return "."
    if any(phrase in lowered for phrase in {"file yang ada", "yang ada", "semua file"}):
        return "."
    return path_text.strip()


def _normalize_read_target(path_text: str) -> str:
    text = path_text.strip()
    lowered = text.lower()
    for prefix in ("file ", "berkas ", "dokumen "):
        if lowered.startswith(prefix):
            return text[len(prefix):].strip()
    if lowered.startswith("./"):
        return text[2:]
    return text


def _wrap_result(result_type: str, data: dict[str, object], default_view: str) -> dict[str, object]:
    """Wrap workspace output into the shared structured-result envelope."""
    return build_result(
        result_type,
        data,
        source_skill="workspace",
        default_view=default_view,
    )
