"""Windows-backed local secret encryption helpers."""

from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import os


class DATA_BLOB(ctypes.Structure):
    """Windows DATA_BLOB structure."""

    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


_CRYPTPROTECT_UI_FORBIDDEN = 0x01


def encrypt_secret(value: str) -> str:
    """Encrypt a secret for local storage."""
    if os.name != "nt":
        raise RuntimeError("Encrypted secret storage saat ini hanya didukung di Windows.")

    raw = value.encode("utf-8")
    in_blob = _to_blob(raw)
    out_blob = DATA_BLOB()

    result = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        _CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(out_blob),
    )
    if not result:
        raise ctypes.WinError()

    try:
        encrypted = ctypes.string_at(out_blob.pbData, out_blob.cbData)
        return base64.b64encode(encrypted).decode("ascii")
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def decrypt_secret(payload: str) -> str:
    """Decrypt a locally stored secret."""
    if os.name != "nt":
        raise RuntimeError("Encrypted secret storage saat ini hanya didukung di Windows.")

    encrypted = base64.b64decode(payload.encode("ascii"))
    in_blob = _to_blob(encrypted)
    out_blob = DATA_BLOB()

    result = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        _CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(out_blob),
    )
    if not result:
        raise ctypes.WinError()

    try:
        decrypted = ctypes.string_at(out_blob.pbData, out_blob.cbData)
        return decrypted.decode("utf-8")
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def _to_blob(raw: bytes) -> DATA_BLOB:
    """Convert bytes to DATA_BLOB."""
    buffer = ctypes.create_string_buffer(raw, len(raw))
    return DATA_BLOB(len(raw), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
