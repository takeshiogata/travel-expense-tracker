# Travel Expense Tracker

チャットベースの旅行経費管理アプリ。自然言語で経費を入力すると、AIが自動的に費目を分類・記録します。

## 機能

- **チャット入力**: 「新幹線 14000円」「ホテル2泊で30000円」のように自然に入力
- **AI自動分類**: 費目カテゴリ（交通費、宿泊費、飲食費など）をAIが判定
- **曖昧さの確認**: 不明確な入力にはAIが質問で確認
- **スレッド管理**: 旅行ごとにスレッドを分離。日付で自動命名、リネーム可能
- **経費編集**: `#edit` キーワードで既存データをチャットから編集
- **集計表示**: カテゴリ別集計、合計金額をテーブルで表示
- **CSVエクスポート**: 経費データをCSVファイルでダウンロード
- **AI切り替え**: Claude / OpenAI をサイドバーで切り替え可能

## 技術スタック

| 項目 | 技術 |
|------|------|
| フロントエンド/UI | Streamlit |
| AI | Claude API (Haiku 4.5) / OpenAI API (GPT-4o mini) |
| データベース | Turso (libSQL) — クラウドSQLite |
| デプロイ | Streamlit Community Cloud |
| 言語 | Python 3.12 |

## ファイル構成

```
travel-expense-tracker/
├── app.py              # Streamlitメインアプリ（チャットUI + 集計タブ）
├── ai_client.py        # Claude/OpenAI API連携・経費JSON抽出
├── db.py               # Turso/SQLite CRUD操作
├── config.py           # カテゴリ・AIモデル・プロンプト定義
├── requirements.txt    # 依存パッケージ
├── DECISIONS.md        # 実装選択の根拠記録
├── .env.example        # 環境変数テンプレート
└── .gitignore
```

## セットアップ

### 1. 環境変数の設定

```bash
cp .env.example .env
```

`.env` を編集してAPIキーとTurso接続情報を記入:

```
ANTHROPIC_API_KEY=your-key
OPENAI_API_KEY=your-key
TURSO_DATABASE_URL=libsql://your-db.turso.io
TURSO_AUTH_TOKEN=your-token
```

Turso未使用の場合は `TURSO_*` を空にすればローカルSQLite (`data/expenses.db`) にフォールバックします。

### 2. Tursoデータベースの作成（オプション）

```bash
brew install tursodatabase/tap/turso
turso auth login
turso db create travel-expenses
turso db show travel-expenses --url
turso db tokens create travel-expenses
```

### 3. ローカル起動

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

venvを使わない起動:

```bash
.venv/bin/streamlit run app.py
```

### 4. Streamlit Community Cloudへのデプロイ

1. GitHubにリポジトリをpush（publicリポジトリが必要）
2. [share.streamlit.io](https://share.streamlit.io) でGitHubログイン
3. リポジトリ・ブランチ (`main`) ・メインファイル (`app.py`) を選択
4. Advanced settings > Secrets に環境変数をTOML形式で記入
5. Deploy

## 使い方

### 経費の入力

チャット欄に自然言語で入力するだけです。

```
新幹線 14000円
ホテル2泊で30000円
今日のランチ 1200円
スタバでコーヒー 500円
```

### 経費の編集

`#edit` を付けて入力すると、既存データを編集できます。

```
#edit 新幹線 12000円に変更
#edit タクシーをカテゴリ交通費に
```

### 集計の確認

チャットで聞くか、「集計・出力」タブで確認できます。

```
集計して
合計いくら？
カテゴリ別に教えて
```

## 費目カテゴリ

| カテゴリ | 例 |
|----------|-----|
| 交通費 | 新幹線、タクシー、バス、飛行機 |
| 宿泊費 | ホテル、旅館、Airbnb |
| 飲食費 | レストラン、カフェ、コンビニ |
| 観光・娯楽費 | 入場料、アクティビティ |
| 買い物 | お土産、日用品 |
| 通信費 | Wi-Fi、SIM |
| その他 | 上記に当てはまらないもの |

## API利用コスト目安

Claude Haiku 4.5 使用時、1回のチャット入力あたり約 **0.6円**。旅行5日間で100回入力しても約60円程度。

## 既知の制限事項

- 通貨は日本円のみ対応
- 個人利用を想定（認証機能なし）
- 会話履歴を全件AIに送るため、長いスレッドではコスト増加
- 割り勘計算機能はなし

## ライセンス

Private project.
