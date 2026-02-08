import argparse

from grab_endfield_cred_lib import run_endfield_cred_grab


def main() -> int:
    ap = argparse.ArgumentParser(description="Read Endfield (SKPort) cred cookie from default browser profile (offline).")
    ap.add_argument("--browser", choices=["auto", "edge", "chrome"], default="chrome")
    ap.add_argument("--profile-directory", default=None, help="Chrome/Edge profile directory, e.g. Default or Profile 1.")
    ap.add_argument("--list-profiles", action="store_true", help="List available Chrome/Edge profile directories and exit.")

    kill_group = ap.add_mutually_exclusive_group()
    kill_group.add_argument("--kill-browser", dest="kill_browser", action="store_true", help="Taskkill the target browser before reading cookie DB.")
    kill_group.add_argument("--no-kill-browser", dest="kill_browser", action="store_false", help=argparse.SUPPRESS)
    ap.set_defaults(kill_browser=False)

    ap.add_argument("--raw", action="store_true", help="Print raw cookie value to console.")
    ap.add_argument("--no-pause", action="store_true", help="Do not wait for Enter before exit.")
    args = ap.parse_args()

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

    return run_endfield_cred_grab(
        browser=args.browser,
        profile_directory=args.profile_directory,
        raw=args.raw,
        pause=not args.no_pause,
        kill_browser=bool(args.kill_browser),
    )


if __name__ == "__main__":
    raise SystemExit(main())
