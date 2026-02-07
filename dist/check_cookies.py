import json
import os
import time
import uuid
import random
import string
import hashlib
from pathlib import Path

import requests


def _find_env_file() -> str:
    here = Path(__file__).resolve().parent
    repo = here.parent
    candidates = [
        Path.cwd() / ".env",
        here / ".env",
        repo / "src" / ".env",
        repo / ".env",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return str(here / ".env")


def _load_env(path: str) -> None:
    # minimal .env loader: KEY=VALUE lines
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            if not k:
                continue
            os.environ.setdefault(k, v.strip())


def _mask(v: str) -> str:
    if not v:
        return "(empty)"
    if len(v) <= 8:
        return "*" * len(v)
    return f"{v[:4]}...{v[-4:]}"


def generate_ds(body: dict | None = None, query: str = "") -> str:
    t = str(int(time.time()))
    r = "".join(random.sample(string.ascii_lowercase + string.digits, 6))
    salt = os.getenv("HOYOLAB_DS_SALT", "h8w582wxwgqvahcdkpvdhbh2w9casgfl")
    body_str = json.dumps(body or {}, separators=(",", ":"), ensure_ascii=False)
    sign_str = f"salt={salt}&t={t}&r={r}&b={body_str}&q={query}"
    c = hashlib.md5(sign_str.encode()).hexdigest()
    return f"{t},{r},{c}"


def make_headers(signgame: str, payload: dict | None = None, query: str = "") -> dict:
    device_id = os.getenv("HOYOLAB_DEVICE_ID") or str(uuid.uuid4())
    ltuid = os.getenv("LTUID") or ""
    ltoken = os.getenv("LTOKEN") or ""
    cookie_token = os.getenv("COOKIE_TOKEN_V2") or ""

    return {
        "Cookie": f"ltuid_v2={ltuid}; account_id_v2={ltuid}; ltoken_v2={ltoken}; cookie_token_v2={cookie_token};",
        "DS": generate_ds(payload, query),
        "x-rpc-client_type": "5",
        "x-rpc-app_version": "2.70.1",
        "x-rpc-language": "ja-jp",
        "x-rpc-signgame": signgame,
        "x-rpc-device_id": device_id,
        "User-Agent": "okhttp/4.8.0",
        "Referer": "https://act.hoyolab.com",
        "Origin": "https://act.hoyolab.com",
        "Content-Type": "application/json",
    }


def check_info(game_name: str, act_id: str, url: str, signgame: str) -> None:
    query = f"act_id={act_id}"
    headers = make_headers(signgame, payload=None, query=query)
    r = requests.get(url, headers=headers, params={"act_id": act_id}, timeout=20)
    print(f"\n== {game_name} info ==")
    print(f"GET {r.url}")
    print(f"Status: {r.status_code}")
    try:
        j = r.json()
    except Exception:
        print(r.text[:400])
        return
    print(json.dumps({"retcode": j.get("retcode"), "message": j.get("message")}, ensure_ascii=False))
    # If available, show sign-in status fields
    data = j.get("data") if isinstance(j, dict) else None
    if isinstance(data, dict):
        for k in ["is_sign", "is_signin", "today", "total_sign_day", "sign_cnt"]:
            if k in data:
                print(f"{k}: {data.get(k)}")


def main() -> None:
    env_path = _find_env_file()
    _load_env(env_path)

    print(f"Loaded env from: {env_path}")
    for k in ["LTUID", "LTOKEN", "COOKIE_TOKEN_V2"]:
        print(f"{k}: {_mask(os.getenv(k, ''))}")

    if not (os.getenv("LTUID") and os.getenv("LTOKEN") and os.getenv("COOKIE_TOKEN_V2")):
        print("\nMissing cookie values. Update your .env or GitHub Secrets first.")
        return

    games = [
        ("原神", "e202102251931481", "https://sg-hk4e-api.hoyolab.com/event/sol/info", "hk4e"),
        ("崩壊スターレイル", "e202303301540311", "https://sg-public-api.hoyolab.com/event/luna/hkrpg/os/info", "hkrpg"),
        ("崩壊3rd", os.getenv("BH3_ACT_ID", "e202110291205111"), "https://sg-public-api.hoyolab.com/event/mani/info", "bh3"),
        ("ゼンレスゾーンゼロ", "e202406031448091", "https://sg-public-api.hoyolab.com/event/luna/zzz/os/info", "zzz"),
    ]

    for game_name, act_id, url, signgame in games:
        check_info(game_name, act_id, url, signgame)


if __name__ == "__main__":
    main()

