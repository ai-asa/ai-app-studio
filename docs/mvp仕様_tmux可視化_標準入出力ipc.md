# MVP設計ドキュメント

## 0. 目的（今回のMVPで達成したいこと）

* 要件定義書から**タスク分解**を行い、タスクごとに**Git worktree＋ブランチ**を切る。
* タスクごとに\*\*開発AIエージェント（CLIプロセス）\*\*を起動し、**自動的に実装→コミット→PR作成**まで到達する。
* **tmuxは可視化専用**（各エージェントのログを並列で“会社っぽく”見せる）。
* **Slackへ進捗通知のみ**（承認なし／開始・PR・CI・完了・失敗）。
* 補佐AIは**今回は省略**。権限確認は `--dangerously-skip-permissions` により全自動（MVP）。

---

## 1. スコープ/非スコープ

**スコープ**

* タスク分解（簡易）とタスクリストの生成
* worktree/ブランチ作成、エージェント起動、PR作成
* 標準入出力(JSON Lines)による**親子プロセスIPC**
* Slack連携（通知、スレッドでの会話集約）
* tmuxでログ表示

**非スコープ（MVPではやらない）**

* 補佐AIのYes/No審査の本格実装（自動YES＋人手Slack承認で代替）
* RAG/長期メモリ/高度なセマンティック計画
* 分散メッセージング（Redis/NATS等）
* 本番環境へのデプロイ・運用自動化（今回はローカル/PoC想定）

---

## 2. 全体アーキテクチャ（論理）

```
┌────────────┐        Slack（ユーザー）
│  Orchestrator  │──postMessage（進捗のみ）──┐
│  (PMAI/親)     │                              │
├──────┬────────┤                              │
│IPC(JSONL)      │                              │
│                │                              │
│    ┌──────────┴───────┐                      │
│    │ Agent(T001) CLI  │  stdout→ログ→tmux     │
│    ├──────────────────┤                      │
│    │ Agent(T002) CLI  │  stdout→ログ→tmux     │
│    └──────────────────┘                      │
│      ↑ cwd=各worktree                        │
└──────┴───────────────────────────────────────┘
        ↓ git/gh CLI
      Git repo（origin） ←→ GitHub（PR/CI/Auto-merge など）
```

* Orchestratorが**唯一の制御点**。エージェントは**子プロセス**として起動し、**stdin/stdoutで会話**。
* tmuxは**ログファイルの `tail -f` を表示**する“窓”。
* Slackはタスク完了報告の場。将来的にはAIエージェントの質問や承認申請の場へ。

---

## 3. 主要コンポーネントと責務

### 3.1 Orchestrator（親/制御平面）

* `requirements.yaml`を読み、**タスク分解**→`tasks.yaml`生成
* 各タスクに対し**worktree＋ブランチ**作成
* タスクごとに**Agent CLIを起動**（cwd=worktree）。**JSON Linesで指示/回収**
* 進捗とログを**ファイル保存**（tmuxはそれを表示）
* **PR作成/更新**（必要なら`gh` CLI使用）
* Slackに**進捗**（開始/PR/CI/完了/失敗）を投稿

### 3.2 Agent CLI（子/作業者）

* 親からの**1行JSON**を読み取り、

  * ファイル編集/依存導入/テスト実行 などを実行
  * 結果を**1行JSONで返す**
* 例：`{"task_id":"T001","event":"patch_applied","files":[...]}\n`

### 3.3 Slack App（Bot）

* `chat.postMessage`で最初の投稿
* メッセージは**スレッド管理**（`thread_ts`）でタスクごとに会話を集約

### 3.4 tmux（可視化）

* `libtmux`等でpane生成
* 各paneは`tail -f logs/agent-T001.log`のようなビュー専用

---

## 4. 典型シナリオ（シーケンス）

### 4.1 要件→分解→開発→PR

