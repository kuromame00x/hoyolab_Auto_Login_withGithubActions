import json
import os
import time
import uuid
import random
import string
import hashlib
from pathlib import Path
from typing import Dict, Tuple

import requests


def _find_env_file() -> str:
    # Prefer ".env" in current dir, then next to script, then repo/src/.env.
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
    return str(Path.cwd() / ".env")


def load_env() -> None:
    path = _find_env_file()
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


def mask(v: str) -> str:
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


def make_headers(signgame: str, query: str) -> Dict[str, str]:
    device_id = os.getenv("HOYOLAB_DEVICE_ID") or str(uuid.uuid4())
    ltuid = os.getenv("LTUID") or ""
    ltoken = os.getenv("LTOKEN") or ""
    cookie_token = os.getenv("COOKIE_TOKEN_V2") or ""

    return {
        "Cookie": f"ltuid_v2={ltuid}; account_id_v2={ltuid}; ltoken_v2={ltoken}; cookie_token_v2={cookie_token};",
        "DS": generate_ds(body=None, query=query),
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


def check_hoyolab_info(game_name: str, act_id: str, info_url: str, signgame: str) -> Tuple[int, str]:
    load_env()

    query = f"act_id={act_id}"
    headers = make_headers(signgame, query=query)
    r = requests.get(info_url, headers=headers, params={"act_id": act_id}, timeout=20)

    try:
        j = r.json()
    except Exception:
        return r.status_code, (r.text[:400] if r.text else "")

    retcode = int(j.get("retcode", 0) or 0)
    msg = str(j.get("message", ""))
    return retcode, msg


def print_cookie_summary() -> None:
    load_env()
    print("Cookie summary (masked):")
    for k in ["LTUID", "LTOKEN", "COOKIE_TOKEN_V2"]:
        print(f"- {k}: {mask(os.getenv(k, ''))}")

