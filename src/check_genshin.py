from cookie_check_common import check_hoyolab_info, print_cookie_summary


def main() -> None:
    print("== Genshin (HoYoLAB) cookie check ==")
    print_cookie_summary()

    act_id = "e202102251931481"
    info_url = "https://sg-hk4e-api.hoyolab.com/event/sol/info"
    signgame = "hk4e"

    retcode, msg = check_hoyolab_info("Genshin", act_id, info_url, signgame)
    print(f"retcode: {retcode}")
    print(f"message: {msg}")


if __name__ == "__main__":
    main()