```
User → Orchestrator: requirements.yaml 置く
Orchestrator: タスク分解→tasks.yaml
Orchestrator: T001/T002 用 worktree + branch 作成
Orchestrator: Agent(T001/T002)を起動（cwd=各worktree）
Orchestrator → Agent(T001): {"cmd":"start","goal":"..."}\n
Agent(T001): 実装→テスト→stdoutでイベント報告
Orchestrator: ログ保存→Slackへ進捗（開始/PR/CI/完了/失敗）を投稿
Orchestrator: git add/commit/push → PR作成（gh）
CI: テストOK
Orchestrator: 自動マージ
```

### 4.2 進捗通知の例

```
T001 START: worktree=../worktrees/T001 branch=feature/T001-backend
T001 PR: https://github.com/org/repo/pull/123
T001 CI: passed
T001 DONE
```

---

## 5. IPC設計（標準入出力 / JSON Lines）

### 5.1 ルール

* **1メッセージ=1行JSON**（末尾に`\n`）。行境界で確実に分割。
* 文字コードはUTF-8。`stdout.flush()`を徹底（バッファ詰まり防止）。
* 親（Orchestrator）は**ノンブロッキング読取**（async）で複数Agentを同時監視。
* すべてのメッセージに`task_id`を含め、**ロギング/スレッド紐付け**に用いる。

### 5.2 代表メッセージ（例）

* 親→子（開始）

```json
{"task_id":"T001","cmd":"start","goal":"implement login","tests":["pytest -q"],"constraints":["no-secret-hardcode"]}
```

* 子→親（ACK）

```json
{"task_id":"T001","event":"ack_start"}
```

* 子→親（進捗）

```json
{"task_id":"T001","event":"log","message":"installed deps"}
```

* 子→親（パッチ適用完了）

```json
{"task_id":"T001","event":"patch_applied","files":["src/auth.py","tests/test_auth.py"]}
```

* 親→子（承認結果）

```json
{"task_id":"T001","cmd":"proceed","approved":true}
```

* 子→親（完了）

```json
{"task_id":"T001","event":"done","pr_url":"https://.../pull/123"}
```

### 5.3 エラー/再試行

* 形式不正：親が`{"event":"error","reason":"bad_json"}`返信、子を再起動可
* 子プロセスクラッシュ：親が**再起動**（起動回数に上限）
* タイムアウト：親がSlackに「手動対応」を促す

---

## 6. Git/GitHub運用

### 6.1 命名規則

* ブランチ：`feature/<task_id>-<slug>` 例：`feature/T001-login`
* worktreeパス：`../worktrees/<task_id>`

### 6.2 典型コマンド

```
# 前提: origin/main が基準
git fetch origin
git worktree add -b feature/T001 ../worktrees/T001 origin/main
# 作業→コミット
cd ../worktrees/T001
git add -A && git commit -m "feat(T001): login MVP"
git push -u origin feature/T001
# PR作成（gh CLI）
gh pr create -B main -H feature/T001 -t "T001: Login MVP" -b "Implements ..."
```

### 6.3 CI/マージ（MVP）

* CIは**最低限のテスト**のみ
* 成功→自動マージ（もしくはSlackで最終Approve）

---

## 7. Slack連携（進捗のみ：MVP）

### 7.1 どう見えるか

* チャンネル例：`#ai-dev` に**タスク開始/PR作成/CI結果/完了/失敗**をポスト。
* 可能なら**スレッド**（`thread_ts`）でタスクごとに集約。

### 7.2 最小設定

* Bot token
* **chat.postMessage**（送信のみ）

### 7.3 投稿フォーマット例（任意）

* `T001 START: worktree=... branch=...`
* `T001 PR: https://.../pull/123`
* `T001 CI: passed` / `T001 CI: failed`
* `T001 DONE` / `T001 ERROR: <summary>`

## 8. tmuxの使い方（MVP） tmuxの使い方（MVP）

