from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

from browser_cookies_windows import find_default_profile, read_hoyolab_tokens_from_profile, taskkill_browser


def mask(v: str) -> str:
    if not v:
        return "(empty)"
    if len(v) <= 8:
        return "*" * len(v)
    return f"{v[:4]}...{v[-4:]}"


def pause_exit(enabled: bool) -> None:
    if not enabled:
        return
    try:
        input("Press Enter to exit...")
    except (EOFError, KeyboardInterrupt):
        pass


def default_user_data_dirs() -> Tuple[Path, Path]:
    lad = Path(os.environ.get("LOCALAPPDATA", ""))
    chrome = lad / "Google" / "Chrome" / "User Data"
    edge = lad / "Microsoft" / "Edge" / "User Data"
    return chrome, edge


def pick_profile_dir(user_data_dir: Path, preferred: Optional[str]) -> Optional[str]:
    if not user_data_dir.exists():
        return None

    if preferred:
        return preferred

    if (user_data_dir / "Default").exists():
        return "Default"

    for p in sorted(user_data_dir.glob("Profile *")):
        if p.is_dir():
            return p.name
    return None


def _load_hoyolab_tokens_from_default_profile(browser: str, profile_directory: Optional[str], kill_browser: bool) -> Dict[str, str]:
    prof = find_default_profile(browser, profile_directory)
    if kill_browser:
        print(f"taskkill: closing {prof.name} to avoid cookie DB lock...")
        taskkill_browser(prof.name)
    return read_hoyolab_tokens_from_profile(prof)


def extract_hoyolab_cookie_values(cookies: list[dict]) -> Dict[str, str]:
    cookie_dict: Dict[str, str] = {}
    for c in cookies:
        domain = str(c.get("domain", ""))
        if "hoyolab.com" in domain:
            name = str(c.get("name", ""))
            value = str(c.get("value", ""))
            cookie_dict[name] = value

    return {
        "LTUID": cookie_dict.get("ltuid_v2", ""),
        "LTOKEN": cookie_dict.get("ltoken_v2", ""),
        "COOKIE_TOKEN_V2": cookie_dict.get("cookie_token_v2", ""),
    }


def run_cookie_grab(
    *,
    url: str,
    browser: str,
    profile_directory: Optional[str],
    use_default_profile: bool,
    headless: bool,
    raw: bool,
    pause: bool,
    kill_browser: bool,
) -> int:
    try:
        if not use_default_profile:
            print("ERROR: --no-default-profile is no longer supported in this build (offline cookie read).")
            pause_exit(pause)
            return 1

        if headless:
            print("Note: headless is ignored (offline cookie read).")

        print("== HoYoLAB cookie grabber (offline) ==")
        print(f"target url (for reference): {url}")

        values = _load_hoyolab_tokens_from_default_profile(browser, profile_directory, kill_browser)

        print("\nCookie values:")
        for k in ["LTUID", "LTOKEN", "COOKIE_TOKEN_V2"]:
            v = values.get(k, "")
            print(f"- {k}: {v if raw else mask(v)}")
        print("\nNOTE: This tool does not save secrets to disk; it only prints them.")
        pause_exit(pause)
        return 0
    except Exception as e:
        print(f"\nERROR: {e}")
        pause_exit(pause)
        return 1
