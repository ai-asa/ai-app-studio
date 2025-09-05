# 展示会向けシステム：tmux 可視化 + ファイルベース・メッセージバス設計（改訂版）

**版:** v0.9 (MVP-of-MVP)
**目的:** デモで「AIが並列に働く様子」を確実に“見せる”。同時に、将来の**双方向通信**を無理なく拡張できる**基盤**を残す。

---

## 0. まとめ（先に結論）

* **すべての Claude Code は tmux pane 上で起動**（可視化＆TTYを担保）。
* **通信は独立のメッセージバス（busd）**が仲介し、親子は**直接は話さない**。
* 親・子は **Bash ツールから `busctl`（薄いCLI）**を呼び、**NDJSON 封筒**を**mailbox**へ投函。
* **busd** は mailbox を監視し、

  * `spawn` → **git worktree/branch 作成**→ **tmux pane 起動**→ **pipe-pane でログ配線**
  * `send`（親→子）→ **tmux send-keys** で pane に注入（TTY経由）
  * `post`（子→親）→ **bus.jsonl に集約**し、`state/tasks.json` を更新
* 親 Claude は **最初にタスク分解と spawn 投函**のみ実施。**常時受信はしない**。全タスク完了後に**一度だけ**呼び出して総括レポートを生成（任意）。

> これにより、**可視化は tmux**、**信頼できる通信はファイル基盤**で分離。`send-keys` 直叩きに依存せず、将来の双方向（レビュー指示、再実行、broadcast）へ素直に拡張できる。

---

## 1. スコープ

### 1.1 MVP-of-MVP（今回）

* 親：要件定義書（`requirements.yml`）を読み、**タスク分解 → spawn** を `busctl` で投函。
* busd：spawn を処理し、**子 pane 起動**・**ログ配線**。
* 子：作業し、**進捗/完了は `busctl post`** を通じて報告。
* ダッシュボード：`tail -F logs/bus.jsonl | jq -r .` を tmux pane に配置。
* **親から子への追加指示は最小限**（初期インストラクションのみ）。

### 1.2 非目標（後回し）

* 公平キュー（fair queue）/ 受信遅延制御（必要になったら追加）
* 子↔子の直接通信、外部SaaS連携、CI/PR 自動化
* 恒久DB（今回はファイルで十分）

---

## 2. コンポーネント

### 2.1 busd（tmux オーケストレータ兼メッセージバスデーモン）

* **役割**

  * mailbox（`mbox/<agent>/in/`）の**投函ファイル**を監視（ポーリングで可）。
  * `spawn` を検出：

    1. **git branch/worktree** 準備
    2. `tmux new-window` で **子 Claude Code** 起動
    3. `tmux pipe-pane` で `logs/raw/<task>.raw` にミラー
    4. `task_id → pane_id` を内部マップに登録
  * `send` を検出：宛先 pane へ **`tmux send-keys` 注入**
  * `post` を検出：**`logs/bus.jsonl` へ追記**、**`state/tasks.json` 更新**
* **備考**：同期は**宛先別 mailbox** と **ファイル名の単調増加**で担保。atomic write（tmp → rename）を徹底。

### 2.2 busctl（投稿CLI：親/子が使う）

* **役割**：封筒（JSON）を**適切な mailbox へ原子的に書き込む**小さなCLI。
* **サブコマンド例**

  * `spawn --task T001 --cwd work/T001 --frame frames/impl/CLAUDE.md --goal '...' [--branch feat/T001]`
  * `send  --to impl:T001 --type instruct --data '{...}'`
  * `post  --from impl:T001 --type log|result --task T001 --data '{...}'`
* **実装**：bash でも python でも良い。`mktemp` → `mv` で原子的に投函。

### 2.3 親/子 Claude Code（frames）

* **親（PMAI）**

  * `requirements.yml` を読解→**`Bash(busctl spawn ...)` を列挙**
  * （必要なら）初期インストラクションを **`Bash(busctl send ...)`** で注入
  * 最後に `busctl post --type result --task ALL ...`（任意）
