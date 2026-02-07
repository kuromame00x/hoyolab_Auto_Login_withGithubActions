from cookie_check_common import check_hoyolab_info, pause_exit, print_cookie_summary, should_pause


def main() -> None:
    print("== Honkai: Star Rail (HoYoLAB) cookie check ==")
    print_cookie_summary()

    act_id = "e202303301540311"
    info_url = "https://sg-public-api.hoyolab.com/event/luna/hkrpg/os/info"
    signgame = "hkrpg"

    retcode, msg = check_hoyolab_info("HSR", act_id, info_url, signgame)
    print(f"retcode: {retcode}")
    print(f"message: {msg}")
    if should_pause():
        pause_exit()


if __name__ == "__main__":
    main()
