# AI エージェントオーケストレーションシステム：ユニットベース階層型設計

**版:** v1.1 (Simplified Unit-based Hierarchical System)
**目的:** 自律的に判断・行動する統一ユニットによる階層的タスク処理システム。ユーザーの負担を最小限にし、ユニットが自動的に必要な情報を取得・管理する。

---

## 0. まとめ（先に結論）

* **すべてのエージェントは「ユニット」として統一**され、同一の機能を持つ
* 各ユニットは**自律的にタスク分解を判断**し、必要に応じて子ユニットを生成
* **親子間のみ通信可能**な階層構造で、スケーラブルな並列処理を実現
* 各ユニットは**PR作成・マージの責任**を持ち、コンフリクト解決も行う
* **tmux による可視化**と**メッセージバス（busd）による信頼性**を両立

> 注意：本設計はCLAUDE.mdによるエージェント制御の実験的側面を含みます。完全な行動制御は保証されず、反復的な改善が必要です。

---

## 1. アーキテクチャ概要

### 1.1 ユニットの統一モデル

すべてのユニットは以下の共通機能を持つ：

1. **要件読み込み**: 全体要件と個別要件を理解
2. **タスク分析**: 分解可能性を判断
3. **分岐処理**:
   - 分解可能 → 子ユニット生成・管理
   - 分解不可 → 直接実装（TDD）
4. **PR管理**: 作成・マージ・コンフリクト解決
5. **報告**: 親への完了通知

**特殊ケース：ルートユニット**
- UNIT_ID="root"で識別
- 専用のframes/root/CLAUDE.mdを使用
- 必ずタスク分解を実行（実装はしない）
- 初期タスクは「requirements.ymlを読んでタスク分解」

### 1.2 階層構造の例

```
root/                            # ルートユニット（自動生成）
├── requirements.yml            # 全体要件（必須）
├── root-auth/                  # 認証システム（自動ID）
│   ├── task-breakdown.yml      # タスク分解リスト
│   ├── children-status.yml     # 子の状態追跡
│   ├── root-auth-login/        # ログイン機能
│   └── root-auth-token/        # トークン管理
└── root-api/                   # APIサーバー（自動ID）
    ├── task-breakdown.yml
    ├── children-status.yml
    ├── root-api-users/         # ユーザーAPI
    └── root-api-posts/         # 投稿API
```

### 1.3 簡素化された起動方法

```bash
# ユーザーが行う操作は以下のみ：
cd /path/to/project
vim requirements.yml  # 要件定義書を作成
busctl spawn         # ルートユニット起動（引数不要）
```

- UNIT_IDは自動生成（root → root-auth → root-auth-login）
- requirements.ymlは現在のディレクトリから自動検出
- 環境変数はbusdが自動設定

**注意**: 現在のバージョンでは、ルートユニットが子ユニットを生成する際に制限があります。
次期バージョンで`busctl spawn --from-breakdown`機能を追加予定です。

---

## 2. ユニットのライフサイクル

### 2.1 起動フェーズ

1. **環境変数（busdが自動設定）**
   ```bash
   UNIT_ID          # 自動生成: root, root-api, root-api-users
   PARENT_UNIT_ID   # 自動設定: 親のUNIT_ID
   TARGET_REPO      # 自動設定: カレントディレクトリ
   ```

2. **コンテキスト読み込み**
   - `./requirements.yml` （必須）
   - `../{PARENT_UNIT_ID}/task-breakdown.yml` （親のタスク分解）
   - `../{PARENT_UNIT_ID}/scoped-requirements.yml` （親が作成した要件）

### 2.2 判断フェーズ

タスク分解の判断基準：
- 受け入れ基準が複数存在
- 異なる技術領域にまたがる
- 依存関係のある複数機能
- 実装規模が大きい

### 2.3 親ユニットとしての動作

1. **タスク分解ファイルの作成（親が作成するチェックリスト）**
   ```yaml
   # task-breakdown.yml - 親が作成し、状態を管理するファイル
   parent_unit: root-api
   total_tasks: 3
   tasks:
     - id: users
       description: "ユーザー管理APIの実装"
       status: pending  # 親が更新: pending -> completed
     - id: posts
       description: "投稿APIの実装"
       status: pending
     - id: auth
       description: "認証ミドルウェアの実装"
       status: pending
   ```
   
   **役割**: 親がタスクを子タスクに分解した結果を記録し、進捗を追跡する

