import json
import os
import sys
from pathlib import Path
from typing import Dict, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


HOYOLAB_URL = "https://act.hoyolab.com/bbs/event/signin/hkrpg/index.html?act_id=e202303301540311"
SKPORT_URL = "https://game.skport.com/endfield/sign-in?header=0&hg_media=skport&hg_link_campaign=tools"

def find_chrome_profile_txt() -> str:
    # Prefer alongside the executable (dist\chrome_profile.txt).
    candidates = []
    try:
        candidates.append(str((Path(sys.executable).resolve().parent / "chrome_profile.txt")))
    except Exception:
        pass
    candidates.append(str((Path.cwd() / "chrome_profile.txt")))
    candidates.append(str((Path(__file__).resolve().parent / "chrome_profile.txt")))

    for p in candidates:
        if p and os.path.exists(p):
            return p
    return "chrome_profile.txt"


def load_chrome_options_from_txt(path: str) -> Options:
    options = Options()
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    expanded_value = os.path.expandvars(value)
                    options.add_argument(f"--{key}={expanded_value}")
    else:
        print(f"{path} not found. Launching Chrome with default profile.")

    return options


def write_env(path: str, key: str, value: str) -> None:
    lines = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            found = True
            break

    if not found:
        lines.append(f"{key}={value}\n")

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def mask(value: Optional[str]) -> str:
    if not value:
        return "(empty)"
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def is_skport_url(url: str) -> bool:
    return "skport.com" in url or "zonai.skport.com" in url or "game.skport.com" in url


def is_hoyo_url(url: str) -> bool:
    return "hoyolab.com" in url or "hoyoverse.com" in url or "mihoyo.com" in url


def maybe_pick_headers(url: str, headers: Dict[str, str], found: Dict[str, str]) -> None:
    if is_skport_url(url):
        if "cred" in headers and "ENDFIELD_CRED" not in found:
            found["ENDFIELD_CRED"] = headers["cred"]
        if "sk-game-role" in headers and "ENDFIELD_SK_GAME_ROLE" not in found:
            found["ENDFIELD_SK_GAME_ROLE"] = headers["sk-game-role"]

    if is_hoyo_url(url):
        if "cred" in headers and "HOYOVERSE_CRED" not in found:
            found["HOYOVERSE_CRED"] = headers["cred"]
        if "sk-game-role" in headers and "HOYOVERSE_SK_GAME_ROLE" not in found:
            found["HOYOVERSE_SK_GAME_ROLE"] = headers["sk-game-role"]


def parse_performance_logs(driver: webdriver.Chrome) -> Dict[str, str]:
    url_map: Dict[str, str] = {}
    found: Dict[str, str] = {}

    for entry in driver.get_log("performance"):
        try:
            msg = json.loads(entry["message"])["message"]
        except Exception:
            continue

        method = msg.get("method")
        params = msg.get("params", {})

        if method == "Network.requestWillBeSent":
            request_id = params.get("requestId")
            request = params.get("request", {})
            url = request.get("url", "")
            if request_id and url:
                url_map[request_id] = url

            headers = request.get("headers", {})
            lower_headers = {str(k).lower(): str(v) for k, v in headers.items()}
            maybe_pick_headers(url, lower_headers, found)

        if method == "Network.requestWillBeSentExtraInfo":
            request_id = params.get("requestId")
            headers = params.get("headers", {})
            url = url_map.get(request_id, "")
            lower_headers = {str(k).lower(): str(v) for k, v in headers.items()}

            maybe_pick_headers(url, lower_headers, found)

    return found


def extract_hoyolab_cookies(driver: webdriver.Chrome) -> Dict[str, str]:
    cookie_dict: Dict[str, str] = {}
    for c in driver.get_cookies():
        if "hoyolab.com" in c.get("domain", ""):
            cookie_dict[c["name"]] = c["value"]

    return {
        "LTUID": cookie_dict.get("ltuid_v2", ""),
        "LTOKEN": cookie_dict.get("ltoken_v2", ""),
        "COOKIE_TOKEN_V2": cookie_dict.get("cookie_token_v2", ""),
    }


def main() -> None:
    profile_path = find_chrome_profile_txt()
    options = load_chrome_options_from_txt(profile_path)
    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd("Network.enable", {})

    try:
        print("Step 1/2: Open HoYoLAB and login if needed.")
        driver.get(HOYOLAB_URL)
        input("After login/check-in page is ready, press Enter...")
        hoyo = extract_hoyolab_cookies(driver)

        print("Step 2/2: Open SKPort Endfield sign-in page.")
        driver.get(SKPORT_URL)
        input("After login and pressing sign-in once, press Enter...")
        skport = parse_performance_logs(driver)

        merged = {}
        merged.update(hoyo)
        merged.update(skport)

        env_path = ".env"
        out_path = "secrets_output.txt"

        ordered_keys = [
            "LTUID",
            "LTOKEN",
            "COOKIE_TOKEN_V2",
            "ENDFIELD_CRED",
            "ENDFIELD_SK_GAME_ROLE",
            "HOYOVERSE_CRED",
            "HOYOVERSE_SK_GAME_ROLE",
        ]

        with open(out_path, "w", encoding="utf-8") as out:
            for key in ordered_keys:
                value = merged.get(key, "")
                if value:
                    write_env(env_path, key, value)
                    out.write(f"{key}={value}\n")
                else:
                    out.write(f"{key}=\n")

        print("\nCollected values (masked):")
        for key in ordered_keys:
            print(f"{key}: {mask(merged.get(key, ''))}")

        print("\nSaved:")
        print(f"- .env updated")
        print(f"- {out_path} written")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
