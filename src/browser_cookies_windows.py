from __future__ import annotations

import base64
import json
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import time
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

    # v20+ is Chrome/Edge "app-bound" cookie encryption on Windows. This is not decryptable
    # with the legacy Local State "encrypted_key" alone.
    if encrypted_value.startswith(b"v20"):
        raise RuntimeError(
            "Detected v20 (app-bound) cookie encryption. Offline cookie DB decryption is not supported in this tool.\n"
            "Use DevTools-exported HAR mode instead (cookiegrab.exe --source har --har <path> --url <url>)."
        )

    # Old format: DPAPI blob
    try:
        return _dpapi_decrypt(encrypted_value).decode("utf-8", errors="replace")
    except Exception:
        return ""


def _copy_sqlite(src: Path, retries: int = 8, base_delay_s: float = 0.15) -> Path:
    # Copy to temp so we can read even if the browser is running/locking the DB.
    # If the profile is locked hard, this may still fail; callers should surface a helpful message.
    td = Path(tempfile.mkdtemp(prefix="cookie_db_"))
    dst = td / "Cookies"
    try:
        last_exc: Exception | None = None
        for i in range(max(1, retries)):
            try:
                shutil.copy2(src, dst)
                return dst
            except Exception as e:
                last_exc = e
                # Windows sharing violation often clears quickly after the browser closes.
                time.sleep(base_delay_s * (i + 1))
        raise last_exc or RuntimeError("copy failed")
    except Exception:
        try:
            shutil.rmtree(td, ignore_errors=True)
        except Exception:
            pass
        raise


def _list_profile_dirs(user_data_dir: Path) -> list[str]:
    out: list[str] = []
    default = user_data_dir / "Default"
    if default.exists():
        out.append("Default")
    for p in sorted(user_data_dir.glob("Profile *")):
        if p.is_dir():
            out.append(p.name)
    return out


def _cookie_db_path(profile_path: Path) -> Optional[Path]:
    p1 = profile_path / "Network" / "Cookies"
    if p1.exists():
        return p1
    p2 = profile_path / "Cookies"
    if p2.exists():
        return p2
    return None


def list_available_profiles(browser: str) -> list[BrowserProfile]:
    lad = Path(os.environ.get("LOCALAPPDATA", ""))
    if not lad.exists():
        return []

    browser_l = (browser or "auto").lower()
    out: list[BrowserProfile] = []

    def _add(name: str, udd: Path) -> None:
        if not udd.exists():
            return
        for d in _list_profile_dirs(udd):
            out.append(BrowserProfile(name, udd, d))

    if browser_l in ("auto", "edge"):
        _add("edge", lad / "Microsoft" / "Edge" / "User Data")
    if browser_l in ("auto", "chrome"):
        _add("chrome", lad / "Google" / "Chrome" / "User Data")

    return out


def read_cookie_values_from_profile(profile: BrowserProfile, *, host_like: str, names: list[str]) -> dict[str, str]:
    aes_key = _get_chromium_key(profile.user_data_dir)
    cookies_db = _cookie_db_path(profile.profile_path)
    if not cookies_db:
        available = _list_profile_dirs(profile.user_data_dir)
        raise FileNotFoundError(
            f"Cookies DB not found under: {profile.profile_path}\n"
            f"Available profiles under {profile.user_data_dir}: {', '.join(available) if available else '(none)'}"
        )

    placeholders = ",".join(["?"] * len(names))
    copied: Path
    try:
        copied = _copy_sqlite(cookies_db)
    except Exception as e:
        raise RuntimeError(
            "Failed to copy Cookies DB (maybe the browser/profile is locked).\n"
            f"Path: {cookies_db}\n"
            "Close Chrome/Edge and retry, or run with --kill-browser.\n"
            f"Original error: {e}"
        )

    try:
        con = sqlite3.connect(str(copied))
        try:
            cur = con.cursor()
            cur.execute(
                f"""
                SELECT host_key, name, encrypted_value
                FROM cookies
                WHERE host_key LIKE ?
                  AND name IN ({placeholders})
                """,
                [host_like, *names],
            )
            rows = cur.fetchall()
        finally:
            con.close()
    finally:
        try:
            shutil.rmtree(copied.parent, ignore_errors=True)
        except Exception:
            pass

    out: dict[str, str] = {n: "" for n in names}
    for _host, name, ev in rows:
        if name in out:
            out[name] = _decrypt_chromium_cookie(ev, aes_key)
    return out


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
    prof = candidates[0]

    # Validate/fix profile directory selection.
    available = _list_profile_dirs(prof.user_data_dir)
    if prof.profile_dir not in available:
        # Common confusion: UI may show "Profile 1" but the first profile folder is still "Default".
        if prof.profile_dir.strip().lower() == "profile 1" and "Default" in available:
            prof = BrowserProfile(prof.name, prof.user_data_dir, "Default")
        else:
            raise FileNotFoundError(
                f"Profile directory not found: {prof.profile_path}\n"
                f"Available profiles under {prof.user_data_dir}: {', '.join(available) if available else '(none)'}"
            )

    return prof