2. **子の状態追跡ファイル（busdが自動更新）**
   ```yaml
   # children-status.yml - busdが子の報告に基づいて自動更新
   children:
     - unit_id: root-api-users
       status: running
       started_at: "2025-01-09T10:00:00Z"
     - unit_id: root-api-posts
       status: pending
     - unit_id: root-api-auth  
       status: completed
       completed_at: "2025-01-09T11:00:00Z"
       pr_number: 123
   ```
   
   **役割**: 子ユニットの実行状態をbusdが自動的に記録（親は参照のみ）

3. **子ユニット生成**
   ```bash
   # task-breakdown.ymlに基づいて子を生成（次期バージョン）
   busctl spawn --from-breakdown
   
   # 現在のバージョンでは個別に生成が必要
   # TODO: --from-breakdown機能の実装が必要
   ```

4. **子からの通知受信と処理**
   - **受動的な通知受信**: 子がsend-keysで `[CHILD:unit-id] Status: completed, Message: Done` を送信
   - 親は通知を受けて、task-breakdown.ymlのstatusを更新
   - **能動的な監視は行わない**（watchやgrepは使用しない）
   - すべての子タスク完了まで待機

4. **統合とマージ**
   - 各子のPRを自身のブランチにマージ
   - コンフリクト発生時は解決を試みる

5. **上流への報告**
   - すべての子タスク完了後、自身も完了報告
   - 親がいない場合（ルート）は最終報告

### 2.4 実装ユニットとしての動作

1. **TDD実装**
   - テストファースト開発
   - 定期的な進捗報告

2. **PR作成**
   ```bash
   gh pr create --title "[${UNIT_ID}] タスク完了" \
                --base "${PARENT_BRANCH}"
   ```

3. **完了報告**
   ```bash
   busctl post --type result --data '{"is_error": false}'
   ```

---

## 3. 通信プロトコル

### 3.1 メッセージタイプ（拡張版）

```json
{
  "type": "spawn",           // ユニット生成
  "type": "task_decomposed", // タスク分解完了通知
  "type": "progress",        // 進捗報告
  "type": "child_completed", // 子タスク完了
  "type": "result",          // 最終結果
  "type": "pr_created",      // PR作成通知
  "type": "merge_request",   // マージ要求
  "type": "conflict_found",  // コンフリクト発生
  "type": "query",          // 親子間の質問
  "type": "response"        // 親子間の回答
}
```

### 3.2 双方向通信の実現

#### 子→親通信（send-keys方式）

Claude Codeの対話式特性を活用し、`tmux send-keys`で直接親のTTYに通知を送信：

```python
# busd内での実装
def notify_parent_unit(parent_unit_id, child_unit_id, status, message):
    parent_pane = pane_map.get(parent_unit_id)
    if not parent_pane:
        return
    
    # 通知フォーマット
    notification = f"[CHILD:{child_unit_id}] Status: {status}, Message: {message}"
    
    # 安全な送信（現在の実装と同じ方式）
    sh(f"tmux send-keys -t {parent_pane} -l {shlex.quote(notification)}")
    sh(f"tmux send-keys -t {parent_pane} Enter")
    
    time.sleep(0.1)  # 連続通知対策
```

**通知フォーマット例**：
```
[CHILD:root-api-users] Status: completed, Message: User API implementation done
[CHILD:root-api-auth] Status: error, Message: JWT implementation failed
[CHILD:root-api-posts] Status: pr_created, Message: PR #123 created
```

**実装上の配慮**：
- `shlex.quote()`: 特殊文字のエスケープ
- `-l`オプション: リテラルテキストとして送信（tmuxの解釈を防ぐ）
- Enterキーの分離送信: テキストとEnterを別々に送信
- 適切な待機時間: 連続通知時に0.1秒の間隔

#### 親→子通信

既存の`busctl send`コマンドを使用（handle_sendで処理）：

```bash
busctl send --to unit:root-api-users --type instruct --data '{"command": "review", "pr": "123"}'
```

#### 通信の利点

1. **非同期性**: 親が処理中でもメッセージをキューイング
2. **視認性**: tmux上で通信が可視化される
3. **確実性**: TTYに直接送信されるため見落としなし
4. **識別性**: どの子からの通知か明確

---

## 4. ディレクトリ構造（簡素化版）