* セッション`ai-factory`、ウィンドウ`dashboard`
* 各paneに：`tail -f logs/agent-<task_id>.log`
* 1paneはOrchestratorのメインログ
* `libtmux`でpane自動生成（入力は**行わない**）

---

## 9. ディレクトリ/ファイル構成（例）

```
repo/
  requirements.yaml          # 入力（要件）
  orchestrator/
    orchestrator.py          # 親（制御）
    task_splitter.py         # 簡易タスク分解
    ipc.py                   # 標準入出力ラッパ
    vcs.py                   # git/gh 操作
    slack.py                 # Slack送受信
  agents/
    agent.py                 # 子（作業者の標準実装）
  state/
    tasks.yaml               # タスクリスト（生成物）
    runs.sqlite              # 実行状態（任意）
  logs/
    agent-T001.log           # tmuxでtailする
worktrees/
  T001/
  T002/
```

---

## 10. 導入手順（ハイレベル）

1. **前提**：Python 3.11+/Git/gh CLI/tmux/Slack App（Bot Token & Signing Secret）/GitHub PAT
2. `requirements.yaml` を作る（最小でもOK）
3. Orchestratorを起動 → タスク分解 → worktree生成 → Agent起動
4. Slackに進捗が流れる（開始/PR/CI/完了）
5. PRが作成されCIが通る→自動マージ

---

## 11. セキュリティ/権限（最小）

* GitHub PATは**対象Repoのみ**（Fine-grained）
* Slack Signing Secretの**署名検証は必須**
* エージェントの実行は**プロジェクトディレクトリ以下**にサンドボックス
* 環境変数や秘密は**dotenv/OS Secret**で管理

---

## 12. 運用・監視（MVP）

* ログ：`logs/`配下（ローテーションは日次）
* 失敗時：再起動回数の上限、タイムアウト通知（Slack）
* メトリクス（任意）：PR件数/CI成功率/平均承認時間

---

## 13. 制約/既知の課題

* 標準入出力IPCは単一ホスト前提。分散化は未対応
* エージェントの“設計理解”は限定的（要件はYAMLで明示する）
* 補佐AIが無いので、**仕様逸脱の自動検知は弱い**（人の承認でカバー）

---

## 14. 将来拡張

* 補佐AIの導入（Yes/Noゲート＋逸脱検知）
* Redis/NATS採用でプロセス/ホスト分散
* タスク計画のLangGraph化、RAG/社内ナレッジ統合
* ガードレール（コマンドホワイトリスト、権限境界）
* 自動リリース/環境分離（dev/stg/prod）

---

## 付録A：`requirements.yaml`の最小例

```yaml
product: "シンプルTodoアプリ"
constraints:
  - "機密情報を直書きしない"
  - "ユニットテストを1本以上追加"
tasks:
  - id: T001
    goal: "バックエンドAPIの雛形（/todos）"
  - id: T002
    goal: "フロントの一覧画面（読み取りのみ）"
```

## 付録B：`tasks.yaml`（自動生成イメージ）

```yaml
- id: T001
  branch: feature/T001-backend
  worktree: ../worktrees/T001
  tests: ["pytest -q"]
  thread_ts: null  # Slack投稿後に埋まる
- id: T002
  branch: feature/T002-frontend
  worktree: ../worktrees/T002
  tests: ["npm test --silent"]
  thread_ts: null
```

## 付録C：Agentが返すイベント一覧（例）

* `ack_start` / `log` / `patch_applied` / `tests_passed` / `tests_failed` / `await_approval` / `done` / `error`

---

以上。これで「何が起こるのか」をコード無しに把握できます。次のステップとして、この設計に沿った**最小スクリプト**を用意できます（Python想定）。変更したい点があれば、この文書上で赤入れしていきましょう。

---

## 15. 子＝Claude Code（ヘッドレス/stream-json）方式（MVP確定）

