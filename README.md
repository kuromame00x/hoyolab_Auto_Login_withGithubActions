# HoYoLAB Auto Login with GitHub Actions

このリポジトリは、次のデイリーチェックインを GitHub Actions で自動化します。

- HoYoLAB（原神 / 崩壊スターレイル / 崩壊3rd / ゼンレスゾーンゼロ）
- Endfield（Arknights: Endfield）

## 自動実行タイミング

`.github/workflows/auto-checkin.yml` の `cron` は現在 `毎日 01:00 JST` です。  
必要に応じて編集してください。

## セットアップ

### 1. リポジトリを fork

GitHub 上で fork して使ってください。

### 2. Actions Secrets を登録

`Settings > Secrets and variables > Actions > Repository secrets` に登録します。  
`Repository variables` ではなく `Repository secrets` に入れてください。

必須 Secret 一覧:

| Secret Name | 用途 |
|---|---|
| `LTUID` | HoYoLAB 用 Cookie |
| `LTOKEN` | HoYoLAB 用 Cookie |
| `COOKIE_TOKEN_V2` | HoYoLAB 用 Cookie |
| `ENDFIELD_CRED` | Endfield API 認証ヘッダ |
| `ENDFIELD_SK_GAME_ROLE` | Endfield API 認証ヘッダ |

補足:
- `ENDFIELD_PLATFORM` / `ENDFIELD_VNAME` / `ENDFIELD_ACCOUNT_NAME` はこの workflow では不要です。
- Secrets の編集画面は仕様上、既存値が空欄表示になります（値が消えているわけではありません）。

## HoYoLAB 用 Secret 取得方法

## Cookie 確認ツール（ゲーム別）

それぞれのゲームをプレイしていない場合、チェックイン状況の確認が分かりづらいことがあるため、
ゲーム別に「ログインできているか（cookie/認証情報が有効か）」だけ確認する `exe` を用意します。

配布:
- GitHub Releases に `cookiecheck_*.exe` を配置します（リポジトリに exe はコミットしません）

ビルド/Release:
- タグ `cookiecheck-v*` を push すると、GitHub Actions が Windows 用 exe をビルドして Release に添付します。

### B. DevTools で手動取得する方法

1. HoYoLAB チェックインページを開く  
   `https://act.hoyolab.com/bbs/event/signin/hkrpg/index.html?act_id=e202303301540311`
2. DevTools (`F12`) を開く
3. `Application > Storage > Cookies > https://*.hoyolab.com`
4. `ltuid_v2` / `ltoken_v2` / `cookie_token_v2` を取得
5. 次の対応で Secrets に登録
   - `LTUID` <- `ltuid_v2`
   - `LTOKEN` <- `ltoken_v2`
   - `COOKIE_TOKEN_V2` <- `cookie_token_v2`

## Endfield 用 Secret 取得方法（`ENDFIELD_CRED`, `ENDFIELD_SK_GAME_ROLE`）

1. Endfield サインインページを開いてログイン  
   `https://game.skport.com/endfield/sign-in?header=0&hg_media=skport&hg_link_campaign=tools`
2. DevTools (`F12`) を開き、`Network` タブへ
3. サインイン実行時の通信を選択（例:  
   `https://zonai.skport.com/web/v1/game/endfield/attendance` か  
   `https://zonai.skport.com/web/v1/auth/refresh`）
4. `Request Headers` から次を取得
   - `cred` -> `ENDFIELD_CRED`
   - `sk-game-role` -> `ENDFIELD_SK_GAME_ROLE`
5. 2つを `Repository secrets` に登録

## 動作確認

1. `Actions` タブで `Auto Hoyolab Check-in` を開く
2. `Run workflow` を実行
3. ログで次を確認
   - HoYoLAB: `retcode -5003` は「本日分取得済み」
   - Endfield: `claimed` または `already-claimed`