```
ai-app-studio/                     # AI App Studioツール本体
├── frames/                        # ユニット指示書
│   ├── root/                     
│   │   └── CLAUDE.md            # ルートユニット専用
│   └── unit/                     
│       └── CLAUDE.md            # 通常ユニット用
└── bin/                          # 実行ファイル
    ├── busctl                   # CLIツール
    └── busd.py                  # デーモン

project/                            # ユーザーのプロジェクト
├── requirements.yml               # 全体要件（必須）
├── .ai-app-studio/               # AI App Studio管理ディレクトリ
│   ├── mbox/                     # メッセージボックス
│   ├── logs/                     # ログ
│   └── state/                    # 状態管理
└── ...

project-root/                       # ルートユニットのworktree
├── requirements.yml               # 全体要件（git worktreeにより自動的に存在）
├── task-breakdown.yml            # タスク分解リスト
├── children-status.yml           # 子の状態
├── CLAUDE.md                     # プロジェクト指示書（コピー）
├── .env.local                    # 環境設定（コピー、存在する場合）
├── .claude/                      # Claude設定（コピー、存在する場合）
└── ...

project-root-api/                   # 子ユニットのworktree 
├── requirements.yml               # 全体要件（git worktreeにより自動的に存在）
├── .parent_unit                  # 親ユニットID記録ファイル
├── scoped-requirements.yml       # 親からの要件
├── CLAUDE.md                     # プロジェクト指示書（コピー）
├── .env.local                    # 環境設定（コピー、存在する場合）
├── .claude/                      # Claude設定（コピー、存在する場合）
└── src/                          # 実装コード
```

**ポイント**：
- requirements.ymlはgit worktreeの特性により自動的に各worktreeに存在（コピー不要）
- 親ユニット：task-breakdown.yml、children-status.ymlを自動生成
- 子ユニット：.parent_unitファイルで親を記録
- CLAUDE.md、.env.local、.claudeディレクトリはworktreeにコピー
- ユニット管理情報はworktree内にYAMLで保存
- .ai-app-studio/は最小限の情報のみ保持

---

## 5. ブランチ戦略

### 5.1 命名規則

```
feat/root                    # ルートユニット
feat/root-api               # APIユニット（親: root）
feat/root-api-users         # ユーザーAPI（親: root-api）
feat/root-api-users-crud    # CRUD実装（親: root-api-users）
```

### 5.2 マージフロー

1. 子ユニットが親ブランチに向けてPR作成
2. 親ユニットがレビュー・マージ
3. コンフリクト発生時は親ユニットが解決
4. 最終的にルートがmainにマージ

---

## 6. 実装上の課題と対策

### 6.1 エージェント制御の最適化

**課題**: CLAUDE.mdの内容が長すぎるとコンテキストを圧迫
**対策**: 
- 必要最小限の指示に絞る
- 具体例は別ファイルに分離
- 明確な判断フローの提供

### 6.2 自動化の徹底

**課題**: ユーザーが複雑なパラメータを指定する負担
**対策**:
- UNIT_IDの自動生成（階層構造に基づく）
- requirements.ymlの固定位置（./requirements.yml）
- 環境変数のbusdによる自動設定

**課題**: ルートユニットからの子ユニット生成と重複回避
**対策**:
- `busctl spawn --from-breakdown`機能の実装予定
- task-breakdown.ymlから自動的に子ユニットを生成

**重要な設計課題**: spawn済み判定の方法
- 問題: task-breakdown.ymlのstatusは初期値が全て"pending"
- 考慮事項:
  - task-breakdown.yml: タスクの「完了状態」を管理（pending/completed）
  - children-status.yml: 子ユニットの「実行状態」を管理（running/completed）
- 実装案:
  1. children-status.ymlの子ユニット一覧でspawn済みを判定
  2. task-breakdown.ymlに"spawned"状態を追加
  3. 別途spawn-tracking.ymlで管理

### 6.3 コンフリクト管理

**課題**: 並列開発によるコンフリクト増加
**対策**:
- セマンティックマージの活用
- 早期統合の促進
- 依存関係の明示的管理

### 6.4 階層の深さ

**課題**: 深すぎる階層による複雑性
**対策**:
- ユニットの判断基準を調整
- 実用的には3-4層程度を想定

---

## 7. セキュリティとフェイルセーフ

- **サンドボックス**: 各ユニットは独立worktreeで作業
- **権限制限**: 必要最小限の権限のみ付与
- **監査ログ**: すべての操作をbus.jsonlに記録
- **デッドロック回避**: タイムアウトと強制終了機能

---

## 8. 将来の拡張性

- **非同期通信**: より効率的な親子間通信
- **分散実行**: 複数マシンでの並列実行
- **外部ツール統合**: CI/CD、監視ツール
- **学習機能**: 過去の判断パターンの活用

---

## 9. 実装フェーズ

### Phase 1: 基盤整備（現在）
- 統一フレーム作成
- busctl/busdの拡張
- 基本的な親子通信

