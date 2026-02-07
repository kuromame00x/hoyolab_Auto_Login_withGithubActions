from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions


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


def exe_dir() -> Path:
    try:
        return Path(sys.executable).resolve().parent
    except Exception:
        return Path.cwd()


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


def build_driver(browser: str, user_data_dir: Optional[Path], profile_dir: Optional[str], headless: bool):
    b = browser.lower()
    if b == "edge":
        opts = EdgeOptions()
        if headless:
            opts.add_argument("--headless=new")
        if user_data_dir and profile_dir:
            opts.add_argument(f"--user-data-dir={str(user_data_dir)}")
            opts.add_argument(f"--profile-directory={profile_dir}")
        return webdriver.Edge(options=opts)

    opts = ChromeOptions()
    if headless:
        opts.add_argument("--headless=new")
    if user_data_dir and profile_dir:
        opts.add_argument(f"--user-data-dir={str(user_data_dir)}")
        opts.add_argument(f"--profile-directory={profile_dir}")
    return webdriver.Chrome(options=opts)


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


def write_env(env_path: Path, kv: Dict[str, str]) -> None:
    lines = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines(True)

    def upsert(key: str, value: str) -> None:
        nonlocal lines
        prefix = f"{key}="
        for i, line in enumerate(lines):
            if line.startswith(prefix):
                lines[i] = f"{key}={value}\n"
                return
        lines.append(f"{key}={value}\n")

    for k, v in kv.items():
        if v:
            upsert(k, v)

    env_path.write_text("".join(lines), encoding="utf-8")


def run_cookie_grab(
    *,
    url: str,
    browser: str,
    profile_directory: Optional[str],
    use_default_profile: bool,
    headless: bool,
    raw: bool,
    pause: bool,
) -> int:
    chrome_ud, edge_ud = default_user_data_dirs()

    user_data_dir: Optional[Path] = None
    profile_dir: Optional[str] = None
    b = browser

    if use_default_profile:
        if b in ("auto", "edge") and edge_ud.exists():
            b = "edge"
            user_data_dir = edge_ud
        elif b in ("auto", "chrome") and chrome_ud.exists():
            b = "chrome"
            user_data_dir = chrome_ud
        else:
            b = "edge" if b == "auto" else b

        if user_data_dir:
            profile_dir = pick_profile_dir(user_data_dir, profile_directory)

    print("== HoYoLAB cookie grabber ==")
    print(f"browser: {b}")
    if user_data_dir and profile_dir:
        print(f"user-data-dir: {user_data_dir}")
        print(f"profile-directory: {profile_dir}")
        print("Note: If the browser is already running, profile may be locked. Close all Chrome/Edge and retry.")
    else:
        print("profile: (temporary session)")

    driver = None
    try:
        driver = build_driver(b, user_data_dir, profile_dir, headless)
        driver.get(url)
        print(f"Opened: {url}")
        if not headless:
            print("If you are not logged in, please login in the opened browser window.")
            input("After the page is ready, press Enter to read cookies...")

        values = extract_hoyolab_cookie_values(driver.get_cookies())

        print("\nCookie values:")
        for k in ["LTUID", "LTOKEN", "COOKIE_TOKEN_V2"]:
            v = values.get(k, "")
            print(f"- {k}: {v if raw else mask(v)}")

        out_dir = exe_dir()
        env_path = out_dir / ".env"
        out_txt = out_dir / "secrets_output.txt"
        write_env(env_path, values)
        out_txt.write_text(
            "".join([f"{k}={values.get(k,'')}\n" for k in ["LTUID", "LTOKEN", "COOKIE_TOKEN_V2"]]),
            encoding="utf-8",
        )
        print(f"\nSaved to: {env_path}")
        print(f"Saved to: {out_txt}")
        pause_exit(pause)
        return 0
    except Exception as e:
        print(f"\nERROR: {e}")
        pause_exit(pause)
        return 1
    finally:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass

