from __future__ import annotations

import base64
import json
import os
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import ctypes
from ctypes import wintypes

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


@dataclass(frozen=True)
class BrowserProfile:
    name: str
    user_data_dir: Path
    profile_dir: str

    @property
    def profile_path(self) -> Path:
        return self.user_data_dir / self.profile_dir


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

CryptUnprotectData = crypt32.CryptUnprotectData
CryptUnprotectData.argtypes = [
    ctypes.POINTER(_DATA_BLOB),
    ctypes.POINTER(ctypes.c_wchar_p),
    ctypes.POINTER(_DATA_BLOB),
    ctypes.c_void_p,
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.POINTER(_DATA_BLOB),
]
CryptUnprotectData.restype = wintypes.BOOL

LocalFree = kernel32.LocalFree
LocalFree.argtypes = [ctypes.c_void_p]
LocalFree.restype = ctypes.c_void_p


def _dpapi_decrypt(encrypted: bytes) -> bytes:
    in_blob = _DATA_BLOB(cbData=len(encrypted), pbData=ctypes.cast(ctypes.create_string_buffer(encrypted), ctypes.POINTER(ctypes.c_byte)))
    out_blob = _DATA_BLOB()
    if not CryptUnprotectData(ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)):
        raise OSError(f"CryptUnprotectData failed: {ctypes.get_last_error()}")
    try:
        out = ctypes.string_at(out_blob.pbData, out_blob.cbData)
        return out
    finally:
        LocalFree(out_blob.pbData)


def _get_chromium_key(user_data_dir: Path) -> bytes:
    local_state = user_data_dir / "Local State"
    if not local_state.exists():
        raise FileNotFoundError(f"Local State not found: {local_state}")
    j = json.loads(local_state.read_text(encoding="utf-8"))
    ek_b64 = j["os_crypt"]["encrypted_key"]
    ek = base64.b64decode(ek_b64)
    # Prefix is "DPAPI"
    if ek.startswith(b"DPAPI"):
        ek = ek[5:]
    return _dpapi_decrypt(ek)


def _decrypt_chromium_cookie(encrypted_value: bytes, aes_key: bytes) -> str:
    if not encrypted_value:
        return ""

    # New format: v10 / v11 + 12 byte nonce + ciphertext+tag
    if encrypted_value.startswith(b"v10") or encrypted_value.startswith(b"v11"):
        nonce = encrypted_value[3:15]
        ct = encrypted_value[15:]
        return AESGCM(aes_key).decrypt(nonce, ct, None).decode("utf-8", errors="replace")

    # Old format: DPAPI blob
    try:
        return _dpapi_decrypt(encrypted_value).decode("utf-8", errors="replace")
    except Exception:
        return ""


def _copy_sqlite(src: Path) -> Path:
    # Copy to temp so we can read even if the browser is running/locking the DB.
    td = Path(tempfile.mkdtemp(prefix="cookie_db_"))
    dst = td / "Cookies"
    shutil.copy2(src, dst)
    return dst


def find_default_profile(browser: str, profile_directory: Optional[str]) -> BrowserProfile:
    lad = Path(os.environ.get("LOCALAPPDATA", ""))
    if not lad.exists():
        raise RuntimeError("LOCALAPPDATA not set; this tool is Windows-only.")

    browser_l = browser.lower()
    candidates: list[BrowserProfile] = []
    if browser_l in ("auto", "edge"):
        udd = lad / "Microsoft" / "Edge" / "User Data"
        if udd.exists():
            candidates.append(BrowserProfile("edge", udd, profile_directory or "Default"))
    if browser_l in ("auto", "chrome"):
        udd = lad / "Google" / "Chrome" / "User Data"
        if udd.exists():
            candidates.append(BrowserProfile("chrome", udd, profile_directory or "Default"))

    if not candidates:
        raise RuntimeError("No Chrome/Edge user data dir found.")

    # Prefer Edge if auto and it exists (most Windows machines).
    return candidates[0]


def read_hoyolab_tokens_from_profile(profile: BrowserProfile) -> dict[str, str]:
    aes_key = _get_chromium_key(profile.user_data_dir)
    cookies_db = profile.profile_path / "Network" / "Cookies"
    if not cookies_db.exists():
        # Older paths sometimes use profile/Cookies
        alt = profile.profile_path / "Cookies"
        if alt.exists():
            cookies_db = alt
        else:
            raise FileNotFoundError(f"Cookies DB not found under: {profile.profile_path}")

    copied = _copy_sqlite(cookies_db)
    try:
        con = sqlite3.connect(str(copied))
        try:
            cur = con.cursor()
            cur.execute(
                """
                SELECT host_key, name, encrypted_value
                FROM cookies
                WHERE host_key LIKE '%hoyolab.com%'
                  AND name IN ('ltuid_v2','ltoken_v2','cookie_token_v2')
                """
            )
            rows = cur.fetchall()
        finally:
            con.close()
    finally:
        # Cleanup temp dir
        try:
            shutil.rmtree(copied.parent, ignore_errors=True)
        except Exception:
            pass

    m: dict[str, str] = {"LTUID": "", "LTOKEN": "", "COOKIE_TOKEN_V2": ""}
    for _host, name, ev in rows:
        val = _decrypt_chromium_cookie(ev, aes_key)
        if name == "ltuid_v2":
            m["LTUID"] = val
        elif name == "ltoken_v2":
            m["LTOKEN"] = val
        elif name == "cookie_token_v2":
            m["COOKIE_TOKEN_V2"] = val
    return m

