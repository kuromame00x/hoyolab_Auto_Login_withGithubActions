import argparse

from grab_hoyolab_cookies_lib import run_cookie_grab
from grab_urls import HOYOLAB_HI3_URL


def main() -> int:
    ap = argparse.ArgumentParser(description="Open HI3 HoYoLAB sign-in page and read cookie values from default browser profile.")
    ap.add_argument("--browser", choices=["auto", "edge", "chrome"], default="auto")
    ap.add_argument("--profile-directory", default=None, help="Chrome/Edge profile directory, e.g. Default or Profile 1.")
    ap.add_argument("--no-default-profile", action="store_true", help="Do not use the default browser profile.")
    ap.add_argument("--headless", action="store_true", help="Run headless (may break interactive login).")
    ap.add_argument("--raw", action="store_true", help="Print raw cookie values to console.")
    ap.add_argument("--no-kill-browser", action="store_true", help="Do not taskkill the target browser before reading cookie DB.")
    ap.add_argument("--no-pause", action="store_true", help="Do not wait for Enter before exit.")
    args = ap.parse_args()

    return run_cookie_grab(
        url=HOYOLAB_HI3_URL,
        browser=args.browser,
        profile_directory=args.profile_directory,
        use_default_profile=not args.no_default_profile,
        headless=args.headless,
        raw=args.raw,
        pause=not args.no_pause,
        kill_browser=not args.no_kill_browser,
    )


if __name__ == "__main__":
    raise SystemExit(main())
