import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions

from grab_urls import SKPORT_ENDFIELD_URL


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
    # Enable performance logs (Chromium DevTools Protocol events)
    logging_prefs = {"performance": "ALL"}

    b = browser.lower()
    if b == "edge":
        opts = EdgeOptions()
        if headless:
            opts.add_argument("--headless=new")
        if user_data_dir and profile_dir:
            opts.add_argument(f"--user-data-dir={str(user_data_dir)}")
            opts.add_argument(f"--profile-directory={profile_dir}")
        opts.set_capability("goog:loggingPrefs", logging_prefs)
        d = webdriver.Edge(options=opts)
        return d

    opts = ChromeOptions()
    if headless:
        opts.add_argument("--headless=new")
    if user_data_dir and profile_dir:
        opts.add_argument(f"--user-data-dir={str(user_data_dir)}")
        opts.add_argument(f"--profile-directory={profile_dir}")
    opts.set_capability("goog:loggingPrefs", logging_prefs)
    return webdriver.Chrome(options=opts)


def parse_performance_logs(driver) -> Dict[str, str]:
    # Best-effort extraction of request headers "cred" and "sk-game-role" from network events.
    url_map: Dict[str, str] = {}
    found: Dict[str, str] = {}

    def is_skport(u: str) -> bool:
        return "skport.com" in u or "zonai.skport.com" in u

    for entry in driver.get_log("performance"):
        try:
            msg = json.loads(entry["message"])["message"]
        except Exception:
            continue
        method = msg.get("method")
        params = msg.get("params", {})

        if method == "Network.requestWillBeSent":
            request_id = params.get("requestId")
            req = params.get("request", {})
            url = str(req.get("url", ""))
            if request_id and url:
                url_map[request_id] = url
            headers = req.get("headers", {}) or {}
            lower = {str(k).lower(): str(v) for k, v in headers.items()}
            if is_skport(url):
                if "cred" in lower and "ENDFIELD_CRED" not in found:
                    found["ENDFIELD_CRED"] = lower["cred"]
                if "sk-game-role" in lower and "ENDFIELD_SK_GAME_ROLE" not in found:
                    found["ENDFIELD_SK_GAME_ROLE"] = lower["sk-game-role"]

        if method == "Network.requestWillBeSentExtraInfo":
            request_id = params.get("requestId")
            url = url_map.get(request_id, "")
            headers = params.get("headers", {}) or {}
            lower = {str(k).lower(): str(v) for k, v in headers.items()}
            if is_skport(url):
                if "cred" in lower and "ENDFIELD_CRED" not in found:
                    found["ENDFIELD_CRED"] = lower["cred"]
                if "sk-game-role" in lower and "ENDFIELD_SK_GAME_ROLE" not in found:
                    found["ENDFIELD_SK_GAME_ROLE"] = lower["sk-game-role"]

    return found


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


def main() -> int:
    ap = argparse.ArgumentParser(description="Open Endfield (SKPort) sign-in page and read ENDFIELD_CRED / ENDFIELD_SK_GAME_ROLE from network headers.")
    ap.add_argument("--browser", choices=["auto", "edge", "chrome"], default="auto")
    ap.add_argument("--profile-directory", default=None)
    ap.add_argument("--no-default-profile", action="store_true")
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--raw", action="store_true")
    ap.add_argument("--no-pause", action="store_true")
    args = ap.parse_args()

    chrome_ud, edge_ud = default_user_data_dirs()
    user_data_dir: Optional[Path] = None
    profile_dir: Optional[str] = None
    b = args.browser

    if not args.no_default_profile:
        if b in ("auto", "edge") and edge_ud.exists():
            b = "edge"
            user_data_dir = edge_ud
        elif b in ("auto", "chrome") and chrome_ud.exists():
            b = "chrome"
            user_data_dir = chrome_ud
        else:
            b = "edge" if b == "auto" else b
        if user_data_dir:
            profile_dir = pick_profile_dir(user_data_dir, args.profile_directory)

    pause = not args.no_pause

    print("== Endfield (SKPort) cred grabber ==")
    print(f"browser: {b}")
    if user_data_dir and profile_dir:
        print(f"user-data-dir: {user_data_dir}")
        print(f"profile-directory: {profile_dir}")
        print("Note: If the browser is already running, profile may be locked. Close all Chrome/Edge and retry.")
    else:
        print("profile: (temporary session)")

    driver = None
    try:
        driver = build_driver(b, user_data_dir, profile_dir, args.headless)
        try:
            driver.execute_cdp_cmd("Network.enable", {})
        except Exception:
            pass

        driver.get(SKPORT_ENDFIELD_URL)
        print(f"Opened: {SKPORT_ENDFIELD_URL}")
        if not args.headless:
            print("If you are not logged in, please login and click the sign-in button once.")
            input("After you did one sign-in attempt, press Enter to read headers...")

        values = parse_performance_logs(driver)
        cred = values.get("ENDFIELD_CRED", "")
        role = values.get("ENDFIELD_SK_GAME_ROLE", "")

        print("\nExtracted values:")
        print(f"- ENDFIELD_CRED: {cred if args.raw else mask(cred)}")
        print(f"- ENDFIELD_SK_GAME_ROLE: {role if args.raw else mask(role)}")

        out_dir = exe_dir()
        env_path = out_dir / ".env"
        out_txt = out_dir / "secrets_output.txt"
        write_env(env_path, values)
        out_txt.write_text(
            "".join([f"{k}={values.get(k,'')}\n" for k in ["ENDFIELD_CRED", "ENDFIELD_SK_GAME_ROLE"]]),
            encoding="utf-8",
        )
        print(f"\nSaved to: {env_path}")
        print(f"Saved to: {out_txt}")

        pause_exit(pause)
        return 0 if cred and role else 1
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


if __name__ == "__main__":
    raise SystemExit(main())