**方針**: 子プロセスは *Claude Code CLI そのもの* を起動し、ヘッドレスで **stream-json** を標準出力へ流します。親はその **NDJSON** を読み、\*\*最後の \*\***`type:"result"`** をもって完了/失敗を機械判定します。通常は親から子への追加入力は行いません（例外時のみ）。

### 15.1 立ち上げと入出力

* **起動**: タスクごとの \*\*worktree を \*\***`--cwd`** に指定し、**ヘッドレス**（例: `-p`）＋`--output-format stream-json` で子を起動。
* **初期メッセージ**: 親は起動直後に **1回だけ**、要約された要件/受入基準/禁止事項を投入（必要な場合のみ）。
* **出力**: 子は作業ログ/ツール実行/考察を **行単位のJSON** で逐次出力し、最後に **`{"type":"result", "is_error": false|true, ...}`** を出力。
* **完了検知**: 親は `type:"result"` を受けた時点でタスク状態を更新（`done/error`）。

### 15.2 権限と無人実行（MVP）

* **全自動**にするため、MVPでは **`--dangerously-skip-permissions`** を使用。
* これにより、Claude Codeの通常の Yes/No 許可プロンプトをスキップし、親が頻繁に応答する必要を排除。
* 将来は `--permission-prompt-tool`（MCP）で外部承認（Slack）へ拡張可能。

### 15.3 失敗ハンドリング（例外系のみ親が介入）

* 子が致命的に進めない場合、最終 `result` が `is_error:true` で終了。
* 親は `tasks.yaml` を `error` に更新し、Slackへエスカレーション（MVPでは人手対応）。

## 16. ヘッドレスを選ぶ理由と tmux の両立

* **機械可読性**: `stream-json` は DONE/ERROR を**確実**に判定でき、外部連携（Slack/PR/CI）トリガを安全に実装可能。TUIの画面文字は機械判定に不向き。
* **無人運転**: `--dangerously-skip-permissions` で親のボトルネックを回避（通常は親へ問い合わせなし）。
* **見た目の両立**: 出力は NDJSON なので、tmux 各 pane では `tail -f logs/T001.jsonl | jq -r '...表示...'` などで**人間向けに整形表示**できる。 「Claude Code UI」ではなくAPIを使う理由と選択肢
* **UI自動操作は脆い**（DOM変更/色コード/対話の同期問題）。MVPでは**API/SDK**で安定実装。
* **選択肢**

  1. 公式SDK/HTTP APIで**モデルを直に呼ぶ**（推奨）。JSONモード/関数呼び出し相当を自作（上記ツール群）。
  2. （代替）CLIがJSON I/Oを保証するなら子から呼ぶ。ただし**標準出力の解析と互換性維持が負担**。

---

## 17. 識別子/並列実行の整理

* **agent\_id**: 子プロセスに付与。親は`proc_handle↔agent_id`を保持。
* **task\_id**: 1タスク＝1ワークツリー＝原則1エージェント。
* **feature\_id**: 機能管理エージェント単位の識別子（将来導入）。
* **thread\_ts**: SlackスレッドID。`task_id`とひも付け、通知を集約。
* **corr\_id**: 親→子→親の往復に付ける相関ID（任意）。
* **並列**: 親は非同期I/Oで複数子のstdoutを同時監視。子は内部でLLM往復を複数回実施しても、親へは節目イベントのみ送る方針でスケール。

---

## 18. MVP運用の確定事項（合意）

* 親は **配車役**：タスク分解 → worktree/branch 作成 → 子(Claude Code)起動。
* 子は **自走**：基本は親へ連絡しない。節目のみ（`result`）親が受信。
* **権限**：MVPは `--dangerously-skip-permissions` で無人実行。
* **Slack**：MVPでは完了/失敗の通知のみ（将来、承認は補佐AI＋MCPに委譲）。
* **tmux**：JSONログの整形ビューを表示（入力は行わない）。

