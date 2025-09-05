# AI App Studio - tmux可視化 + ファイルベース・メッセージバス

展示会向けのAIエージェントオーケストレーションシステムです。
複数のClaude Codeエージェントが並列に動作する様子をtmuxで可視化し、ファイルベースのメッセージバスで信頼性の高い通信を実現します。

## 特徴

- **tmux可視化**: 各エージェントの動作をリアルタイムで観察可能
- **ファイルベース通信**: mailboxパターンによる堅牢なメッセージング
- **並列実行**: 複数タスクを独立したgit worktreeで同時実行
- **透明性**: すべての通信がJSONファイルとして記録される

## システム構成

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

## 前提条件

- tmux 3.2以上
- git 2.35以上  
- Python 3.10以上
- Claude Code CLI（`claude`コマンド）

## クイックスタート

### 1. インストール

```bash
# リポジトリをクローン
git clone https://github.com/your-org/ai-app-studio.git
cd ai-app-studio
```

### 2. 基本的な使い方

```bash
# 1. 作業したいプロジェクトディレクトリに移動
cd /path/to/your-project

# 2. 別ターミナルでbusdデーモンを起動（現在のディレクトリがTARGET_REPOになる）
python3 ~/tools/ai-app-studio/bin/busd.py

# または、任意の場所から起動して引数で指定
python3 ~/tools/ai-app-studio/bin/busd.py /path/to/your-project

# 3. 別ターミナルで.ai-app-studioディレクトリに移動してPMAI（親エージェント）をspawn
cd .ai-app-studio
~/tools/ai-app-studio/bin/busctl spawn --task PMAI --cwd work/PMAI --frame ~/tools/ai-app-studio/frames/pmai/CLAUDE.md --goal "Process requirements.yml"

# 4. tmuxセッションで動作を確認
tmux attach -t cc
```

**TARGET_REPO機能**: AI App Studioは、指定されたターゲットリポジトリ（デフォルトは現在のディレクトリ）の`requirements.yml`を読み込みます。作業ディレクトリは`TARGET_REPO/.ai-app-studio/`に作成されます。

```bash
# .gitignoreに追加することを推奨
.ai-app-studio/
```

### 3. 手動でタスクを管理する場合

```bash
# PATHを一時的に追加
export PATH="/path/to/ai-app-studio/bin:$PATH"

# 手動でタスクを投函
busctl spawn --task T001 --goal "Create hello.txt"
```

### 4. tmuxセッション内での操作

```bash
# tmuxセッション内でのペイン移動
Ctrl+B → 矢印キー

# Claude Codeの初回起動時
# セキュリティ警告が表示されたら "2. Yes, I accept" を選択
```

### 5. 進捗確認

```bash
# リアルタイムログ
tail -F logs/bus.jsonl | python3 -m json.tool

# タスク状態
cat state/tasks.json | python3 -m json.tool

# tmuxで各エージェントを確認
tmux list-windows -t cc
```

## ディレクトリ構造

```
.
├── bin/
│   ├── busctl       # メッセージ投函CLI
│   └── busd.py      # オーケストレータデーモン
├── frames/
│   ├── pmai/        # 親エージェント用フレーム
│   └── impl/        # 子エージェント用フレーム
├── mbox/            # メッセージボックス（通信用）
│   ├── bus/in/      # デーモン宛メッセージ
│   └── pmai/in/     # 親エージェント宛メッセージ
├── logs/
│   ├── raw/         # 各paneの生ログ
│   └── bus.jsonl    # 集約イベントログ
├── state/
│   ├── tasks.json   # タスク状態
│   └── panes.json   # tmux paneマッピング
└── work/            # 各タスクの作業ディレクトリ（git worktree）
```

## 基本的な使い方

### タスクの投函（spawn）

```bash
./bin/busctl spawn \
  --task T001 \
  --cwd work/T001 \
  --frame frames/impl/CLAUDE.md \
  --goal "Implement user authentication"
```

### メッセージ送信（send）

```bash
./bin/busctl send \
  --to impl:T001 \
  --type instruct \
  --data '{"action": "start", "priority": "high"}'
```

### 進捗報告（post）

```bash
./bin/busctl post \
  --from impl:T001 \
  --type result \
  --task T001 \
  --data '{"is_error": false, "summary": "Task completed"}'
```

## フレームの仕組み

### 親フレーム（PMAI）
- `requirements.yml`を読み込み、タスクに分解
- 各タスクをbusctl spawnで子エージェントに割り当て
- 必要に応じて初期指示を送信

### 子フレーム（Impl）
- 割り当てられたタスクを実行
- busctl postで進捗と結果を報告
- 独立したworktreeで他タスクと干渉なく作業

## トラブルシューティング

### tmuxセッションが見つからない
```bash
# セッション一覧を確認
tmux ls

# 新しいセッションを作成
export TMUX_SESSION=demo
python3 bin/busd.py
```

### メッセージが処理されない
```bash
# mailboxの状態確認
find mbox -name "*.json" | head

# busdのログ確認
tail -F logs/bus.jsonl
```

### git worktreeエラー
```bash
# worktree一覧
git worktree list

# 不要なworktreeを削除
git worktree remove work/T001
```

## 開発者向け

### テスト実行
```bash
# busctlテスト
./tests/bin/test_busctl_simple.sh

# busdテスト
python3 tests/bin/test_busd.py

# フレームテスト
python3 tests/frames/test_frames.py
```

### 拡張ポイント
- `handle_*`関数でメッセージタイプを追加
- フレームをカスタマイズして特定用途に特化
- MCPツールとの連携も可能

## 既知の問題と今後の改善

### TARGET_REPO問題
現在の実装では、PMAIがAI App Studio自体のrequirements.ymlを読み込んでしまいます。
他のプロジェクトに対して実行する場合は、明示的にパスを指定する必要があります。

今後のバージョンでは、環境変数`TARGET_REPO`で作業対象リポジトリを指定できるように改善予定です。

## requirements.ymlの例

```yaml
project_name: "My Awesome Project"
version: 1.0
tasks:
  - id: T001
    name: "プロジェクト構造の作成"
    goal: "src/, tests/, docs/ディレクトリを作成し、基本的な.gitignoreを設置"
    type: setup
    
  - id: T002
    name: "READMEの作成"
    goal: "プロジェクトの概要、使い方、ライセンス情報を含むREADME.mdを作成"
    type: documentation
    
  - id: T003
    name: "Hello Worldの実装"
    goal: "src/main.pyに簡単なHello Worldプログラムを実装"
    type: implementation
```

## ライセンス

MIT License - 詳細はLICENSEファイルを参照してください。
