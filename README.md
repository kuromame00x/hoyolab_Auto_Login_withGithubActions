# HoYoLAB Auto Login with GitHub Actions
 
このリポジトリは、HoYoLAB（原神 / スターレイル）のデイリーチェックインを GitHub Actions で自動化するスクリプトです。  
※ 崩壊3rdとゼンレスゾーンゼロ（ZZZ）は現在API非対応のため、別途対応中です。

---

## ✅ 自動実行のタイミング

`.github/workflows/auto-checkin.yml` の中で、毎日 7:00 JST に実行されるよう設定されています。  
必要に応じて `cron` を編集してください。

---

## ✅ セットアップ手順

### 1. このリポジトリをフォークする

GitHub 上で本リポジトリ [`hoyolab_Auto_Login_withGithubActions`](https://github.com/kuromame00x/hoyolab_Auto_Login_withGithubActions) をフォークしてください。

---

### 2. Cookie・トークンを取得する

#### ✅ 2-1. `get_cookie.exe` を入手する

- このリポジトリを `git clone` または ZIP でダウンロードして展開
- フォルダ内の `dist/get_cookie.exe` を実行します

#### ✅ 2-2. Chrome プロファイルの準備（初回のみ）

`get_cookie.exe` は、Chrome の指定プロファイルを使って HoYoLAB にアクセスし、ログイン状態の Cookie を取得します。

> ⚠️ 初回実行時またはプロファイルが未ログイン状態の場合、**ブラウザが自動で起動し、手動ログインが必要です**。

- ログイン画面が表示された場合は、アカウントでログインしてください
- ログイン完了後、ターミナルに戻って Enter を押すと Cookie 情報が `.env` に出力されます

Chrome のユーザーデータパスの例：
```
C:\Users\<あなたのユーザー名>\AppData\Local\Google\Chrome\User Data\hoyolab
```
---

## ❗ トークンが取得できない場合の手動方法

`.env` にトークンが正しく書き込まれない場合は、以下の手順で **開発者ツールからトークンを取得し、GitHub Secrets に直接登録**してください。

---

### ✅ ステップ 1：HoYoLAB チェックインページを開く

[https://act.hoyolab.com/bbs/event/signin/hkrpg/index.html?act_id=e202303301540311](https://act.hoyolab.com/bbs/event/signin/hkrpg/index.html?act_id=e202303301540311)

---

### ✅ ステップ 2：DevTools を開く

1. `F12` キーを押す（または右クリック → 検証）
2. `Application` タブを選択
3. 左メニューの `Storage > Cookies > https://*.hoyolab.com` を開く

---

### ✅ ステップ 3：Cookie 一覧をフィルターする

上部の検索欄に `v2` と入力すると、以下の3つのクッキーが見つかるはずです：

| Cookie名          | 説明                     |
|-------------------|--------------------------|
| `ltuid_v2`        | ユーザーID（数値）       |
| `ltoken_v2`       | セッション用トークン     |
| `cookie_token_v2` | API用の認証トークン      |

---

### ✅ ステップ 4：GitHub にトークンを登録する

1. フォークしたリポジトリの `Settings > Secrets and variables > Actions` に移動
2. `New repository secret` をクリックして、以下3つを追加：

| Secret Name        | 値（Cookieの中身）          |
|---------------------|-----------------------------|
| `LTUID`             | `ltuid_v2` の値（数値）     |
| `LTOKEN`            | `ltoken_v2` の値            |
| `COOKIE_TOKEN_V2`   | `cookie_token_v2` の値      |

---

## ✅ 自動チェックインの確認

`Actions` タブに移動し、ワークフローが正しく動作しているか確認できます。  
`Run workflow` を手動実行して、動作確認することも可能です。