## 19. 子→親 イベント取り扱い（最小スキーマ）

* **ストリーム中の通常行**: 解析は任意（ログ保存）。
* **完了行**: `{"type":"result", "is_error": false, "summary": "...", "artifacts": {...}}`

  * `is_error:false` → 親は `tasks.yaml` を `done` に更新 → PR/CI/マージへ進む。
  * `is_error:true`  → 親は `tasks.yaml` を `error` に更新 → Slackへエスカレーション。
* 付加情報（任意）: `pr_url`, `commit_ref`, `test_report` などが含まれる場合は保存。

## 20. 将来拡張：承認フロー

* `--permission-prompt-tool`（MCP）で**承認プロンプトを外部化**し、補佐AIやSlackボタンで応答。
* 親は承認結果だけを受け取り、子へ再投入（継続実行）。

## 21. 起動コマンドの雛形（例）

```
claude \
  -p \
  --output-format stream-json \
  --dangerously-skip-permissions \
  --cwd ../worktrees/T001
```

> 省略しない場合：`--input-format stream-json` で追加メッセージ投入も可能（MVPでは通常不要）。

## 22. tmux 表示パイプライン（例）

```
# 親が保存する NDJSON を人間向けに整形
 tail -f logs/T001.jsonl \
   | jq -r 'select(.type=="tool" or .type=="message" or .type=="result")
             | "[\(.type)] \(.subtype // "-") => \(.text // .summary // "")"'
```

以上の更新により、MVPの「全自動（確認スキップ）」「親は配車のみ」「完了/失敗のみイベント処理」という方針が明文化されました。

## 2A. エージェント階層（3層・将来拡張/展示会仕様の想定）

* **最上位 親エージェント（PMAI）**：要件定義書に従い、**機能/画面/大きめのUIコンポーネント単位**で粗くタスク分解し、各機能に\*\*機能管理エージェント（FMA）\*\*を割り当てる。worktreeの親ディレクトリや命名規則、グローバル制約を配布。
* **中位 機能管理エージェント（FMA）**：担当機能の実装方針をまとめ、**細粒度の開発タスク**に再分解。各タスクは\*\*成果物ファイルが2つ以下（実装ファイル＋テストファイルの合計≦2）\*\*を原則とし、**1タスク=1ブランチ=1 worktree=1実装エージェント**で起動。
* **下位 実装エージェント**：タスクの受入基準を満たすまで自走（Claude Codeヘッドレス）。

> MVPでは“PMAI→実装エージェント”の**2層で運用**し、FMAは**将来追加**する。設計上は**再帰的**に適用できるため、FMA導入時もプロトコルは共通。

---

## 23. 同時起動数の上限制御（スケジューリング）

**上限例（展示会想定）**

* 機能管理エージェント（FMA）：同時最大 **3** 個
* 実装エージェント（子）：全体で同時最大 **10** 個

**割り当てと管理の方法（MVP→将来）**

* 親は `state/tasks.yaml`（またはSQLite）に **キュー** を持ち、`queued → starting → running → done|error` の**状態機械**で管理。
* **2段のセマフォ**で制御：`sem_fm=3`、`sem_child_total=10`。FMA（将来導入）が子を起動する前に **child 権限チケット**を取得し、終了時に返却。
* **公平性**：同一機能に子を集中させすぎないよう、**ラウンドロビン**または**per-feature 上限**（例：各FMAあたり同時子 4 まで）を設定。
* **バックプレッシャ**：子が`error`で終了した場合は**指数バックオフ**して再投入。`running`が閾値以上のFMAは一時的に**抑制**。
* **解放処理**：子が `result` を出した時点でスロットを即時解放し、次のタスクを起動。tmuxのビューはログファイル単位で自動追従。

> MVPでは FMA が未導入のため、`sem_child_total=10` の**単一セマフォ**で十分。FMA導入時に `sem_fm`を追加する。
