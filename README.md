# 英語1000本ノック 自動投稿

追加料金のかからない構成で、CSVからInstagram用カルーセル画像を生成し、公式APIで毎日投稿するプロジェクトです。

## 現在できること

- `data/posts.csv` で投稿原稿を管理
- 承認済みの原稿から1080×1350pxの画像を4枚生成
- 日本語フォントをmacOS/Linuxで自動検出

## 画像を生成する

通常のPython環境では、最初にPillowをインストールします。

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python src/generate_images.py --post-id 0001
```

Codex付属のPythonを使用できる場合は、追加インストールなしで実行できます。

```bash
/Users/fujikei/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  src/generate_images.py --post-id 0001
```

生成先は `generated/0001/01.jpg` から `04.jpg` です。

## 投稿データの状態

- `draft`: 下書き
- `approved`: 投稿可能
- `posted`: 投稿済み
- `error`: 投稿失敗

`.env` やアクセストークンはGitへ追加しないでください。

## Instagram投稿のドライラン

`.env.example` を `.env` にコピーし、まず公開画像URLだけ設定します。

```bash
cp .env.example .env
```

サンプル投稿を選択し、実際には投稿せず内容を確認します。

```bash
python3 src/post_instagram.py --post-id 0001
```

実投稿は、Meta側の設定とアクセストークンの確認後にだけ `--publish` を付けて実行します。

```bash
python3 src/post_instagram.py --post-id 0001 --publish
```

同じIDは `data/published.json` に記録され、誤って二重投稿しないよう停止します。

## GitHubでの無料定時実行

このプロジェクトは次のURLで生成画像を公開する構成です。

```text
https://keisan7777-rgb.github.io/english-1000-knock/generated/0001/01.jpg
```

- `pages.yml`: `main`への画像追加時にGitHub Pagesを更新
- `daily-instagram.yml`: 毎朝7時（日本時間）に当日分を投稿
- 手動実行時は既定でドライラン。`publish`を有効にした場合だけ実投稿

GitHubリポジトリの `Settings → Secrets and variables → Actions` に次の2件を登録します。

- `INSTAGRAM_ACCESS_TOKEN`
- `INSTAGRAM_USER_ID`

リポジトリ名は `english-1000-knock`、公開設定は `Public` を使用します。GitHub Pagesの公開元は `GitHub Actions` を選択します。
