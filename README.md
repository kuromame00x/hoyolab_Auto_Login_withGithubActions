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

### cookiegrab.exe（推奨）

1. GitHub Releases から `cookiegrab.exe` をダウンロード
2. 対象ゲームのチェックインページを開く（ログイン済み状態にする）
3. DevTools (`F12`) → `Network`
4. `Preserve log` を ON にして、ページを再読み込み（通信を出す）
5. `Save all as HAR with content` で `.har` を保存
6. `cookiegrab.exe` で HAR を読み取って値を表示

例:

```bat
cookiegrab.exe --list-games
cookiegrab.exe 1 "C:\\path\\to\\hoyolab.har" --raw
```

出力された値をそのまま Secrets に登録してください:
- `LTUID`
- `LTOKEN`
- `COOKIE_TOKEN_V2`

注意:
- `.har` には Cookie やヘッダが含まれるので、他人に共有しないでください。使い終わったら削除推奨です。

## Endfield 用 Secret 取得方法（`ENDFIELD_CRED`, `ENDFIELD_SK_GAME_ROLE`）

1. Endfield サインインページを開いてログイン  
   `https://game.skport.com/endfield/sign-in?header=0&hg_media=skport&hg_link_campaign=tools`
2. DevTools (`F12`) → `Network`
3. `Preserve log` を ON にして、サインイン（出席）ボタンを 1 回押して通信を出す
4. `Save all as HAR with content` で `.har` を保存
5. `cookiegrab.exe` で HAR を読み取って値を表示

例:

```bat
cookiegrab.exe 5 "C:\\path\\to\\endfield.har" --raw
```

出力された値を Secrets に登録してください:
- `ENDFIELD_CRED`
- `ENDFIELD_SK_GAME_ROLE`

## 動作確認

1. `Actions` タブで `Auto Hoyolab Check-in` を開く
2. `Run workflow` を実行
3. ログで次を確認
   - HoYoLAB: `retcode -5003` は「本日分取得済み」
   - Endfield: `claimed` または `already-claimed`