* **子（Impl）**

  * 進捗：`Bash(busctl post --type log ...)` で報告
  * 完了：`Bash(busctl post --type result ...)`（`is_error` 必須）
  * pane 上の自然な発話は**可視化用**。通信は**busctl 経由**のみとする

---

## 3. メッセージ封筒（スキーマ）

```json
{
  "id": "ulid",
  "ts": 1730550000000,
  "from": "pmai" | "impl:T001",
  "to":   "impl:T001" | "pmai" | "bus",
  "type": "spawn" | "send" | "log" | "result" | "error",
  "task_id": "T001",
  "data": {"cwd":"work/T001","frame":"frames/impl/CLAUDE.md","goal":"..."}
}
```

* **必須**：`type` / `task_id`（`spawn` の親 → 子起動時のみ必須）/ `data`
* **`result`**：`data.is_error: true|false` を必須とする。

---

## 4. ディレクトリ構成（MVP）

> **物理配置の前提**
> この章のパスは“論理構成”です。実運用では、本体コード（オーケストレーター）・対象リポジトリ・作業用サイドカーの**3つのルート**を分離します（次節 4.1 参照）。

```
target-repo/                  # TARGET_REPO（作業対象リポジトリ）
  README.md                   # 既存のプロジェクトファイル
  requirements.yml            # AIタスクの要件定義
  T001/                       # worktree（feat/T001ブランチ）
  T002/                       # worktree（feat/T002ブランチ）
  .ai-app-studio/            # AI App Studio管理ディレクトリ
    mbox/
      bus/in/                # 親→bus への spawn 等
      pmai/in/               # 子→親（post）受け口
      impl-T001/in/          # 親→子（send）受け口（動的に増える）
    logs/
      raw/T001.raw           # 子 pane の生ログ（pipe-pane ミラー）
      bus.jsonl              # 集約イベント
    state/
      tasks.json             # [{id, status}]
      panes.json             # pane管理情報

ai-app-studio/               # オーケストレーター本体（別の場所）
  bin/
    busd.py                  # デーモン
    busctl.py                # 投稿CLI
  frames/
    pmai/CLAUDE.md           # 親エージェント用フレーム
    impl/CLAUDE.md           # 子エージェント用フレーム
```

### 4.1 物理配置（シンプルな2層構造）

**結論:** *worktree は「対象リポジトリ」内にサブディレクトリとして作成し、管理ファイルは `.ai-app-studio` 配下に集約*します。

* **AI_APP_STUDIO_HOME**: オーケストレーターのコード配置（例: `~/tools/ai-app-studio`）
* **TARGET_REPO**: 作業対象リポジトリ（例: `/path/to/my-project`）

  * `T001/`, `T002/` などの worktree は **TARGET_REPO** の直下に作成
  * `logs/`, `state/`, `mbox/` は **TARGET_REPO/.ai-app-studio** の下に配置

**spawn 時の作成例（実コマンド）**

```bash
cd /path/to/target-repo
TASK=T001

# ブランチ作成（なければ）
git show-ref --verify --quiet refs/heads/feat/$TASK || \
  git branch feat/$TASK main

# worktree を TARGET_REPO 内のサブディレクトリとして作成
git worktree add "$TASK" "feat/$TASK"

# 確認
git worktree list
```

> `worktree list` に **TARGET\_REPO の本体パス**と**TARGET\_REPO/T001** が表示されます。**編集の実体は TARGET\_REPO 内のサブディレクトリ**で、**Git 的には feat/T001 ブランチ**です。

**起動方法**

```bash
# 1. 作業対象リポジトリに移動
cd /path/to/target-repo

# 2. busd を起動（バックグラウンドで実行）
python3 ~/tools/ai-app-studio/bin/busd.py

# 3. PMAI をスポーン
~/tools/ai-app-studio/bin/busctl spawn --task PMAI \
  --frame ~/tools/ai-app-studio/frames/pmai/CLAUDE.md \
  --goal "Process requirements.yml"
```

