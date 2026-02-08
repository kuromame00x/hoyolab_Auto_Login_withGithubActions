import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

from endfieldgrab_har import extract_endfield_headers_from_har
from grab_hoyolab_cookies_lib import run_cookie_grab
from grab_urls import HOYOLAB_GI_URL, HOYOLAB_HSR_URL, HOYOLAB_HI3_URL, HOYOLAB_ZZZ_URL, SKPORT_ENDFIELD_URL
from grab_endfield_cred_lib import run_endfield_cred_grab


PRESETS = {
    # HoYoLAB
    "genshin": HOYOLAB_GI_URL,
    "gi": HOYOLAB_GI_URL,
    "hsr": HOYOLAB_HSR_URL,
    "starrail": HOYOLAB_HSR_URL,
    "zzz": HOYOLAB_ZZZ_URL,
    "hi3": HOYOLAB_HI3_URL,
    "bh3": HOYOLAB_HI3_URL,
    # Endfield (SKPort)
    "endfield": SKPORT_ENDFIELD_URL,
    "skport": SKPORT_ENDFIELD_URL,
}


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


def _parse_cookie_header(cookie_header: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in (cookie_header or "").split(";"):
        p = part.strip()
        if not p or "=" not in p:
            continue
        k, v = p.split("=", 1)
        k = k.strip()
        if not k:
            continue
        out[k] = v.strip()
    return out


def extract_hoyolab_tokens_from_har(har: dict) -> dict[str, str]:
    wanted = ["ltuid_v2", "ltoken_v2", "cookie_token_v2"]
    best: dict[str, str] = {}
    best_score = 0

    entries = (((har or {}).get("log") or {}).get("entries")) or []
    if not isinstance(entries, list):
        return {"LTUID": "", "LTOKEN": "", "COOKIE_TOKEN_V2": ""}

    for ent in entries:
        req = (ent or {}).get("request") or {}
        url = str(req.get("url", ""))
        if "hoyolab.com" not in url:
            continue
        headers = req.get("headers") or []
        if not isinstance(headers, list):
            continue
        m: dict[str, str] = {}
        for h in headers:
            if not isinstance(h, dict):
                continue
            n = str(h.get("name", "")).strip().lower()
            v = str(h.get("value", "")).strip()
            if n:
                m[n] = v
        cookie_header = m.get("cookie", "")
        if not cookie_header:
            continue
        cookies = _parse_cookie_header(cookie_header)
        score = sum(1 for k in wanted if cookies.get(k))
        if score > best_score:
            best = cookies
            best_score = score
            if best_score >= 3:
                break

    return {
        "LTUID": best.get("ltuid_v2", ""),
        "LTOKEN": best.get("ltoken_v2", ""),
        "COOKIE_TOKEN_V2": best.get("cookie_token_v2", ""),
    }


def detect_target(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        host = ""
    if "hoyolab.com" in host:
        return "hoyolab"
    if "skport.com" in host or "zonai.skport.com" in host:
        return "endfield"
    # Fallback: if the url is empty or malformed, treat as unknown.
    return "unknown"


def run_from_har(*, target: str, har_path: str, raw: bool, pause: bool) -> int:
    hp = Path(har_path).expanduser()
    if not hp.exists():
        print(f"ERROR: HAR not found: {hp}")
        pause_exit(pause)
        return 1

    try:
        har = json.loads(hp.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"ERROR: Failed to parse HAR: {e}")
        pause_exit(pause)
        return 1

    if target == "hoyolab":
        values = extract_hoyolab_tokens_from_har(har)
        print("== HoYoLAB cookie grabber (HAR) ==")
        print(f"har: {hp}")
        print("\nCookie values:")
        for k in ["LTUID", "LTOKEN", "COOKIE_TOKEN_V2"]:
            v = values.get(k, "") or ""
            print(f"- {k}: {v if raw else mask(v)}")
        if any(not values.get(k) for k in ["LTUID", "LTOKEN", "COOKIE_TOKEN_V2"]):
            print("\nNOTE: Some cookie values were not found in this HAR.")
            print("Tips: In DevTools Network tab, enable 'Preserve log', reload the page, then export HAR.")
        print("\nNOTE: This tool does not save secrets to disk; it only prints them.")
        pause_exit(pause)
        return 0 if any(values.get(k) for k in values) else 1

    if target == "endfield":
        values = extract_endfield_headers_from_har(har)
        print("== Endfield (SKPort) grabber (HAR) ==")
        print(f"har: {hp}")
        print("\nExtracted values:")
        for k in ["ENDFIELD_CRED", "ENDFIELD_SK_GAME_ROLE", "ENDFIELD_PLATFORM", "ENDFIELD_VNAME"]:
            v = values.get(k, "") or ""
            print(f"- {k}: {v if raw else mask(v)}")
        if not values.get("ENDFIELD_CRED") or not values.get("ENDFIELD_SK_GAME_ROLE"):
            print("\nNOTE: cred / sk-game-role not found in this HAR.")
            print("Tips: In DevTools Network tab, enable 'Preserve log'.")
            print("      Open Endfield sign-in page and click the sign-in button once, then export HAR.")
        print("\nNOTE: This tool does not save secrets to disk; it only prints them.")
        pause_exit(pause)
        return 0 if values.get("ENDFIELD_CRED") and values.get("ENDFIELD_SK_GAME_ROLE") else 1

    print(f"ERROR: Unknown target: {target}")
    pause_exit(pause)
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(
        description="One-file grabber for HoYoLAB cookies and Endfield (SKPort) headers.\n"
        "Note: Modern Chrome/Edge uses v20 (app-bound) cookie encryption; offline cookie DB decrypt may not work.\n"
        "      Use --source har with a DevTools-exported HAR for the most reliable results."
    )
    ap.add_argument(
        "--preset",
        "--game",
        dest="preset",
        choices=sorted(PRESETS.keys()),
        default="hsr",
        help="Choose a URL preset.",
    )
    ap.add_argument("--url", default=None, help="Target URL. If set, overrides --preset.")
    ap.add_argument("--target", choices=["auto", "hoyolab", "endfield"], default="auto", help="Override auto detection by URL host.")
    ap.add_argument("--source", choices=["har", "browser"], default="har", help="Where to read values from (default: har).")
    ap.add_argument("--har", default=None, help="Path to HAR file exported from browser DevTools (required for --source har).")

    # Browser options (only used with --source browser)
    ap.add_argument("--browser", choices=["auto", "edge", "chrome"], default="chrome")
    ap.add_argument("--profile-directory", default=None, help="Chrome/Edge profile directory, e.g. Default or Profile 1.")
    ap.add_argument("--list-profiles", action="store_true", help="List available Chrome/Edge profile directories and exit.")
    kill_group = ap.add_mutually_exclusive_group()
    kill_group.add_argument("--kill-browser", dest="kill_browser", action="store_true", help="Taskkill the target browser before reading cookie DB.")
    kill_group.add_argument("--no-kill-browser", dest="kill_browser", action="store_false", help=argparse.SUPPRESS)  # backward compat
    ap.set_defaults(kill_browser=False)

    ap.add_argument("--raw", action="store_true", help="Print raw values to console.")
    ap.add_argument("--no-pause", action="store_true", help="Do not wait for Enter before exit.")
    args = ap.parse_args()

    pause = not args.no_pause

    if args.list_profiles:
        from browser_cookies_windows import list_available_profiles

        profs = list_available_profiles(args.browser)
        print("Available profiles:")
        if not profs:
            print("(none found)")
            return 1
        for p in profs:
            print(f"- {p.name}: {p.profile_dir} ({p.user_data_dir})")
        return 0

    url = args.url or PRESETS[args.preset]
    target = args.target if args.target != "auto" else detect_target(url)
    if target == "unknown":
        print("ERROR: Could not detect target type from URL. Use --target hoyolab|endfield.")
        pause_exit(pause)
        return 1

    if args.source == "har":
        if not args.har:
            print("ERROR: --har is required for --source har.")
            pause_exit(pause)
            return 1
        return run_from_har(target=target, har_path=args.har, raw=args.raw, pause=pause)

    # --source browser (best-effort; may fail on v20 app-bound cookie encryption)
    if target == "hoyolab":
        return run_cookie_grab(
            url=url,
            browser=args.browser,
            profile_directory=args.profile_directory,
            use_default_profile=True,
            headless=False,
            raw=args.raw,
            pause=pause,
            kill_browser=bool(args.kill_browser),
        )

    if target == "endfield":
        print("NOTE: Endfield requires ENDFIELD_SK_GAME_ROLE (request header).")
        print("      Offline mode can show cred and role ids, but HAR mode is recommended for exact header values.")
        return run_endfield_cred_grab(
            browser=args.browser,
            profile_directory=args.profile_directory,
            raw=args.raw,
            pause=pause,
            kill_browser=bool(args.kill_browser),
        )

    print(f"ERROR: Unknown target: {target}")
    pause_exit(pause)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