### Phase 2: PR/マージ機能
- ghコマンド統合
- 自動マージ機能
- 基本的なコンフリクト対処

### Phase 3: 高度な協調
- 複雑なコンフリクト解決
- 動的な再タスク分解
- パフォーマンス最適化

---

## 付録: 実験的性質について

本システムは以下の実験的要素を含みます：

1. **LLMの自律性**: ユニットの判断品質は予測困難
2. **スケーラビリティ**: 大規模階層での動作は未検証
3. **エラー処理**: 想定外の状況への対応力は限定的

継続的な改善とフィードバックが必要です。

---

## 10. Web クライアント設計

### 10.1 概要

AI App Studioの実行状況をリアルタイムで可視化するWebベースのモニタリングツール。
タスクの階層構造と実行状態を直感的に表示し、各タスクの詳細ログを確認できる。

### 10.2 設計方針

- **最小限の実装**: 必要最低限の機能に絞り、シンプルに保つ
- **リアルタイム性**: WebSocketを使用して即座に状態を反映
- **直感的なUI**: クリックでログ表示、色でステータスを識別

### 10.3 アーキテクチャ

#### バックエンド構成
```
web-client/backend/
├── main.py        # FastAPIアプリケーション
├── monitor.py     # ファイル監視とイベント送信
└── models.py      # データモデル定義
```

- **FastAPI**: 高速で軽量なWebフレームワーク
- **WebSocket**: リアルタイム通信
- **watchdog**: ファイル変更監視

#### フロントエンド構成
```
web-client/frontend/
├── index.html     # メインHTML
├── app.js         # Reactアプリケーション
└── style.css      # 最小限のスタイリング
```

- **React**: シンプルな状態管理とコンポーネント化
- **WebSocket Client**: サーバーとのリアルタイム通信
- **Tailwind CSS**: ユーティリティファーストのCSS

### 10.4 データフロー

1. **初期データ取得**
   - `/api/tasks`でタスク階層を取得
   - 各タスクのworktreeから階層情報を構築

2. **リアルタイム更新**
   - `bus.jsonl`の変更を監視
   - `tasks.json`の変更を監視
   - 変更があればWebSocketで通知

3. **ログ表示**
   - タスククリック時に`/api/logs/{task_id}`でログ取得
   - `logs/raw/{task_id}.raw`から読み込み

### 10.5 API仕様

#### REST API

```http
GET /api/tasks
Response:
{
  "root": {
    "id": "root",
    "status": "pending",
    "children": ["root-frontend", "root-backend", "root-infrastructure"]
  },
  "root-frontend": {
    "id": "root-frontend",
    "status": "completed",
    "children": []
  },
  ...
}

GET /api/logs/{task_id}
Response:
{
  "task_id": "root-backend",
  "content": "Building backend API...\nError: Module not found...",
  "last_updated": "2025-01-10T10:30:00Z"
}
```

#### WebSocket メッセージ

```json
// タスク状態更新
{
  "type": "task_update",
  "task_id": "root-backend",
  "status": "error",
  "message": "Build failed"
}

// 新規タスク追加
{
  "type": "task_added",
  "task_id": "root-auth",
  "parent_id": "root"
}
```

### 10.6 UI設計

#### レイアウト
```
┌─────────────────────────────────────────────┐
│ AI App Studio Monitor            [自動更新] │
├─────────────────────────────────────────────┤
│                                             │
│ root ⏳                                     │
│ ├─ root-frontend ✅ Frontend completed      │
│ ├─ root-backend ❌ Build failed            │
│ └─ root-infrastructure ⏳                   │
│                                             │
├─────────────────────────────────────────────┤
│ ▼ root-backend のログ                       │
│ Building backend API...                     │
│ Installing dependencies...                  │
│ Error: Module 'express' not found           │
│ ...                                         │
└─────────────────────────────────────────────┘
```

#### ステータス表示
- ⏳ **実行中** (pending): タスクが進行中
- ✅ **完了** (completed): 正常終了
- ❌ **エラー** (error): エラーで終了

### 10.7 実装の注意点

1. **状態の整合性**
   - `tasks.json`と`bus.jsonl`の情報を統合
   - 各worktreeの`children-status.yml`も参照

2. **パフォーマンス**
   - ログファイルは大きくなる可能性があるため、末尾のみ取得
   - WebSocketメッセージは必要最小限に

3. **エラーハンドリング**
   - ファイルが存在しない場合の処理
   - WebSocket切断時の再接続

### 10.8 将来の拡張

- タスクの手動制御（停止、再実行）
- ログのフィルタリング・検索
- 実行時間の統計表示
- エラーの集約表示