> これにより、\*\*本体コード（ORCH\_HOME）\*\*の場所に関係なく、**BUS\_HOME** にログ/状態/キューが集約され、**TARGET\_REPO** は worktree で“横から”編集されます。

---

## 5. フロー（シーケンス）

### 5.1 親のタスク分解 → spawn 投函

1. 親 Claude（tmux pane）で `Bash(busctl spawn ...)` をタスク数分実行。
2. busd が `mbox/bus/in/*.json` を検出→**子を起動**。

### 5.2 子起動時の処理（busd）

* `git branch feat/T001 main`（無ければ）
* `git worktree add T001 feat/T001`（TARGET_REPO内のサブディレクトリとして）
* `tmux new-window -n T001 -c T001 -- 'claude --dangerously-skip-permissions --allowedTools "Bash Edit" --add-dir .'`
* `tmux pipe-pane -o -t :T001.0 'stdbuf -oL -eL tee -a .ai-app-studio/logs/raw/T001.raw'`
* `task_id → pane_id` を保存（メモリ＆`.ai-app-studio/state/panes.json`）。

### 5.3 親→子の指示（任意・初期のみ）

* 親が `busctl send --to impl:T001 --type instruct --data '{"read":"./task.json","contract":"busctl post で報告"}'` を投函
* busd が受信→ `tmux send-keys -t :T001.0 "Read ./task.json ..." C-m`

### 5.4 子→親の報告

* 子は **Bash ツール**で：

  * `busctl post --from impl:T001 --type log --task T001 --data '{"msg":"start"}'`
  * `busctl post --from impl:T001 --type result --task T001 --data '{"is_error":false,"summary":"done"}'`
* busd が `mbox/pmai/in` を監視して集約：`logs/bus.jsonl` 追記、`state/tasks.json` 更新。

> 進捗/完了は **親のTTYに送らない**。**busdが受ける**ため、親が“受け付けられないタイミング問題”を根絶。

---

## 6. 仕様（CLI & ファイル）

### 6.1 busctl（bash 参考実装）

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT=${ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}
MBOX="$ROOT/mbox"
mkdir -p "$MBOX"

ts() { date -u +%Y%m%dT%H%M%S.%3NZ; }
rand() { hexdump -n 6 -v -e '/1 "%02x"' /dev/urandom; }
write_json() {
  local dest="$1"; shift
  local tmp="$dest/.tmp-$(ts)-$(rand).json"
  mkdir -p "$dest"
  printf '%s\n' "$*" > "$tmp"
  mv "$tmp" "$dest/$(ts)-$(rand).json"
}

case "${1:-}" in
  spawn)
    shift; # --task T001 --frame ... --goal ... --branch ...
    while [[ $# -gt 0 ]]; do case $1 in
      --task) TASK=$2; shift 2;; --frame) FRAME=$2; shift 2;;
      --goal) GOAL=$2; shift 2;; --branch) BR=$2; shift 2;; *) echo "unknown $1"; exit 1;; esac; done
    [[ -n "${TASK:-}" ]] || { echo "--task required"; exit 1; }
    write_json "$MBOX/bus/in" "{\"id\":\"$(ts)-$(rand)\",\"ts\":$(date +%s%3N),\"from\":\"pmai\",\"to\":\"bus\",\"type\":\"spawn\",\"task_id\":\"$TASK\",\"data\":{\"frame\":\"$FRAME\",\"goal\":\"${GOAL:-}\",\"branch\":\"${BR:-feat/$TASK}\"}}"
    ;;
  send)
    shift; while [[ $# -gt 0 ]]; do case $1 in
      --to) TO=$2; shift 2;; --type) T=$2; shift 2;; --data) D=$2; shift 2;; *) echo "unknown $1"; exit 1;; esac; done
    AG=$(echo "$TO" | tr ':' '-')
    write_json "$MBOX/$AG/in" "{\"id\":\"$(ts)-$(rand)\",\"ts\":$(date +%s%3N),\"from\":\"pmai\",\"to\":\"$TO\",\"type\":\"$T\",\"task_id\":\"${TO#impl:}\",\"data\":$D}"
    ;;
  post)
    shift; while [[ $# -gt 0 ]]; do case $1 in
      --from) FROM=$2; shift 2;; --type) T=$2; shift 2;; --task) TASK=$2; shift 2;; --data) D=$2; shift 2;; *) echo "unknown $1"; exit 1;; esac; done
    write_json "$MBOX/pmai/in" "{\"id\":\"$(ts)-$(rand)\",\"ts\":$(date +%s%3N),\"from\":\"$FROM\",\"to\":\"pmai\",\"type\":\"$T\",\"task_id\":\"$TASK\",\"data\":$D}"
    ;;
  *) echo "usage: busctl spawn|send|post ..."; exit 1;;
