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
    ap.add_argument("--preset", choices=sorted(PRESETS.keys()), default="hsr", help="Choose a game URL preset (for reference only).")
    ap.add_argument("--url", default=None, help="Optional URL (for reference only). If set, overrides --preset.")
    ap.add_argument("--browser", choices=["auto", "edge", "chrome"], default="auto")
    ap.add_argument("--profile-directory", default=None, help="Chrome/Edge profile directory, e.g. Default or Profile 1.")
    ap.add_argument("--raw", action="store_true", help="Print raw cookie values to console.")
    ap.add_argument("--no-kill-browser", action="store_true", help="Do not taskkill the target browser before reading cookie DB.")
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
        kill_browser=not args.no_kill_browser,
    )


if __name__ == "__main__":
    raise SystemExit(main())

