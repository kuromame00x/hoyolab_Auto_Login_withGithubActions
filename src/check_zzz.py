from cookie_check_common import check_hoyolab_info, print_cookie_summary


def main() -> None:
    print("== Zenless Zone Zero (HoYoLAB) cookie check ==")
    print_cookie_summary()

    act_id = "e202406031448091"
    info_url = "https://sg-public-api.hoyolab.com/event/luna/zzz/os/info"
    signgame = "zzz"

    retcode, msg = check_hoyolab_info("ZZZ", act_id, info_url, signgame)
    print(f"retcode: {retcode}")
    print(f"message: {msg}")


if __name__ == "__main__":
    main()