esac
```

### 6.2 busd（python 骨組み）

```python
#!/usr/bin/env python3
import json, os, time, glob, subprocess, shlex, pathlib
from datetime import datetime

ROOT = pathlib.Path.cwd() / ".ai-app-studio"
MBOX = ROOT / "mbox"
LOGS = ROOT / "logs"; (LOGS/"raw").mkdir(parents=True, exist_ok=True)
STATE = ROOT / "state"; STATE.mkdir(exist_ok=True)
BUS = LOGS / "bus.jsonl"; BUS.touch(exist_ok=True)
PANES = STATE / "panes.json"

TMUX_SESSION = os.environ.get("TMUX_SESSION","cc")
CLAUDE_CMD = os.environ.get("CLAUDE_CMD","claude code --dangerously-skip-permissions --allowedTools 'Bash Edit' --add-dir .")

pane_map = {}  # task_id -> tmux pane id (e.g. 'cc:T001.0')

def sh(cmd):
    return subprocess.check_output(cmd, shell=True, text=True).strip()

def ensure_session():
    try:
        sh(f"tmux has-session -t {TMUX_SESSION}")
    except subprocess.CalledProcessError:
        sh(f"tmux new-session -d -s {TMUX_SESSION} -n DASH 'bash -lc " +
           shlex.quote("tail -F logs/bus.jsonl | jq -r . 2>/dev/null") + "'")

def ensure_worktree(task_id, branch):
    # PMAIはTARGET_REPOで動作、他はサブディレクトリ
    if task_id == "PMAI":
        return pathlib.Path.cwd()
    
    worktree_path = pathlib.Path.cwd() / task_id
    if not worktree_path.exists():
        # 簡易: ブランチ・ワークツリー作成（存在時はノーオペ）
        try: sh(f"git show-ref --verify --quiet refs/heads/{branch}")
        except subprocess.CalledProcessError:
            sh(f"git branch {branch} main")
        sh(f"git worktree add {shlex.quote(str(worktree_path))} {branch}")
    return worktree_path


def spawn_child(task_id, worktree_path):
    # pane を作成
    sh(f"tmux new-window -t {TMUX_SESSION} -n {task_id} 'bash -lc " +
       shlex.quote(f"cd {worktree_path} && {CLAUDE_CMD}") + "'")
    # pane id 取得
    pane = sh(f"tmux list-panes -t {TMUX_SESSION}:{task_id} -F '#{{session_name}}:#{{window_name}}.#{{pane_index}}' | head -n1")
    # 出力ミラー
    (LOGS/"raw").mkdir(exist_ok=True)
    sh(f"tmux pipe-pane -o -t {pane} 'stdbuf -oL -eL tee -a .ai-app-studio/logs/raw/{task_id}.raw'")
    pane_map[task_id] = pane
    PANES.write_text(json.dumps(pane_map, ensure_ascii=False, indent=2))


def handle_spawn(msg):
    d = msg["data"]; task = msg["task_id"]
    branch = d.get("branch", f"feat/{task}")
    worktree_path = ensure_worktree(task, branch)
    spawn_child(task, worktree_path)


def handle_send(msg):
    to = msg["to"]  # impl:T001
    task = to.split(":",1)[1]
    pane = pane_map.get(task)
    if not pane:
        return
    data = msg.get("data", {})
    text = data.get("text") or json.dumps(data, ensure_ascii=False)
    sh(f"tmux send-keys -t {pane} {shlex.quote(text)} C-m")


