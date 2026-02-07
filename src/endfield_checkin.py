import os
import json
import time
import hmac
import hashlib
import urllib.request
import urllib.error


ZONAI_ORIGIN = "https://game.skport.com"
REFRESH_URL = "https://zonai.skport.com/web/v1/auth/refresh"
ATTEND_PATH = "/web/v1/game/endfield/attendance"
ATTEND_URL = "https://zonai.skport.com" + ATTEND_PATH


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
        # HTTP errorでもボディは返ってくることがある
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


def generate_sign(path: str, body_str: str, timestamp: str, token: str, platform: str, vname: str) -> str:
    # gistの文字列形式に合わせる（スペース無し）
    header_json = f'{{"platform":"{platform}","timestamp":"{timestamp}","dId":"","vName":"{vname}"}}'
    msg = path + body_str + timestamp + header_json

    h = hmac.new(token.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()
    return hashlib.md5(h.encode("utf-8")).hexdigest()


def claim_once(name: str, cred: str, sk_game_role: str, platform: str = "3", vname: str = "1.0.0") -> dict:
    ts = str(int(time.time()))

    token = refresh_token(cred, platform, vname)
    sign = generate_sign(ATTEND_PATH, "", ts, token, platform, vname)

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
        "Referer": ZONAI_ORIGIN + "/",
        "Origin": ZONAI_ORIGIN,
        "Content-Type": "application/json",
        "sk-language": os.getenv("ENDFIELD_LANG", "en"),
        "sk-game-role": sk_game_role,
        "cred": cred,
        "platform": platform,
        "vName": vname,
        "timestamp": ts,
        "sign": sign,
    }

    # gist側はbody無しで叩いている（UrlFetchApp.fetchでpayload未指定）流れに合わせる
    status, text = _http("POST", ATTEND_URL, headers, body=None)

    try:
        j = json.loads(text)
    except json.JSONDecodeError:
        return {"name": name, "ok": False, "http": status, "error": f"non-json: {text[:200]}"}

    code = j.get("code")
    if code == 0:
        # 報酬の整形（あれば）
        awards = []
        data = j.get("data") or {}
        award_ids = data.get("awardIds") or []
        rim = data.get("resourceInfoMap") or {}
        for a in award_ids:
            _id = a.get("id") if isinstance(a, dict) else a
            r = rim.get(str(_id)) or rim.get(_id)
            if isinstance(r, dict) and r.get("name") is not None:
                awards.append(f'{r.get("name")} x{r.get("count")}')
        return {"name": name, "ok": True, "http": status, "code": code, "status": "claimed", "awards": awards}

    if code == 10001:
        return {"name": name, "ok": True, "http": status, "code": code, "status": "already-claimed"}

    return {"name": name, "ok": False, "http": status, "code": code, "error": j.get("message")}


def load_profiles() -> list[dict]:
    # 1) 複数アカ対応（JSON）
    pj = os.getenv("ENDFIELD_PROFILES_JSON", "").strip()
    if pj:
        profiles = json.loads(pj)
        if not isinstance(profiles, list) or not profiles:
            raise RuntimeError("ENDFIELD_PROFILES_JSON must be a non-empty JSON array")
        return profiles

    # 2) 単一アカ
    cred = os.getenv("ENDFIELD_CRED", "").strip()
    role = os.getenv("ENDFIELD_SK_GAME_ROLE", "").strip()
    if not cred or not role:
        raise RuntimeError("ENDFIELD_CRED / ENDFIELD_SK_GAME_ROLE is required (or ENDFIELD_PROFILES_JSON)")
    return [{
        "accountName": os.getenv("ENDFIELD_ACCOUNT_NAME", "account"),
        "cred": cred,
        "skGameRole": role,
        "platform": os.getenv("ENDFIELD_PLATFORM", "3"),
        "vName": os.getenv("ENDFIELD_VNAME", "1.0.0"),
    }]


def main():
    profiles = load_profiles()
    results = []
    for p in profiles:
        name = p.get("accountName", "account")
        try:
            res = claim_once(
                name=name,
                cred=str(p["cred"]),
                sk_game_role=str(p["skGameRole"]),
                platform=str(p.get("platform", "3")),
                vname=str(p.get("vName", "1.0.0")),
            )
        except Exception as e:
            res = {"name": name, "ok": False, "error": str(e)}
        results.append(res)

    print("== Endfield daily check-in results ==")
    print(json.dumps(results, ensure_ascii=False, indent=2))

    # 失敗があればジョブを落としたい場合
    if any(not r.get("ok") for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
