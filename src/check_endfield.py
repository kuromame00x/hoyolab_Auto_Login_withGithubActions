import json
import os
import time
import hmac
import hashlib
import urllib.request
import urllib.error

from cookie_check_common import load_env, mask


ZONAI_ORIGIN = "https://game.skport.com"
REFRESH_URL = "https://zonai.skport.com/web/v1/auth/refresh"


def _http(method: str, url: str, headers: dict, body: bytes | None = None, timeout: int = 20) -> tuple[int, str]:
    req = urllib.request.Request(url, data=body, method=method.upper())
    for k, v in headers.items():
        req.add_header(k, v)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
            text = resp.read().decode("utf-8", errors="replace")
            return status, text
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", errors="replace")
        return e.code, text


def refresh_token(cred: str, platform: str, vname: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "cred": cred,
        "platform": platform,
        "vName": vname,
        "Origin": ZONAI_ORIGIN,
        "Referer": ZONAI_ORIGIN + "/",
    }
    status, text = _http("GET", REFRESH_URL, headers, body=None)
    try:
        j = json.loads(text)
    except json.JSONDecodeError:
        raise RuntimeError(f"refresh: non-json (HTTP {status}): {text[:200]}")

    if j.get("code") == 0 and isinstance(j.get("data"), dict) and j["data"].get("token"):
        return str(j["data"]["token"])

    raise RuntimeError(f"refresh failed: HTTP {status}, code={j.get('code')}, msg={j.get('message')}")


def main() -> None:
    print("== Endfield credential check ==")
    load_env()

    cred = (os.getenv("ENDFIELD_CRED") or "").strip()
    role = (os.getenv("ENDFIELD_SK_GAME_ROLE") or "").strip()
    platform = (os.getenv("ENDFIELD_PLATFORM") or "3").strip()
    vname = (os.getenv("ENDFIELD_VNAME") or "1.0.0").strip()

    print(f"ENDFIELD_CRED: {mask(cred)}")
    print(f"ENDFIELD_SK_GAME_ROLE: {mask(role)}")
    print(f"ENDFIELD_PLATFORM: {platform}")
    print(f"ENDFIELD_VNAME: {vname}")

    if not cred or not role:
        print("Missing ENDFIELD_CRED or ENDFIELD_SK_GAME_ROLE.")
        raise SystemExit(1)

    # Minimal non-claim check: refresh must succeed.
    token = refresh_token(cred, platform, vname)
    print(f"refresh ok, token: {mask(token)}")
    print("OK")


if __name__ == "__main__":
    main()

