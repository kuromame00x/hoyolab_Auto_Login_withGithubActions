import json
import os
import time
import uuid
import random
import string
import hashlib

import requests
from dotenv import load_dotenv

load_dotenv()


def generate_ds(body: dict | None = None, query: str = "") -> str:
    """Generate DS header using body and query (required for some luna endpoints)."""
    t = str(int(time.time()))
    r = "".join(random.sample(string.ascii_lowercase + string.digits, 6))
    salt = os.getenv("HOYOLAB_DS_SALT", "h8w582wxwgqvahcdkpvdhbh2w9casgfl")
    body_str = json.dumps(body or {}, separators=(",", ":"), ensure_ascii=False)
    sign_str = f"salt={salt}&t={t}&r={r}&b={body_str}&q={query}"
    c = hashlib.md5(sign_str.encode()).hexdigest()
    return f"{t},{r},{c}"


def checkin(game_name: str, act_id: str, url: str, signgame: str) -> None:
    payload = {"act_id": act_id}
    query = f"act_id={act_id}"

    device_id = os.getenv("HOYOLAB_DEVICE_ID") or str(uuid.uuid4())
    ltuid = os.getenv("LTUID") or ""
    ltoken = os.getenv("LTOKEN") or ""
    cookie_token = os.getenv("COOKIE_TOKEN_V2") or ""

    headers = {
        # include account_id_v2 for luna endpoints that validate account id explicitly
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

    print(f"\n== {game_name} チェックイン中...")
    response = requests.post(url, headers=headers, json=payload)
    print(f"Status: {response.status_code}")
    print(response.text)


# 各ゲームごとのact_idとURL
games = [
    ("原神", "e202102251931481", "https://sg-hk4e-api.hoyolab.com/event/sol/sign", "hk4e"),  # Genshin
    ("崩壊スターレイル", "e202303301540311", "https://sg-public-api.hoyolab.com/event/luna/hkrpg/os/sign", "hkrpg"),  # Star Rail
    # 崩壊3rdのact_idはイベントが切り替わるたびに変わることがあるため、環境変数で上書きできるようにする
    ("崩壊3rd", os.getenv("BH3_ACT_ID", "e202110291205111"), "https://sg-public-api.hoyolab.com/event/luna/bh3/os/sign", "bh3"),  # Honkai Impact 3rd
    ("ゼンレスゾーンゼロ", "e202406031448091", "https://sg-public-api.hoyolab.com/event/luna/zzz/os/sign", "zzz"),  # Zenless Zone Zero
]

for game_name, act_id, url, signgame in games:
    checkin(game_name, act_id, url, signgame)
