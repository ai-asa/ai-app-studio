# AI App Studio 起動ガイド

AI App Studioは、複数のClaude Codeエージェントが並列に動作する様子をtmuxで可視化する、展示会向けのオーケストレーションシステムです。

## 目次
1. [システム概要](#システム概要)
2. [事前準備](#事前準備)
3. [クイックスタート](#クイックスタート)
4. [詳細な起動手順](#詳細な起動手順)
5. [基本的な使い方](#基本的な使い方)
6. [トラブルシューティング](#トラブルシューティング)
7. [高度な使い方](#高度な使い方)

## システム概要

### アーキテクチャ
```
┌─────────────┐     spawn      ┌──────────┐     tmux      ┌─────────────┐
│ Parent Agent│───────────────▶│   busd   │──────────────▶│ Child Agent │
│   (PMAI)    │                 │ (daemon) │                │  (impl:T001)│
└─────────────┘                 └──────────┘                └─────────────┘
       │                              │                             │
       │         busctl post          │          busctl post        │
       └──────────────────────────────┴─────────────────────────────┘
                            mailbox (file-based)
```

### 主要コンポーネント
- **busd**: メッセージバスデーモン（オーケストレータ）
- **busctl**: メッセージ投函用CLI
- **PMAI**: 親エージェント（タスク分解・管理）
- **Impl**: 子エージェント（実装ワーカー）

## 事前準備

### 1. 必要な環境
- Linux (Ubuntu推奨) または WSL
- tmux 3.2以上
- Python 3.10以上
- git 2.35以上
- Claude Code CLI（インストール済み）
- jq（オプション、ログ表示用）

### 2. 環境確認
```bash
# tmuxバージョン確認
tmux -V

# Pythonバージョン確認
python3 --version

# gitバージョン確認
git --version

# Claude Code確認
claude --version

# jq確認（オプション）
jq --version
```

### 3. AI App Studioのセットアップ
```bash
# リポジトリをクローン
git clone https://github.com/ai-asa/ai-app-studio.git
cd ai-app-studio

# 実行権限を付与
chmod +x bin/busctl

# ログディレクトリを作成（存在しない場合）
mkdir -p logs/raw state mbox/{bus,pmai}/in work
```

### 4. GitHub認証の設定（PR作成機能を使う場合）
```bash
# GitHub Personal Access Token の作成
# 1. https://github.com/settings/tokens にアクセス
# 2. "Generate new token (classic)" をクリック
# 3. 必要な権限を選択:
#    - repo (Full control of private repositories)
#    - workflow (Update GitHub Action workflows)
# 4. トークンをコピー

# .env.localファイルに設定（プロジェクトごと）
echo "GH_TOKEN=ghp_your_token_here" > .env.local

# またはグローバルに設定
export GH_TOKEN="ghp_your_token_here"

# ghコマンドでログイン（推奨）
gh auth login
# "GitHub.com" → "HTTPS" → "Paste an authentication token" を選択
```

## クイックスタート

### 統一ユニットシステム（新方式・推奨）

最新の統一ユニットシステムでは、操作が大幅に簡素化されています：

```bash
# 1. 作業したいプロジェクトに移動
cd /path/to/your-project

# 2. 要件定義ファイルを作成
cat > requirements.yml << 'EOF'
project_name: "My Web App"
version: 1.0
tasks:
  - name: "認証システムの実装"
    description: "ユーザー登録、ログイン、JWT認証を実装"
  - name: "APIサーバーの実装"
    description: "RESTful APIを実装"
EOF

# 3. busdデーモンを起動（別ターミナル）
python3 ~/tools/ai-app-studio/bin/busd.py

# 4. ルートユニットを起動（引数なし！）
~/tools/ai-app-studio/bin/busctl spawn

# 5. tmuxで動作を確認
tmux attach -t cc
```

これだけで、システムが自動的に：
- requirements.ymlを読み込んでタスクを分解
- 各タスクに対して子ユニットを生成
- 並列でタスクを実行
- 完了時にPRを作成（GH_TOKEN設定済みの場合）

### 従来方式（手動タスク投函）

手動でタスクを管理したい場合：

```bash
# 1. tmuxセッションを開始
tmux new -s demo

# 2. busdデーモンを起動
python3 bin/busd.py &

# 3. サンプルタスクを投函（別window: Ctrl-b c）
./bin/busctl spawn --task TEST001 --goal "Create hello.txt with 'Hello World'"

# 4. tmuxウィンドウを確認
tmux list-windows

# 5. 子エージェントの動作を観察
# Ctrl-b 2 でTEST001ウィンドウに切り替え
```

## 詳細な起動手順

### 1. 作業ディレクトリの準備
```bash
# AI App Studioのディレクトリに移動
cd /path/to/ai-app-studio

# 作業用gitリポジトリであることを確認
git status
```

### 2. tmuxセッションの作成
```bash
# 既存のセッションを確認
tmux ls

# 新規セッション作成（ccという名前）
tmux new-session -d -s cc -n DASH 'bash'

# または既にセッション内にいる場合
export TMUX_SESSION=cc
```

### 3. busdデーモンの起動
```bash
# バックグラウンドで起動（推奨）
python3 bin/busd.py > logs/busd.log 2>&1 &

# または、フォアグラウンドで起動（デバッグ用）
python3 bin/busd.py
```

### 4. ダッシュボードの設定（オプション）
```bash
# DASHウィンドウでログ監視を開始
tmux send-keys -t cc:DASH 'tail -F logs/bus.jsonl | jq -r . 2>/dev/null || tail -F logs/bus.jsonl' C-m
```

### 5. 要件定義からの自動実行

#### requirements.ymlを作成
```yaml
project_name: "My Project"
tasks:
  - id: T001
    name: "First task"
    goal: "Create hello.txt"
  - id: T002
    name: "Second task"  
    goal: "Create README.md"
```

#### 親エージェント（PMAI）を起動
```bash
# 親エージェントをspawn
./bin/busctl spawn \
  --task PMAI \
  --cwd work/pmai \
  --frame frames/pmai/CLAUDE.md \
  --goal "Process requirements.yml and spawn child tasks"
```

### 6. tmuxセッションで監視
```bash
# セッションにアタッチ
tmux attach -t cc

# tmux内でウィンドウを切り替え
# Ctrl-b 0 : DASHウィンドウ（ログ監視）
# Ctrl-b 1 : PMAIウィンドウ（親エージェント）
# Ctrl-b 2〜 : 子タスクウィンドウ（自動作成される）

# ウィンドウ一覧を表示
# Ctrl-b w
```

## 基本的な使い方

### 手動でタスクを投函
```bash
# タスク1: ファイル作成
./bin/busctl spawn \
  --task T001 \
  --cwd work/T001 \
  --frame frames/impl/CLAUDE.md \
  --goal "Create hello.txt with greeting message"

# タスク2: Pythonスクリプト作成
./bin/busctl spawn \
  --task T002 \
  --cwd work/T002 \
  --frame frames/impl/CLAUDE.md \
  --goal "Create calculator.py with basic arithmetic functions"
```

### 子エージェントへの指示送信
```bash
# 初期指示を送信（オプション）
./bin/busctl send \
  --to impl:T001 \
  --type instruct \
  --data '{"text":"Read frames/impl/CLAUDE.md and start working. Report progress via busctl post."}'
```

### 進捗の確認
```bash
# タスク状態を確認
cat state/tasks.json | jq .

# ログを確認
tail -f logs/bus.jsonl | jq .

# 特定タスクの生ログを確認
tail -f logs/raw/T001.raw
```

### メッセージの流れを理解する

1. **spawn**: 親→busd（新しい子エージェントを起動）
2. **send**: 親→子（指示を送信）
3. **post**: 子→親（進捗・結果を報告）

メッセージ例：
```json
// spawn
{"type":"spawn","task_id":"T001","data":{"goal":"Create hello.txt"}}

// post (進捗)
{"type":"log","from":"impl:T001","data":{"msg":"Task started"}}

// post (完了)
{"type":"result","from":"impl:T001","data":{"is_error":false,"summary":"Completed"}}
```

## トラブルシューティング

### busdが起動しない場合
```bash
# プロセス確認
ps aux | grep busd

# 既存プロセスを停止
pkill -f "python.*busd.py"

# ログ確認
tail -100 logs/busd.log

# デバッグモードで起動
python3 bin/busd.py
```

### tmuxウィンドウが作成されない場合
```bash
# mailbox確認
ls -la mbox/*/in/

# 未処理メッセージ確認
find mbox -name "*.json" -exec cat {} \; | jq .

# tmuxセッション確認
tmux ls
tmux list-windows -t cc
```

### メッセージが処理されない場合
```bash
# busdが動作しているか確認
ps aux | grep busd

# mailboxの権限確認
ls -la mbox/

# メッセージファイルの確認
find mbox -name "*.json" | head -5
```

### git worktreeエラー
```bash
# worktree一覧
git worktree list

# 不要なworktreeを削除
git worktree remove work/T001

# ブランチ確認
git branch -a
```

### Claude Codeが起動しない
```bash
# Claude Codeの動作確認
claude --version

# 権限エラーの場合（デモ環境のみ）
export CLAUDE_DANGEROUSLY_SKIP_PERMISSIONS=1
```

## 高度な使い方

### 複数プロジェクトの並列実行
```bash
# プロジェクトごとに別セッション
tmux new -s project1
python3 /path/to/ai-app-studio/bin/busd.py &

# 別ターミナルで
tmux new -s project2
TMUX_SESSION=project2 python3 /path/to/ai-app-studio/bin/busd.py &
```

### カスタムフレームの作成
```bash
# 新しいフレームを作成
mkdir frames/custom
cat > frames/custom/CLAUDE.md << 'EOF'
# Custom Agent Frame
カスタムエージェントの動作定義
EOF

# カスタムフレームで起動
./bin/busctl spawn --task CUSTOM001 --frame frames/custom/CLAUDE.md --goal "Custom task"
```

### 環境変数の活用
```bash
# セッション名を変更
export TMUX_SESSION=myproject

# Claude Codeコマンドをカスタマイズ
export CLAUDE_CMD="claude code --allowedTools 'Bash Edit Read' --add-dir ."

# プロジェクトルートを指定
export ROOT=/path/to/project
```

### ログの分析
```bash
# タスクごとの完了時間を集計
cat logs/bus.jsonl | jq -r 'select(.type=="result") | "\(.task_id): \(.data.summary)"'

# エラーのみ抽出
cat logs/bus.jsonl | jq 'select(.data.is_error==true)'

# 特定タスクのログのみ
cat logs/bus.jsonl | jq 'select(.task_id=="T001")'
```

### 停止と再開

#### システムの停止
```bash
# 1. busdを停止
pkill -f "python.*busd.py"

# 2. tmuxセッションを終了
tmux kill-session -t cc
```

#### クリーンアップ
```bash
# メールボックスクリア
rm -f mbox/*/in/*.json

# ログクリア（必要に応じて）
rm -f logs/raw/*.raw
rm -f logs/bus.jsonl

# 状態クリア
rm -f state/*.json

# ワークツリー削除
git worktree prune
for dir in work/*; do
  [ -d "$dir" ] && git worktree remove "$dir" || true
done
```

### セキュリティの考慮事項

1. **本番環境では`--dangerously-skip-permissions`を使用しない**
2. **作業ディレクトリを適切に制限する**
3. **機密情報を含むプロジェクトでは注意**

### パフォーマンスチューニング

```bash
# ポーリング間隔の調整（busd.py内）
# time.sleep(0.5) → time.sleep(0.1)  # より高速な応答

# ログローテーション
# logrotateの設定例
cat > /etc/logrotate.d/ai-app-studio << 'EOF'
/path/to/ai-app-studio/logs/*.jsonl {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
EOF
```

## よくある質問

**Q: 複数のbusdを同時に実行できますか？**
A: 異なるセッション名とworkspaceを使用すれば可能です。

**Q: 子エージェント同士で通信できますか？**
A: 現在のMVPでは未対応です。将来の拡張として計画されています。

**Q: タスクの優先順位を設定できますか？**
A: requirements.ymlでpriorityフィールドを定義できますが、現在は参考情報として使用されます。

**Q: エラーが発生したタスクを再実行するには？**
A: 同じタスクIDで再度spawnするか、新しいタスクIDで投函してください。

## 次のステップ

1. [docs/design.md](docs/design.md) - システム設計の詳細
2. [frames/pmai/CLAUDE.md](frames/pmai/CLAUDE.md) - 親エージェントのカスタマイズ
3. [frames/impl/CLAUDE.md](frames/impl/CLAUDE.md) - 子エージェントのカスタマイズ
4. テストスクリプトの実行: `./tests/bin/test_busctl_simple.sh`

## サポート

問題が発生した場合は、以下を確認してください：
1. ログファイル（logs/bus.jsonl、logs/busd.log）
2. システム要件（tmux、Python、gitのバージョン）
3. 権限設定（ファイル、ディレクトリのアクセス権）

---

**注意**: このシステムはデモ・展示会向けに設計されています。本番環境での使用には追加のセキュリティ対策が必要です。