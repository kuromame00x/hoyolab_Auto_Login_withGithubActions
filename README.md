# HoYoLAB Auto Login with GitHub Actions

このリポジトリは、HoYoLAB（原神 / スターレイル）のデイリーチェックインを GitHub Actions で自動化するスクリプトです。
崩壊3rdとZZZはAPIが対応していないため、APIとは別のチェックイン方法で開発中です。

---

## ✅ セットアップ手順

### 1. このリポジトリをフォークする

GitHub 上で本リポジトリをフォークしてください：

---

### 2. Cookie・トークンを取得する

ローカルで以下のファイルを実行し、必要なトークン情報を取得します。

```bash
python dist/get_cookie.exe


