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

url = "https://sg-public-api.hoyolab.com/event/luna/hkrpg/os/sign"
data = {
    "act_id": "e202303301540311"
}

response = requests.post(url, headers=headers, json=data)
print("Status:", response.status_code)
print(response.text)