def handle_post(msg):
    with BUS.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(msg, ensure_ascii=False) + "\n")
    # state 更新（簡易）
    t = msg.get("task_id"); typ = msg.get("type")
    stp = STATE/"tasks.json"
    try:
        tasks = {x["id"]: x for x in json.loads(stp.read_text())}
    except Exception:
        tasks = {}
    rec = tasks.setdefault(t, {"id": t, "status": "running"})
    if typ == "result":
        rec["status"] = "done" if not msg.get("data",{}).get("is_error") else "error"
    stp.write_text(json.dumps(list(tasks.values()), ensure_ascii=False, indent=2))


def process_mbox_once():
    # 宛先順に処理
    for dest in ["bus", "pmai"] + [p.name for p in (MBOX).glob("impl-*/in")]:
        pass
    # 簡易：すべての in/ を走査
    for ind in glob.glob(str(MBOX/"*"/"in")):
        for f in sorted(glob.glob(ind+"/*.json")):
            try:
                msg = json.loads(pathlib.Path(f).read_text())
            except Exception:
                continue
            t = msg.get("type")
            if t == "spawn":
                handle_spawn(msg)
            elif t == "send":
                handle_send(msg)
            else:
                handle_post(msg)  # log/result/error → post扱い
            pathlib.Path(f).unlink(missing_ok=True)


def main():
    ensure_session()
    while True:
        process_mbox_once()
        time.sleep(0.5)

if __name__ == "__main__":
    main()
