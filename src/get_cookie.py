from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os

# プロファイル設定ファイルを読み込んで ChromeOptions に反映
def load_chrome_options_from_txt(path):
    options = Options()
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    expanded_value = os.path.expandvars(value)  # 環境変数を展開
                    options.add_argument(f"--{key}={expanded_value}")
    else:
        print(f"{path} が見つかりません")
    return options

# 設定ファイルからChromeオプションを読み込む
options = load_chrome_options_from_txt("chrome_profile.txt")

# ChromeDriver 起動
driver = webdriver.Chrome(options=options)

# HoYoLAB にアクセス（Star Rail のチェックインページ）
driver.get("https://act.hoyolab.com/bbs/event/signin/hkrpg/index.html?act_id=e202303301540311")

print("ログインしていない場合は、ログインしてください。完了したらEnterを押してください。")
input()

# Cookie を収集
cookies = driver.get_cookies()

# 必要なCookieだけ抽出（ドメイン名に hoyolab.com を含むもの限定）
cookie_dict = {}
for c in cookies:
    if "hoyolab.com" in c.get("domain", ""):
        cookie_dict[c["name"]] = c["value"]

# 必要なキー
cookie_values = {
    "LTUID": cookie_dict.get("ltuid_v2"),
    "LTOKEN": cookie_dict.get("ltoken_v2"),
    "COOKIE_TOKEN_V2": cookie_dict.get("cookie_token_v2"),
}

# クォートなしで .env に書き込む関数
def write_env(path, key, value):
    lines = []
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

    key_exists = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            key_exists = True
            break

    if not key_exists:
        lines.append(f"{key}={value}\n")

    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print(f"{key} を .env に書き込みました（クォートなし）")

# 書き込み実行
env_path = ".env"
for key, value in cookie_values.items():
    if value:
        write_env(env_path, key, value)
    else:
        print(f"{key} が見つかりませんでした")

driver.quit()
