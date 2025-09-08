# AI App Studio Web Client

AI App Studioの実行状況をリアルタイムで可視化するWebベースのモニタリングツールです。

## 機能

- **タスク階層表示**: ユニットの親子関係を視覚的に表示
- **リアルタイム更新**: WebSocketによる即時状態反映
- **ログビューア**: 各タスクの実行ログを表示
- **ステータス表示**: ⏳実行中、✅完了、❌エラーなどを分かりやすく表示

## セットアップ

### 必要な環境

- Python 3.8以上
- FastAPI関連パッケージ

### インストール

```bash
# 必要なパッケージをインストール
pip install fastapi uvicorn websockets watchdog
```

## 起動方法

### 1. 監視したいプロジェクトで実行

```bash
# プロジェクトディレクトリに移動
cd /path/to/your/project

# AI App Studio Web Clientを起動
TARGET_REPO=$(pwd) /path/to/ai-app-studio/web-client/start.sh
```

### 2. 環境変数を設定して実行

```bash
export TARGET_REPO=/path/to/your/project
cd /path/to/ai-app-studio/web-client
./start.sh
```

### 3. 直接実行

```bash
cd /path/to/ai-app-studio/web-client
TARGET_REPO=/path/to/your/project python -m uvicorn backend.main:app --port 8000
```

## 使い方

1. ブラウザで `http://localhost:8000` を開く
2. 左側のタスク階層からタスクをクリック
3. 右側にそのタスクのログが表示される
4. タスクの状態はリアルタイムで更新される

## API仕様

### REST API

- `GET /api/tasks` - タスク階層を取得
- `GET /api/logs/{task_id}` - 特定タスクのログを取得
- `GET /health` - ヘルスチェック

### WebSocket

- `ws://localhost:8000/ws` - リアルタイム更新用WebSocket

メッセージタイプ:
- `task_update` - タスク状態の更新
- `task_added` - 新規タスクの追加
- `log_update` - ログの更新

## アーキテクチャ

### バックエンド

- **FastAPI**: 高速なWebフレームワーク
- **WebSocket**: リアルタイム通信
- **watchdog**: ファイル監視

### フロントエンド

- **React**: UIフレームワーク（CDN版）
- **Tailwind CSS**: スタイリング（CDN版）
- **WebSocket Client**: リアルタイム更新

## 開発

### テスト実行

```bash
# ユニットテスト
cd web-client
python -m pytest tests/

# 統合テスト
python tests/test_integration.py
```

### 監視対象ファイル

- `.ai-app-studio/logs/bus.jsonl` - イベントログ
- `.ai-app-studio/state/tasks.json` - タスク状態
- `.ai-app-studio/logs/raw/{task_id}.raw` - 各タスクのログ

## トラブルシューティング

### WebSocketが接続できない

- ファイアウォールやプロキシの設定を確認
- ポート8000が使用可能か確認

### ファイル監視が動作しない

- TARGET_REPOが正しく設定されているか確認
- .ai-app-studioディレクトリが存在するか確認

### ログが表示されない

- `logs/raw/{task_id}.raw`ファイルが存在するか確認
- ファイルの読み取り権限を確認