```

---

## 7. フレーム（CLAUDE.md の最小原則）

### 7.1 親 `frames/pmai/CLAUDE.md`

* **やること**：

  1. `requirements.yml` を読み `tasks: [{id,cwd,goal}]` を取得
  2. 各タスクについて **Bash ツールで** `busctl spawn --task ...` を実行
  3. （任意）初期 `send` を 1 回だけ投函
  4. 最後に `busctl post --type result --task ALL ...` を 1 回
* **注意**：標準出力は自由でOK（可視化用）。通信は**必ず busctl** に限定。

### 7.2 子 `frames/impl/CLAUDE.md`

* **やること**：

  * 最初に `Bash(busctl post --type log ...)` で start ログ
  * `TASK_GOAL`/`./task.json` に従い作業（**cwd 配下のみ**）
  * 完了時に `Bash(busctl post --type result --data '{"is_error":false,...}' )`
  * 失敗時は `is_error:true` とエラー要約を含める

---

## 8. tmux レイアウト（例）

```
[0] DASH : tail -F logs/bus.jsonl | jq -r .
[1] PMAI : 親 Claude Code（任意）
[2] T001 : 子1 pane（work/T001）
[3] T002 : 子2 pane（work/T002）
...
```

---

## 9. 受け入れ基準（DoD）

* `busctl spawn` により：

  * `work/<task>` が作成され、対応ブランチ/ワークツリーが張られる
  * 新規 tmux 窓が立ち、`logs/raw/<task>.raw` に出力が流れる
* 子が `busctl post --type result` を投函し、`logs/bus.jsonl` と `state/tasks.json` が更新される
* `tail -F logs/bus.jsonl | jq` ダッシュボードで結果が見える

---

## 10. セキュリティ & フェイルセーフ

* **権限**：`--dangerously-skip-permissions` はデモ環境限定。`--add-dir` を `work/` のみに制限。
* **原子性**：busctl は tmp→rename、busd は処理後に削除（少なくとも一回配送）。
* **復旧**：busd 再起動時は未処理ファイルを再走査。pane マップは `state/panes.json` から復元。
* **バックプレッシャ**：宛先別 mailbox。必要時はディレクトリ監視→キュー長で制御。

---

## 11. ビルド順（最短）

1. `busctl`（投函CLI）
2. `busd`（spawn→tmux起動→pipe / send / post 集約）
3. `frames` 最小版（親=spawn列挙、子=post報告）
4. `requirements.yml` サンプル → E2E 通電
5. worktree 自動化（既存時のスキップ含む）

---

## 11.1 期待と現状のギャップ（2025年9月5日追記）

### ユーザーの期待
- **親と子の相互連動**: 子エージェントが完了報告を送ると、親エージェントがそれを受け取って次の処理を行う
- **リアルタイムな結果通知**: 子の作業結果が親に即座に伝わり、親が適切に反応する
- **動的な調整**: 親が子の結果を見て、追加の指示や新しいタスクの生成を行える

### 現在の設計（MVP-of-MVP）
- **プル型アーキテクチャ**: 親は能動的にファイル（bus.jsonl、tasks.json）を読みに行く必要がある
- **常時受信なし**: 親のTTYには結果を送らない設計で、「受け付けられないタイミング問題」を回避
- **非同期・疎結合**: メッセージバス経由で通信し、親子は直接対話しない

### 改善の方向性
将来の拡張として、以下のような実装を検討：
1. **親への通知機能**: resultメッセージ受信時に、親エージェントのpaneに通知を送る
2. **イベントドリブン**: 親がファイル監視により、新しい結果を検知して自動処理
3. **インタラクティブモード**: 親子間の多ターン対話を可能にする

## 11.2 ユーザー要望と実装状況（2025年9月5日追記）

### ユーザーの具体的な要望
1. **タスクごとにブランチを切って、そのブランチのworktreeで各子claude codeが作業する**
2. **各子が完了した段階でPRを作成してマージまで行う**
3. **コンフリクトが発生した場合に対処する**
4. **最終的にすべてのコンフリクトを解消し、すべての開発が完了した状態になる**

### 現在の実装状況
1. ✅ **ブランチ・worktree機能** - 実装済み（MVP-of-MVPに含まれる）
   - `ensure_worktree`関数でTARGET_REPOにブランチ作成
   - `.ai-app-studio/work/<TASK_ID>`にworktreeを作成
   - 各子エージェントが独立した環境で作業可能

2. ❌ **PR作成・マージ機能** - 未実装（非目標として設計）
   - 現在のMVP-of-MVPでは「CI/PR 自動化」は明確に非目標
   - ghコマンドによるPR操作の仕様はCLAUDE.mdに記載あり

3. ❌ **コンフリクト対処** - 未実装（設計外）
   - 現在の設計では各タスクが独立worktreeで作業
   - マージ時のコンフリクト解決機能なし

4. ❌ **統合完了機能** - 未実装（設計外）
   - 全タスクの統合とコンフリクト解消のフローなし
   - 最終的な品質保証プロセスなし

### 実装に必要な拡張
これらの要望を実現するには、以下の拡張が必要：
- **メッセージタイプの追加**: `pr_create`, `pr_merge`, `conflict_resolve`など
- **busdの機能拡張**: PR管理、マージ処理、コンフリクト検出
- **子エージェントフレームの拡張**: PR作成処理の追加
- **親エージェントの役割拡張**: マージ戦略の決定、コンフリクト解決の指示

## 11.3 worktree配置の設計問題（2025年9月5日追記）

### 発見された問題
- **現在の実装**: worktreeが`.ai-app-studio/work/`内に作成される
- **問題点**: `.gitignore`に`.ai-app-studio/`が含まれるため、開発成果もgitignoreされてしまう
- **結果**: 開発したコードがコミット・プッシュできない

### 一般的なworktreeの使い方
1. **並列ディレクトリ方式**（最も一般的）
   ```
   parent-directory/
   ├── my-project/          # メインリポジトリ（main）
   ├── my-project-feat-A/   # worktree（feat/A）
   ├── my-project-feat-B/   # worktree（feat/B）
   ```

2. **worktreesサブディレクトリ方式**
   ```
   my-project/
   └── worktrees/
       ├── feat-A/
       └── feat-B/
   ```

### 採用する解決策：並列ディレクトリ方式

#### 新しいディレクトリ構造
```
workspace/                    # 作業ディレクトリ
├── my-project/              # TARGET_REPO（main）
├── my-project-T001/         # worktree（feat/T001）
├── my-project-T002/         # worktree（feat/T002）
└── my-project/.ai-app-studio/  # 管理ファイルのみ
    ├── mbox/
    ├── logs/
    └── state/
