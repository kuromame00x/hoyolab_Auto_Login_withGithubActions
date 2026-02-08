from __future__ import annotations

from typing import Dict, Optional

from browser_cookies_windows import find_default_profile, read_endfield_cred_from_profile, taskkill_browser
from cookie_check_common import mask, pause_exit


def _load_endfield_cred_from_default_profile(browser: str, profile_directory: Optional[str], kill_browser: bool) -> Dict[str, str]:
    prof = find_default_profile(browser, profile_directory)
    if kill_browser:
        print(f"taskkill: closing {prof.name} to avoid cookie DB lock...")
        taskkill_browser(prof.name)
    return read_endfield_cred_from_profile(prof)


def run_endfield_cred_grab(
    *,
    browser: str,
    profile_directory: Optional[str],
    raw: bool,
    pause: bool,
    kill_browser: bool,
) -> int:
    try:
        print("== Endfield (SKPort) cred grabber (offline) ==")
        values = _load_endfield_cred_from_default_profile(browser, profile_directory, kill_browser)

        print("\nCookie values:")
        v = values.get("ENDFIELD_CRED", "")
        print(f"- ENDFIELD_CRED: {v if raw else mask(v)}")
        print("\nNOTE: This tool does not save secrets to disk; it only prints them.")
        if pause:
            pause_exit()
        return 0 if v else 1
    except Exception as e:
        print(f"\nERROR: {e}")
        if pause:
            pause_exit()
        return 1
