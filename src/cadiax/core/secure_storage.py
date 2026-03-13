"""Cross-platform local secret encryption helpers."""

from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import hashlib
import hmac
import os
from pathlib import Path
import secrets


PROJECT_ROOT = Path(__file__).resolve().parents[3]
STATE_DIR = Path(os.getenv("OTONOMASSIST_STATE_DIR", str(PROJECT_ROOT / ".cadiax"))).expanduser().resolve()
PORTABLE_KEY_FILE = STATE_DIR / "portable_secrets.key"
_CRYPTPROTECT_UI_FORBIDDEN = 0x01


class DATA_BLOB(ctypes.Structure):
    """Windows DATA_BLOB structure."""

    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


def encrypt_secret(value: str) -> str:
    """Encrypt a secret for local storage."""
    if os.name == "nt":
        return "win-dpapi:" + _encrypt_windows(value)
    return "portable-v1:" + _encrypt_portable(value)


def decrypt_secret(payload: str) -> str:
    """Decrypt a locally stored secret."""
    if payload.startswith("win-dpapi:"):
        return _decrypt_windows(payload.split(":", 1)[1])
    if payload.startswith("portable-v1:"):
        return _decrypt_portable(payload.split(":", 1)[1])
    if os.name == "nt":
        return _decrypt_windows(payload)
    return _decrypt_portable(payload)


def get_secret_storage_info() -> dict[str, str]:
    """Return backend information for status/doctor reporting."""
    if os.name == "nt":
        return {
            "backend": "windows-dpapi",
            "platform": os.name,
            "status": "healthy",
            "detail": "DPAPI user-scoped encryption aktif.",
        }
    key_exists = PORTABLE_KEY_FILE.exists()
    return {
        "backend": "portable-file-key",
        "platform": os.name,
        "status": "healthy" if key_exists else "warning",
        "detail": (
            f"Portable encrypted file key di {PORTABLE_KEY_FILE}"
            if key_exists
            else f"Portable key akan dibuat saat secret pertama disimpan di {PORTABLE_KEY_FILE}"
        ),
    }


def _encrypt_windows(value: str) -> str:
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


def _decrypt_windows(payload: str) -> str:
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


def _encrypt_portable(value: str) -> str:
    key = _load_or_create_portable_key()
    nonce = secrets.token_bytes(16)
    raw = value.encode("utf-8")
    ciphertext = _xor_with_keystream(raw, key, nonce)
    tag = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
    return base64.b64encode(nonce + tag + ciphertext).decode("ascii")


def _decrypt_portable(payload: str) -> str:
    key = _load_or_create_portable_key()
    blob = base64.b64decode(payload.encode("ascii"))
    if len(blob) < 48:
        raise ValueError("Portable secret payload tidak valid.")
    nonce = blob[:16]
    tag = blob[16:48]
    ciphertext = blob[48:]
    expected_tag = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected_tag):
        raise ValueError("Portable secret payload gagal diverifikasi.")
    raw = _xor_with_keystream(ciphertext, key, nonce)
    return raw.decode("utf-8")


def _xor_with_keystream(data: bytes, key: bytes, nonce: bytes) -> bytes:
    stream = bytearray()
    counter = 0
    while len(stream) < len(data):
        block = hmac.new(key, nonce + counter.to_bytes(8, "big"), hashlib.sha256).digest()
        stream.extend(block)
        counter += 1
    return bytes(a ^ b for a, b in zip(data, stream[: len(data)]))


def _load_or_create_portable_key() -> bytes:
    PORTABLE_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if PORTABLE_KEY_FILE.exists():
        return base64.b64decode(PORTABLE_KEY_FILE.read_text(encoding="utf-8").strip().encode("ascii"))
    key = secrets.token_bytes(32)
    PORTABLE_KEY_FILE.write_text(base64.b64encode(key).decode("ascii"), encoding="utf-8")
    try:
        os.chmod(PORTABLE_KEY_FILE, 0o600)
    except OSError:
        pass
    return key


def _to_blob(raw: bytes) -> DATA_BLOB:
    """Convert bytes to DATA_BLOB."""
    buffer = ctypes.create_string_buffer(raw, len(raw))
    return DATA_BLOB(len(raw), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
