import argparse

from grab_hoyolab_cookies_lib import run_cookie_grab
from grab_urls import HOYOLAB_GI_URL, HOYOLAB_HSR_URL, HOYOLAB_HI3_URL, HOYOLAB_ZZZ_URL


PRESETS = {
    "genshin": HOYOLAB_GI_URL,
    "gi": HOYOLAB_GI_URL,
    "hsr": HOYOLAB_HSR_URL,
    "starrail": HOYOLAB_HSR_URL,
    "zzz": HOYOLAB_ZZZ_URL,
    "hi3": HOYOLAB_HI3_URL,
    "bh3": HOYOLAB_HI3_URL,
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Read HoYoLAB cookie values from default browser profile (offline).")
    ap.add_argument(
        "--preset",
        "--game",
        dest="preset",
        choices=sorted(PRESETS.keys()),
        default="hsr",
        help="Choose a game URL preset (for reference only).",
    )
    ap.add_argument("--url", default=None, help="Optional URL (for reference only). If set, overrides --preset.")
    # Prefer Chrome by default (user request); use --browser auto if you want auto detection.
    ap.add_argument("--browser", choices=["auto", "edge", "chrome"], default="chrome")
    ap.add_argument("--profile-directory", default=None, help="Chrome/Edge profile directory, e.g. Default or Profile 1.")
    ap.add_argument("--raw", action="store_true", help="Print raw cookie values to console.")

    # Default: do NOT kill the browser. If the cookie DB is locked, close Chrome and retry, or pass --kill-browser.
    kill_group = ap.add_mutually_exclusive_group()
    kill_group.add_argument("--kill-browser", dest="kill_browser", action="store_true", help="Taskkill the target browser before reading cookie DB.")
    kill_group.add_argument("--no-kill-browser", dest="kill_browser", action="store_false", help=argparse.SUPPRESS)  # backward compat
    ap.set_defaults(kill_browser=False)

    ap.add_argument("--no-pause", action="store_true", help="Do not wait for Enter before exit.")
    args = ap.parse_args()

    url = args.url or PRESETS[args.preset]
    return run_cookie_grab(
        url=url,
        browser=args.browser,
        profile_directory=args.profile_directory,
        use_default_profile=True,
        headless=False,
        raw=args.raw,
        pause=not args.no_pause,
        kill_browser=bool(args.kill_browser),
    )


if __name__ == "__main__":
    raise SystemExit(main())
