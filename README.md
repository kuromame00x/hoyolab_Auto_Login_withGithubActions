# HoYoLAB Auto Login with GitHub Actions

このリポジトリは、HoYoLAB（原神 / スターレイル）のデイリーチェックインを GitHub Actions で自動化するスクリプトです。
崩壊3rdとZZZはAPIが対応していないため、APIとは別のチェックイン方法で開発中です。

```
.github/workflows/auto-checkin.yml
```
内の実行時間が7:00に設定されているので、必要に応じて変更してください。

---

## ✅ セットアップ手順

### 1. このリポジトリをフォークする

GitHub 上で本リポジトリをフォークしてください：

---

### 2. Cookie・トークンを取得する

ローカルで以下のファイルを実行し、必要なトークン情報を取得します。

```bash
python dist/get_cookie.exe
```
---

## ❗ トークンが取得できない場合の手動方法

`get_cookie.exe` を実行しても `.env` にトークンが正しく書き込まれない場合は、以下の手順で **開発者ツールからトークンを取得し、GitHub Secrets に直接登録**してください。

---

### ✅ ステップ 1：HoYoLAB チェックインページを開く

以下のURLをブラウザで開いて、ログイン状態にします：

[https://act.hoyolab.com/bbs/event/signin/hkrpg/index.html?act_id=e202303301540311](https://act.hoyolab.com/bbs/event/signin/hkrpg/index.html?act_id=e202303301540311)

---

### ✅ ステップ 2：DevTools を開く

1. `F12` キーを押す（または右クリック → 検証）
2. `Application` タブを選択
3. 左メニュー → `Storage` > `Cookies` > `https://*.hoyolab.com` をクリック

---

### ✅ ステップ 3：上部の検索バーで `v2` と入力

以下の3つのトークンが表示されるはずです：

| Cookie名          | 説明                     |
|-------------------|--------------------------|
| `ltuid_v2`        | ユーザーID（数値）       |
| `ltoken_v2`       | セッション用トークン     |
| `cookie_token_v2` | API用の認証トークン      |

---

### ✅ ステップ 4：GitHub にトークンを登録する

1. フォーク先リポジトリの `Settings > Secrets and variables > Actions` に移動
2. `New repository secret` を3つ作成：

| Secret Name        | 値（コピーした中身）           |
|---------------------|----------------------------------|
| `LTUID`             | `ltuid_v2` の値（数値のみ）      |
| `LTOKEN`            | `ltoken_v2` の値                 |
| `COOKIE_TOKEN_V2`   | `cookie_token_v2` の値           |



---
