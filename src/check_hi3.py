import os

from cookie_check_common import check_hoyolab_info, pause_exit, print_cookie_summary, should_pause


def main() -> None:
    print("== Honkai Impact 3rd (HoYoLAB) cookie check ==")
    print_cookie_summary()

    act_id = os.getenv("BH3_ACT_ID", "e202110291205111")
    info_url = "https://sg-public-api.hoyolab.com/event/mani/info"
    signgame = "bh3"

    retcode, msg = check_hoyolab_info("HI3", act_id, info_url, signgame)
    print(f"act_id: {act_id}")
    print(f"retcode: {retcode}")
    print(f"message: {msg}")
    if should_pause():
        pause_exit()


if __name__ == "__main__":
    main()
