"""Notify skill handler."""

from __future__ import annotations

from cadiax.core.result_builder import build_result
from cadiax.services.interactions.notification_dispatcher import NotificationDispatcher


def handle(args: str) -> dict[str, object] | str:
    """Dispatch durable notifications through the shared dispatcher."""
    args = args.strip()
    if not args:
        return _usage()

    command, options, message = _parse_args(args)
    if command == "send":
        return _send_notification(options, message)
    if command == "batch":
        return _send_batch(options, message)
    if command == "history":
        return _show_history(options)
    return _usage()


def _usage() -> str:
    return (
        "Usage: notify <send|batch|history> <message> "
        "[channel=<name>] [title=<text>] [target=<value>] [delivery=<channel:target>]"
    )


def _parse_args(args: str) -> tuple[str, dict[str, object], str]:
    tokens = [token for token in args.split() if token.strip()]
    if not tokens:
        return "", {}, ""
    command = tokens[0].strip().lower()
    options: dict[str, object] = {"deliveries": []}
    message_parts: list[str] = []
    for token in tokens[1:]:
        key, separator, value = token.partition("=")
        if not separator:
            message_parts.append(token)
            continue
        key = key.strip().lower()
        value = value.strip()
        if key == "channel":
            options["channel"] = value or "internal"
        elif key == "title":
            options["title"] = value or "Notification"
        elif key == "target":
            options["target"] = value
        elif key == "delivery" and value:
            channel_name, _, target = value.partition(":")
            if channel_name.strip():
                options["deliveries"].append(
                    {
                        "channel": channel_name.strip(),
                        "target": target.strip(),
                    }
                )
        else:
            message_parts.append(token)
    return command, options, " ".join(message_parts).strip()


def _send_notification(options: dict[str, object], message: str) -> dict[str, object] | str:
    if not message:
        return "Notify send membutuhkan message."
    payload = NotificationDispatcher().dispatch(
        channel=str(options.get("channel") or "internal"),
        title=str(options.get("title") or "Notification"),
        message=message,
        target=str(options.get("target") or ""),
    )
    return build_result(
        "notify_send",
        {
            "summary": (
                f"Notify send: channel={payload['channel']}, "
                f"status={payload['status']}, "
                f"target={payload['target'] or '-'}."
            ),
            "notification": payload,
        },
        source_skill="notify",
        default_view="summary",
        status="ok" if str(payload.get("status") or "") != "deferred" else "deferred",
    )


def _send_batch(options: dict[str, object], message: str) -> dict[str, object] | str:
    if not message:
        return "Notify batch membutuhkan message."
    deliveries = list(options.get("deliveries") or [])
    if not deliveries:
        return "Notify batch membutuhkan minimal satu delivery=<channel:target>."
    payload = NotificationDispatcher().dispatch_many(
        title=str(options.get("title") or "Notification"),
        message=message,
        deliveries=deliveries,
    )
    return build_result(
        "notify_batch",
        {
            "summary": (
                f"Notify batch: delivery_count={payload['delivery_count']}, "
                f"batch_id={payload['batch_id']}."
            ),
            "batch": payload,
        },
        source_skill="notify",
        default_view="summary",
    )


def _show_history(options: dict[str, object]) -> dict[str, object]:
    snapshot = NotificationDispatcher().get_snapshot()
    return build_result(
        "notify_history",
        {
            "summary": (
                f"Notify history: notifications={snapshot['notification_count']}, "
                f"channels={len(snapshot['by_channel'])}, "
                f"batches={snapshot['delivery_batch_count']}."
            ),
            "snapshot": snapshot,
        },
        source_skill="notify",
        default_view="summary",
    )
