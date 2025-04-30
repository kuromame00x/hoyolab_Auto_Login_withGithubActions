# HoYoLAB Auto Login with GitHub Actions

このリポジトリは、HoYoLAB（原神 / スターレイル）のデイリーチェックインを GitHub Actions で自動化するスクリプトです。
崩壊3rdとZZZはAPIが対応していないため、APIとは別のチェックイン方法で開発中です。

---

## ✅ セットアップ手順

### 1. このリポジトリをフォークする

GitHub 上で本リポジトリをフォークしてください：

👉 [Fork this repository](https://github.com/kuromame00x/hoyolab_Auto_Login_withGithubActions)

---

### 2. Cookie・トークンを取得する

ローカルで以下のスクリプトを実行し、必要なトークン情報を取得します。

```bash
python src/get_cookie.py
