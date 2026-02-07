from cookie_check_common import check_hoyolab_info, pause_exit, print_cookie_summary, should_pause


def main() -> None:
    print("== Genshin (HoYoLAB) cookie check ==")
    print_cookie_summary()

    act_id = "e202102251931481"
    info_url = "https://sg-hk4e-api.hoyolab.com/event/sol/info"
    signgame = "hk4e"

    retcode, msg = check_hoyolab_info("Genshin", act_id, info_url, signgame)
    print(f"retcode: {retcode}")
    print(f"message: {msg}")
    if should_pause():
        pause_exit()


if __name__ == "__main__":
    main()
