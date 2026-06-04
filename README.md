# WC2026 データ配信（GitHub）

このフォルダの JSON を **GitHub の公開リポジトリ** に置くと、アプリが起動時に取得して反映します。
ファイルを編集して push するだけで、**アプリを出し直さずに全ユーザーへ配信**できます。

## ファイル
- `squads.json` … 各国の確定メンバー（teamId → GK/DF/MF/FW の名前配列）
- `news.json` … 速報（`{"ja":[...], "en":[...]}` / 各要素は `time,title,body,tag`）
- `meta.json` … バージョン情報（任意）

## セットアップ手順
1. GitHub で **公開（public）リポジトリ** を作る（例: `wc26-data`）。
2. この `data/` の中身（`squads.json`, `news.json` など）をリポジトリに push する。
   - 置き方は自由（リポジトリ直下でも `data/` フォルダでも可）。
3. Raw のベースURLを確認する。形式:
   ```
   https://raw.githubusercontent.com/<ユーザー名>/<リポジトリ>/<ブランチ>/<パス>
   例: https://raw.githubusercontent.com/yourname/wc26-data/main/data
   ```
4. アプリの `lib/remote.dart` の `baseUrl` にそのURL（末尾スラッシュなし）を設定。
5. ビルドして配布。以後は **JSONを編集→commit→push** で配信完了。

## 動作
- 起動時：端末キャッシュを即表示（オフラインでも前回分が出る）。
- 起動直後：GitHubから最新を取得 → 変わっていれば差し替え＆再描画。
- 配信元（`baseUrl`）未設定の間は、アプリ同梱データで動作（フォールバック）。

## 注意
- `raw.githubusercontent.com` は数分のCDNキャッシュがあるため、反映に少し時間がかかることがあります。
- 公開リポジトリなので、機密情報は置かないこと（配信データは公開前提）。
- プッシュ通知（試合中の即時通知）は別途サーバー（APNs）が必要です。これは「起動時のデータ更新」の仕組みです。
