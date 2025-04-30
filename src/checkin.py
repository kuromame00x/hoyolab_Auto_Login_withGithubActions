import os
import requests
import time
import random
import hashlib
import uuid
from dotenv import load_dotenv

load_dotenv()

def generate_ds():
    t = str(int(time.time()))
    r = str(random.randint(100000, 200000))
    salt = "xV8v4Qu54lUKrEYFZkJhB8cuOh9Asafs"
    c = hashlib.md5(f"salt={salt}&t={t}&r={r}".encode()).hexdigest()
    return f"{t},{r},{c}"

def checkin(game_name, act_id, url):
    headers = {
        "Cookie": f"ltuid_v2={os.getenv('LTUID')}; ltoken_v2={os.getenv('LTOKEN')}; cookie_token_v2={os.getenv('COOKIE_TOKEN_V2')};",
        "DS": generate_ds(),
        "x-rpc-client_type": "2",
        "x-rpc-app_version": "2.36.1",
        "x-rpc-language": "ja-jp",
        "x-rpc-device_id": str(uuid.uuid4()),
        "User-Agent": "okhttp/4.8.0",
        "Referer": "https://act.hoyolab.com",
        "Content-Type": "application/json"
    }

    data = { "act_id": act_id }

    print(f"\n🔄 {game_name} チェックイン中...")
    response = requests.post(url, headers=headers, json=data)
    print(f"Status: {response.status_code}")
    print(response.text)

# 各ゲームごとのact_idとURL
games = [
    ("原神",        "e202102251931481",   "https://sg-hk4e-api.hoyolab.com/event/sol/sign"),             # Genshin
    ("崩壊スターレイル", "e202303301540311",   "https://sg-public-api.hoyolab.com/event/luna/hkrpg/os/sign"), # Star Rail
    ("崩壊3rd",     "e202110291205111",   "https://sg-public-api.hoyolab.com/event/luna/bh3/os/sign"),   # Honkai Impact 3rd
    ("ゼンレスゾーンゼロ", "e202406031448091",   "https://sg-public-api.hoyolab.com/event/luna/zzz/os/sign"),   # Zenless Zone Zero
]

for game_name, act_id, url in games:
    checkin(game_name, act_id, url)