```

#### 実装変更が必要な箇所
1. **ensure_worktree関数**
   - worktreeをTARGET_REPOの親ディレクトリに作成
   - 命名規則: `{repo-name}-{task-id}`
   - 例: `/home/user/projects/my-app` → `/home/user/projects/my-app-T001`

2. **spawn処理**
   - cwdパラメータを新しいworktree位置に変更
   - 例: `--cwd work/T001` → `--cwd ../my-app-T001`（相対）または絶対パス
   - 子エージェントの作業ディレクトリを適切に設定

3. **フレーム更新**
   - PMAIフレーム: spawn時のcwdを適切に計算
   - 子フレーム: 作業ディレクトリの認識

4. **環境変数の見直し**
   - WORKTREE_BASE: worktreeを作成する親ディレクトリ
   - 各子エージェントへの環境変数引き継ぎ

---

## 12. 将来拡張（残せる余白）

* **公平キュー**：busd で宛先ごとに RR スケジューラ
* **broadcast**：`to:"broadcast"` を `impl-*` 全宛先へ複製
* **再試行/死亡検知**：pane 心拍（`tmux display -p '#{pane_dead}'`）/ 再起動カウント
* **親←→子の多ターン**：`send`（親→子）と `post`（子→親）を任意回数に拡張
* **永続DB**：bus.jsonl を後段でSQLite/ClickHouseへ
* **外部連携**：MCP/CI、PR 自動化… busd のハンドラ追加で非侵襲に実現
* **親子相互連動**：子の完了通知を親のTTYに送信し、リアルタイムな反応を実現

---

## 付録A：起動コマンド例（手動）

```bash
# 1) デーモン起動
python3 bin/busd.py &

# 2) サンプルタスク 2 件
./bin/busctl spawn --task T001 --cwd work/T001 --frame frames/impl/CLAUDE.md --goal 'hello.txt を作る'
./bin/busctl spawn --task T002 --cwd work/T002 --frame frames/impl/CLAUDE.md --goal 'README.md を作る'

# 3) 初期インストラクション（任意）
./bin/busctl send --to impl:T001 --type instruct --data '{"text":"Read ./task.json and report via busctl post."}'

# 4) ダッシュボード
tmux attach -t cc  # 画面でログ流れを確認
```

---

## 付録B：メッセージ例

```json
{"type":"spawn","from":"pmai","to":"bus","task_id":"T001","data":{"cwd":"work/T001","frame":"frames/impl/CLAUDE.md","goal":"hello.txt を作る","branch":"feat/T001"}}
{"type":"send","from":"pmai","to":"impl:T001","task_id":"T001","data":{"text":"Read ./task.json; report via busctl post."}}
{"type":"log","from":"impl:T001","to":"pmai","task_id":"T001","data":{"msg":"start"}}
{"type":"result","from":"impl:T001","to":"pmai","task_id":"T001","data":{"is_error":false,"summary":"done"}}
```

---

## 付録C：環境要件

* Linux（Ubuntu系推奨）、tmux ≥ 3.2、git ≥ 2.35、Python ≥ 3.10
* Claude Code が CLI で起動可能であること
* `jq` / `sed` / `stdbuf`（GNU coreutils/Moreutils）

---

## 付録D：既知のリスクと緩和

* **モデルが指示に従わず余計な発話**：通信は busctl 経由に限定（発話は可視化のみ）
* **tmux pane 名の衝突**：task\_id ベースで一意化。存在時は再利用 or suffix
* **ファイル監視の遅延**：MVP はポーリング 500ms。必要時 inotify へ
* **ワークツリーの肥大**：リテンション設定（完了後に archive/）

---

以上。これで **可視化（tmux）× 信頼できる通信（mailbox バス）** が最小実装で成立し、双方向の将来拡張をそのまま受け止める“芯”が出来ます。