def read_hoyolab_tokens_from_profile(profile: BrowserProfile) -> dict[str, str]:
    m = read_cookie_values_from_profile(
        profile,
        host_like="%hoyolab.com%",
        names=["ltuid_v2", "ltoken_v2", "cookie_token_v2"],
    )
    return {
        "LTUID": m.get("ltuid_v2", ""),
        "LTOKEN": m.get("ltoken_v2", ""),
        "COOKIE_TOKEN_V2": m.get("cookie_token_v2", ""),
    }


def read_endfield_cred_from_profile(profile: BrowserProfile) -> dict[str, str]:
    # From DevTools screenshot: cookie name SK_OAUTH_CRED_KEY under game.skport.com.
    m = read_cookie_values_from_profile(profile, host_like="%skport.com%", names=["SK_OAUTH_CRED_KEY"])
    return {"ENDFIELD_CRED": m.get("SK_OAUTH_CRED_KEY", "")}


def _local_storage_leveldb_dir(profile_path: Path) -> Optional[Path]:
    p = profile_path / "Local Storage" / "leveldb"
    return p if p.exists() else None


def _scan_leveldb_dir_for_key(leveldb_dir: Path, key_fragment: str) -> Optional[str]:
    # Best-effort "string scrape" from LevelDB files.
    #
    # Chromium stores Local Storage in a LevelDB. We avoid heavy dependencies by scanning for the key string
    # and extracting a nearby numeric value. This works for simple cases like APP_CURRENT_ROLE_GAME_ROLE:endfield.
    key_b = key_fragment.encode("utf-8", errors="ignore")
    # Prefer values that look like large numeric IDs with trailing "::" (as shown in DevTools).
    value_re = re.compile(rb"([0-9]{7,})(::)")

    files = list(leveldb_dir.glob("*.log")) + list(leveldb_dir.glob("*.ldb")) + list(leveldb_dir.glob("*.sst"))
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    for fp in files:
        try:
            data = fp.read_bytes()
        except Exception:
            continue

        # The LevelDB key may include origin/prefix bytes; we search by fragment.
        idx = data.rfind(key_b)
        if idx < 0:
            continue

        # Look around for a plausible numeric value (allow wider window).
        window = data[idx : idx + 4096]
        start = min(len(window), len(key_b))  # local index offset from window start
        # Search only AFTER the key fragment to avoid accidentally picking an earlier numeric field.
        tail = window[start:]
        m = value_re.search(tail)
        if not m:
            continue

        try:
            return m.group(0).decode("utf-8", errors="replace")
        except Exception:
            return None

    return None


def read_endfield_roles_from_profile(profile: BrowserProfile) -> dict[str, str]:
    # From DevTools screenshot (Application -> Local storage https://game.skport.com):
    # - APP_CURRENT_ROLE:endfield -> e.g. "372802296::"
    # - APP_CURRENT_ROLE_GAME_ROLE:endfield -> e.g. "4722345642::"
    ldb = _local_storage_leveldb_dir(profile.profile_path)
    if not ldb:
        return {"ENDFIELD_ROLE_ID": "", "ENDFIELD_GAME_ROLE_ID": ""}

    # Search by fragments (LevelDB key contains origin/prefix bytes).
    role = _scan_leveldb_dir_for_key(ldb, "APP_CURRENT_ROLE:endfield") or _scan_leveldb_dir_for_key(ldb, "APP_CURRENT_ROLE") or ""
    game_role = (
        _scan_leveldb_dir_for_key(ldb, "APP_CURRENT_ROLE_GAME_ROLE:endfield")
        or _scan_leveldb_dir_for_key(ldb, "APP_CURRENT_ROLE_GAME_ROLE")
        or ""
    )

    # Normalize: keep raw too? Caller can decide; we strip trailing :: for convenience.
    def _strip(v: str) -> str:
        return v[:-2] if v.endswith("::") else v

    return {
        "ENDFIELD_ROLE_ID": _strip(role),
        "ENDFIELD_GAME_ROLE_ID": _strip(game_role),
    }


def taskkill_browser(browser_name: str) -> None:
    # Best-effort. This is intentionally forceful to avoid cookie DB locks.
    b = (browser_name or "").lower()
    img = "msedge.exe" if b == "edge" else "chrome.exe"

    def _run(cmd: list[str]) -> tuple[int, str]:
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, check=False)
            out = (p.stdout or "") + (p.stderr or "")
            return int(p.returncode), out.strip()
        except Exception as e:
            return 999, str(e)

    code, out = _run(["taskkill", "/IM", img, "/F", "/T"])
    if code == 0:
        print(f"taskkill ok: {img}")
        time.sleep(0.5)
        return

    # taskkill can fail if process is elevated or already closed.
    if out:
        print(f"taskkill failed ({code}) for {img}: {out}")
    else:
        print(f"taskkill failed ({code}) for {img}")

    # Fallback: PowerShell Stop-Process (sometimes works when taskkill doesn't).
    name_no_ext = img[:-4] if img.lower().endswith(".exe") else img
    code2, out2 = _run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            f"Get-Process -Name {name_no_ext} -ErrorAction SilentlyContinue | Stop-Process -Force",
        ]
    )
    if code2 == 0:
        print(f"Stop-Process ok: {name_no_ext}")
        time.sleep(0.5)
        return
    if out2:
        print(f"Stop-Process failed ({code2}) for {name_no_ext}: {out2}")
