#!/usr/bin/env python3
"""
busd - tmuxオーケストレータ兼メッセージバスデーモン

役割:
- mailboxの投函ファイルを監視（ポーリング）
- spawnメッセージ: git branch/worktree作成、tmux pane起動、pipe-pane設定
- sendメッセージ: tmux send-keys実行
- postメッセージ: logs/bus.jsonl追記、state/tasks.json更新
"""

import json
import os
import sys
import time
import glob
import subprocess
import shlex
from pathlib import Path
from datetime import datetime

# ターゲットリポジトリの決定
# 優先順位: 1) コマンドライン引数 2) カレントディレクトリ
# 注: 環境変数は使わない（汎用性のため）
if len(sys.argv) > 1:
    TARGET_REPO = Path(sys.argv[1]).resolve()
else:
    TARGET_REPO = Path.cwd()

print(f"busd starting with TARGET_REPO: {TARGET_REPO}")

# AI App Studioのルートディレクトリ
AI_APP_STUDIO_ROOT = Path(__file__).parent.parent

# タイミング関連の定数
POLLING_INTERVAL = 0.5  # メールボックスのポーリング間隔（秒）
TMUX_OPERATION_DELAY = 0.1  # tmux操作後の待機時間（秒）
CLAUDE_STARTUP_DELAY = 5  # Claude Code起動待機時間（秒）
TEXT_PREVIEW_LENGTH = 50  # テキストプレビューの最大文字数
MS_PER_SECOND = 1000  # ミリ秒変換係数

# 作業ディレクトリは TARGET_REPO/.ai-app-studio に設定
if os.environ.get("ROOT"):
    # テスト環境などでROOTが明示的に設定されている場合はそれを使用
    ROOT = Path(os.environ.get("ROOT"))
else:
    # 本番環境では .ai-app-studio サブディレクトリを使用
    ROOT = TARGET_REPO / ".ai-app-studio"

MBOX = ROOT / "mbox"
LOGS = ROOT / "logs"
STATE = ROOT / "state"
WORK = ROOT / "work"

# TARGET_REPOは環境変数として設定しない（汎用性のため）
# 各子プロセスが必要に応じて独自に設定する

# 必要なディレクトリの作成
MBOX.mkdir(parents=True, exist_ok=True)
(LOGS / "raw").mkdir(parents=True, exist_ok=True)
STATE.mkdir(exist_ok=True)
WORK.mkdir(exist_ok=True)

# ファイルパス
BUS_LOG = LOGS / "bus.jsonl"
PANES_FILE = STATE / "panes.json"
TASKS_FILE = STATE / "tasks.json"

# ログファイルの初期化
BUS_LOG.touch(exist_ok=True)

# tmux設定
TMUX_SESSION = os.environ.get("TMUX_SESSION", "cc")
CLAUDE_CMD = os.environ.get("CLAUDE_CMD", 
    "claude --dangerously-skip-permissions --allowedTools Bash,Edit --add-dir .")

# レイアウト設定
LAYOUT_RIGHT_BASE_PANE = 2  # 右側ペインのベースインデックス
PANE_PMAI = 0  # 左上：PMAIエージェント用
PANE_DASHBOARD = 1  # 左下：ダッシュボード用

# グローバル状態
pane_map = {}  # task_id -> tmux pane id (e.g. 'cc:T001.0')
tasks = {}     # task_id -> task info


def sh(cmd, check=True):
    """シェルコマンドを実行"""
    try:
        result = subprocess.run(cmd, shell=True, text=True, 
                              capture_output=True, check=check)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        if check:
            print(f"Command failed: {cmd}")
            print(f"stderr: {e.stderr}")
            raise
        return None


def load_state():
    """永続化された状態を読み込み"""
    global pane_map, tasks
    
    # pane_map
    if PANES_FILE.exists():
        try:
            pane_map = json.loads(PANES_FILE.read_text())
        except Exception as e:
            print(f"Failed to load panes.json: {e}")
            pane_map = {}
    
    # tasks
    if TASKS_FILE.exists():
        try:
            task_list = json.loads(TASKS_FILE.read_text())
            tasks = {t["id"]: t for t in task_list}
        except Exception as e:
            print(f"Failed to load tasks.json: {e}")
            tasks = {}


def save_pane_map():
    """pane_mapを永続化"""
    PANES_FILE.write_text(json.dumps(pane_map, ensure_ascii=False, indent=2))


def save_tasks():
    """tasksを永続化"""
    task_list = list(tasks.values())
    TASKS_FILE.write_text(json.dumps(task_list, ensure_ascii=False, indent=2))


def ensure_session():
    """tmuxセッションが存在することを確認"""
    result = sh(f"tmux has-session -t {TMUX_SESSION} 2>&1", check=False)
    if result is None or "can't find session" in str(result):
        # セッションを作成（TEMPウィンドウで開始）
        cmd = f"tmux new-session -d -s {TMUX_SESSION} -n TEMP 'bash'"
        if sh(cmd, check=False) is not None:
            print(f"Created tmux session: {TMUX_SESSION}")
            time.sleep(TMUX_OPERATION_DELAY)  # セッション作成を待つ
    
    # MAINウィンドウのレイアウトを確保
    ensure_main_window_layout()
    
    # MAINウィンドウをアクティブにする
    sh(f"tmux select-window -t {TMUX_SESSION}:MAIN", check=False)


def get_worktree_path(task_id):
    """並列ディレクトリ方式のworktreeパスを返す"""
    # TARGET_REPOの親ディレクトリに、リポジトリ名-タスクIDの形式でworktreeを作成
    # 例: /workspace/my-project → /workspace/my-project-T001
    parent_dir = TARGET_REPO.parent
    repo_name = TARGET_REPO.name
    worktree_path = parent_dir / f"{repo_name}-{task_id}"
    return worktree_path


def is_git_repository(repo_path):
    """指定されたパスがGitリポジトリかどうかをチェック"""
    try:
        sh(f"git -C {shlex.quote(str(repo_path))} rev-parse --git-dir")
        return True
    except subprocess.CalledProcessError:
        return False


def get_current_branch(repo_path):
    """現在のブランチを取得"""
    current_branch = sh(f"git -C {shlex.quote(str(repo_path))} branch --show-current", check=False)
    
    if not current_branch:
        # デフォルトブランチを取得（HEADが指すブランチ）
        try:
            current_branch = sh(f"git -C {shlex.quote(str(repo_path))} symbolic-ref --short HEAD")
        except subprocess.CalledProcessError:
            # HEADがデタッチド状態の場合、最初のブランチを使用
            branches = sh(f"git -C {shlex.quote(str(repo_path))} branch --format='%(refname:short)'", check=False)
            if branches:
                current_branch = branches.split('\n')[0].strip()
            else:
                return None
    
    return current_branch


def create_initial_commit(repo_path):
    """リポジトリに初期コミットを作成"""
    # git設定の確認（コミットに必要）
    try:
        sh(f"git -C {shlex.quote(str(repo_path))} config user.name", check=True)
    except subprocess.CalledProcessError:
        # git設定がない場合はデフォルト値を設定
        sh(f"git -C {shlex.quote(str(repo_path))} config user.name 'AI App Studio'")
        sh(f"git -C {shlex.quote(str(repo_path))} config user.email 'ai-app-studio@localhost'")
        print("Set default git config for initial commit")
    
    # .gitignoreファイルを作成
    gitignore_path = Path(repo_path) / ".gitignore"
    if not gitignore_path.exists():
        gitignore_content = "# AI App Studio\n.ai-app-studio/\n*.pyc\n__pycache__/\n.DS_Store\n"
        gitignore_path.write_text(gitignore_content)
        sh(f"git -C {shlex.quote(str(repo_path))} add .gitignore")
    
    # 初期コミット
    sh(f"git -C {shlex.quote(str(repo_path))} commit -m 'Initial commit' --allow-empty")
    print("Created initial commit")


def branch_exists(repo_path, branch):
    """指定されたブランチが存在するかチェック"""
    try:
        sh(f"git -C {shlex.quote(str(repo_path))} show-ref --verify --quiet refs/heads/{branch}")
        return True
    except subprocess.CalledProcessError:
        return False


def create_branch_if_needed(repo_path, branch, base_branch):
    """必要に応じてブランチを作成"""
    if not branch_exists(repo_path, branch):
        # ベースブランチがコミットを持っているか確認
        try:
            sh(f"git -C {shlex.quote(str(repo_path))} rev-parse {base_branch}")
            # ブランチ作成
            sh(f"git -C {shlex.quote(str(repo_path))} branch {branch} {base_branch}")
            print(f"Created git branch: {branch} (from {base_branch})")
        except subprocess.CalledProcessError:
            # リポジトリが空の場合、初期コミットを作成
            print(f"Repository has no commits yet. Creating initial commit...")
            create_initial_commit(repo_path)
            # ブランチ作成を再試行
            sh(f"git -C {shlex.quote(str(repo_path))} branch {branch} {base_branch}")
            print(f"Created git branch: {branch} (from {base_branch})")


def setup_worktree(repo_path, worktree_path, branch):
    """Worktreeをセットアップ"""
    try:
        sh(f"git -C {shlex.quote(str(repo_path))} worktree add {shlex.quote(str(worktree_path))} {branch}")
        print(f"Created worktree: {worktree_path}")
    except subprocess.CalledProcessError as e:
        # worktreeが作成できない場合は通常のディレクトリを作成
        print(f"Failed to create worktree: {e.stderr}")
        worktree_path.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {worktree_path}")


def ensure_worktree(task_id, branch):
    """git worktreeが存在することを確認（並列ディレクトリ方式）"""
    worktree_path = get_worktree_path(task_id)
    
    print(f"DEBUG: ensure_worktree called for task_id={task_id}, branch={branch}")
    print(f"  worktree_path: {worktree_path}")
    
    if worktree_path.exists():
        return worktree_path  # すでに存在
    
    # TARGET_REPOがgitリポジトリかチェック
    if is_git_repository(TARGET_REPO):
        # 現在のブランチを取得
        current_branch = get_current_branch(TARGET_REPO)
        
        if not current_branch:
            # ブランチが全く存在しない場合はエラー
            print(f"Error: No branches found in {TARGET_REPO}")
            print("Please make at least one commit in the repository first.")
            worktree_path.mkdir(parents=True, exist_ok=True)
            print(f"Created directory instead: {worktree_path}")
            return worktree_path
        
        # 必要に応じてブランチを作成
        create_branch_if_needed(TARGET_REPO, branch, current_branch)
        
        # worktreeをセットアップ
        setup_worktree(TARGET_REPO, worktree_path, branch)
    else:
        # gitリポジトリでない場合は通常のディレクトリを作成
        print(f"Note: {TARGET_REPO} is not a git repository")
        worktree_path.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {worktree_path}")
    
    return worktree_path


def ensure_main_window_layout():
    """メインウィンドウのレイアウトを確保"""
    # MAINウィンドウが存在するかチェック
    result = sh(f"tmux list-windows -t {TMUX_SESSION} -F '#{{window_name}}'", check=False)
    
    if result is None or "MAIN" not in str(result):
        # 存在しない場合は作成
        print("Creating MAIN window with initial layout")
        
        # セッションに最初のウィンドウがある場合は、それをリネーム
        first_window = sh(f"tmux list-windows -t {TMUX_SESSION} -F '#{{window_index}}'", check=False)
        if first_window:
            first_window_idx = first_window.strip().split('\n')[0]
            sh(f"tmux rename-window -t {TMUX_SESSION}:{first_window_idx} MAIN")
        else:
            # ウィンドウがない場合は新規作成
            sh(f"tmux new-window -t {TMUX_SESSION} -n MAIN 'bash'")
        time.sleep(TMUX_OPERATION_DELAY)
        
        # 左右に分割 - オプションなしで実行（互換性向上）
        sh(f"tmux split-window -h -t {TMUX_SESSION}:MAIN")
        
        # 左側を上下に分割 - PMAI用とダッシュボード用
        sh(f"tmux select-pane -t {TMUX_SESSION}:MAIN.0")
        sh(f"tmux split-window -v -t {TMUX_SESSION}:MAIN.0")
        
        # ダッシュボード起動（左下ペイン）
        dashboard_cmd = 'tail -F logs/bus.jsonl 2>/dev/null || echo "Waiting for logs..."'
        sh(f"tmux send-keys -t {TMUX_SESSION}:MAIN.{PANE_DASHBOARD} {shlex.quote(dashboard_cmd)} C-m")
        
        return False
    return True


def get_right_pane_for_child(child_count):
    """右側ペインに子エージェントを配置するためのペインを取得
    
    Args:
        child_count: 現在の子エージェント数（0ベース）
    
    Returns:
        str: tmuxペイン指定子 または None（ペイン作成失敗時）
    """
    right_base_pane = LAYOUT_RIGHT_BASE_PANE
    
    if child_count == 0:
        # 最初の子エージェント
        return f"{TMUX_SESSION}:MAIN.{right_base_pane}"
    else:
        # 既存の右側ペインを分割
        # 最後の右側ペインを取得して分割
        panes = sh(f"tmux list-panes -t {TMUX_SESSION}:MAIN -F '#{{pane_index}}'")
        if panes:
            last_pane = max([int(p) for p in panes.split('\n') if p])
            # 最後のペインを分割（エラーハンドリング付き）
            try:
                sh(f"tmux split-window -v -t {TMUX_SESSION}:MAIN.{last_pane}")
            except subprocess.CalledProcessError as e:
                if "no space for new pane" in str(e.stderr):
                    print(f"WARNING: No space for new pane, maximum panes reached")
                    return None
                raise
            time.sleep(TMUX_OPERATION_DELAY)
            # 新しく作られたペインのIDを取得
            new_panes = sh(f"tmux list-panes -t {TMUX_SESSION}:MAIN -F '#{{pane_index}}'")
            if new_panes:
                newest_pane = max([int(p) for p in new_panes.split('\n') if p])
                return f"{TMUX_SESSION}:MAIN.{newest_pane}"
    
    return None


# 子エージェントのカウント（グローバル） - 右側ペインの動的配置に使用
child_count = 0


def _determine_target_pane(task_id):
    """タスクIDに基づいて対象ペインを決定"""
    global child_count
    
    if task_id == "PMAI":
        # 親エージェントは左上ペインに配置
        target_pane = f"{TMUX_SESSION}:MAIN.{PANE_PMAI}"
        print(f"DEBUG: Placing PMAI in left-top pane (pane {PANE_PMAI})")
    else:
        # 子エージェントは右側に順番に配置
        target_pane = get_right_pane_for_child(child_count)
        child_count += 1
        print(f"DEBUG: Placing child {task_id} in right pane (child #{child_count})")
    
    if not target_pane:
        print(f"ERROR: Could not find target pane for {task_id} - maximum panes may have been reached")
        return None
    
    return target_pane


def _execute_in_pane(target_pane, worktree_path, task_id, goal=None):
    """対象ペインでコマンドを実行してペインIDを返す"""
    ai_app_studio_bin = str(AI_APP_STUDIO_ROOT / "bin")
    
    try:
        print(f"DEBUG: Setting up pane {target_pane}")
        
        # 1. 作業ディレクトリに移動
        sh(f"tmux send-keys -t {target_pane} 'cd {shlex.quote(str(worktree_path))}' Enter")
        time.sleep(POLLING_INTERVAL)
        
        # 2. 環境変数を設定
        sh(f"tmux send-keys -t {target_pane} 'export PATH=\"{ai_app_studio_bin}:$PATH\"' Enter")
        sh(f"tmux send-keys -t {target_pane} 'export ROOT=\"{str(ROOT)}\"' Enter")
        sh(f"tmux send-keys -t {target_pane} 'export TASK_ID=\"{task_id}\"' Enter")
        if goal:
            sh(f"tmux send-keys -t {target_pane} 'export TASK_GOAL=\"{goal}\"' Enter")
        if task_id == "PMAI":
            sh(f"tmux send-keys -t {target_pane} 'export TARGET_REPO=\"{str(TARGET_REPO)}\"' Enter")
        time.sleep(POLLING_INTERVAL)
        
        # 3. Claudeを起動
        sh(f"tmux send-keys -t {target_pane} '{CLAUDE_CMD}' Enter")
        
        print(f"DEBUG: Commands sent to pane {target_pane}")
        
        # 実際のペインIDを取得
        pane = sh(f"tmux display-message -p -t {target_pane} -F '#{{pane_id}}'")
        return pane
        
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to spawn in pane: {e}")
        print(f"ERROR stderr: {e.stderr}")
        raise


def _setup_pane_logging(task_id, pane):
    """ペインの出力ログを設定"""
    raw_log = LOGS / "raw" / f"{task_id}.raw"
    sh(f"tmux pipe-pane -o -t {pane} " +
       f"'stdbuf -oL -eL tee -a {shlex.quote(str(raw_log))}'")
    
    # pane_mapを更新
    pane_map[task_id] = pane
    save_pane_map()
    print(f"Spawned child {task_id} in pane {pane}")


def _send_initial_message(task_id, pane, frame=None, goal=None):
    """起動したエージェントに初期指示を送信"""
    # Claude Codeの起動を待つ
    time.sleep(CLAUDE_STARTUP_DELAY)
    
    # 親エージェントの指示
    if task_id == "PMAI" and frame and "pmai" in frame:
        init_message = (f"Read {frame} and follow the instructions to act as the Parent Agent. "
                       f"Process $TARGET_REPO/requirements.yml and spawn tasks using busctl commands.")
        sh(f"tmux send-keys -t {pane} -l {shlex.quote(init_message)}")
        sh(f"tmux send-keys -t {pane} Enter")
        print(f"Sent initial instructions to parent agent")
    
    # 子エージェントの指示
    elif frame and "impl" in frame and goal:
        init_message = (f"You are task {task_id}. Your goal: {goal}. "
                       f"Read {frame} for instructions on reporting progress with busctl post commands.")
        sh(f"tmux send-keys -t {pane} -l {shlex.quote(init_message)}")
        sh(f"tmux send-keys -t {pane} Enter")
        print(f"Sent initial instructions to child agent {task_id}")


def spawn_child(task_id, worktree_path, frame=None, goal=None):
    """子Claude Codeをtmux paneで起動（分割表示）"""
    print(f"DEBUG: Spawning child for task {task_id}, worktree: {worktree_path}")
    
    # worktreeディレクトリが存在することを確認
    if not worktree_path.exists():
        worktree_path.mkdir(parents=True, exist_ok=True)
        print(f"DEBUG: Created directory {worktree_path}")
    
    # メインウィンドウレイアウトを確保
    ensure_main_window_layout()
    
    # 1. ターゲットペインを決定
    target_pane = _determine_target_pane(task_id)
    if not target_pane:
        return None
    
    # 2. ペインでコマンドを実行
    pane = _execute_in_pane(target_pane, worktree_path, task_id, goal)
    
    # ペインが作成されたことを確認
    if not pane:
        raise RuntimeError(f"Failed to create tmux pane for task {task_id}")
    
    # 3. ロギングをセットアップ
    _setup_pane_logging(task_id, pane)
    
    # 4. 初期メッセージを送信
    _send_initial_message(task_id, pane, frame, goal)
    
    return pane


def handle_spawn(msg):
    """spawnメッセージを処理"""
    data = msg.get("data", {})
    task_id = msg["task_id"]
    
    branch = data.get("branch", f"feat/{task_id}")
    frame = data.get("frame", "")
    goal = data.get("goal", "")
    
    # PMAIは特別扱い - TARGET_REPO自体で動作
    if task_id == "PMAI":
        worktree_path = TARGET_REPO
        print(f"DEBUG: PMAI will run in TARGET_REPO: {worktree_path}")
    else:
        # 子タスクはサブディレクトリのworktreeで動作
        worktree_path = ensure_worktree(task_id, branch)
    
    # プロセス起動
    spawn_child(task_id, worktree_path, frame, goal)
    
    # タスク状態を記録
    tasks[task_id] = {
        "id": task_id,
        "status": "running",
        "created_at": msg.get("ts", int(time.time() * MS_PER_SECOND)),
        "cwd": str(worktree_path),
        "branch": branch,
        "goal": goal,
        "frame": frame
    }
    save_tasks()


def handle_send(msg):
    """sendメッセージを処理"""
    to = msg["to"]  # e.g. "impl:T001"
    
    # task_idを抽出
    if ":" in to:
        _, task_id = to.split(":", 1)
    else:
        task_id = to
    
    # paneを検索
    pane = pane_map.get(task_id)
    if not pane:
        print(f"Warning: No pane found for task {task_id}")
        return
    
    # データからテキストを抽出
    data = msg.get("data", {})
    if isinstance(data, dict):
        text = data.get("text", json.dumps(data, ensure_ascii=False))
    else:
        text = str(data)
    
    # tmux send-keys実行
    sh(f"tmux send-keys -t {pane} -l {shlex.quote(text)}")
    sh(f"tmux send-keys -t {pane} Enter")
    print(f"Sent to {task_id}: {text[:TEXT_PREVIEW_LENGTH]}...")


def handle_post(msg):
    """postメッセージを処理（log/result）"""
    # bus.jsonlに追記
    with BUS_LOG.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(msg, ensure_ascii=False) + "\n")
    
    # タスク状態を更新
    task_id = msg.get("task_id")
    msg_type = msg.get("type")
    
    if task_id and task_id in tasks:
        if msg_type == "result":
            # 結果メッセージの場合、ステータスを更新
            is_error = msg.get("data", {}).get("is_error", False)
            tasks[task_id]["status"] = "error" if is_error else "done"
            tasks[task_id]["completed_at"] = msg.get("ts", int(time.time() * MS_PER_SECOND))
            if "data" in msg:
                tasks[task_id]["result"] = msg["data"]
        
        save_tasks()
    
    print(f"Posted {msg_type} from {msg.get('from')} for task {task_id}")


def process_mailbox_once():
    """mailbox内のメッセージを一度処理"""
    # すべてのin/ディレクトリを走査
    for inbox_dir in MBOX.glob("*/in"):
        # JSONファイルを時刻順にソート
        json_files = sorted(inbox_dir.glob("*.json"))
        
        for json_file in json_files:
            try:
                # メッセージを読み込み
                msg = json.loads(json_file.read_text())
                msg_type = msg.get("type")
                
                print(f"Processing {msg_type} message from {json_file}")
                
                # メッセージタイプに応じて処理
                if msg_type == "spawn":
                    handle_spawn(msg)
                elif msg_type in ["send", "instruct"]:
                    handle_send(msg)
                else:
                    # log, result, error等はすべてpostとして扱う
                    handle_post(msg)
                
                # 処理済みファイルを削除
                json_file.unlink()
                
            except Exception as e:
                print(f"Error processing {json_file}: {e}")
                import traceback
                traceback.print_exc()
                # エラーが発生してもファイルは削除しない（再試行のため）


def main():
    """メインループ"""
    print(f"Starting busd daemon...")
    print(f"TARGET_REPO: {TARGET_REPO}")
    print(f"ROOT: {ROOT}")
    print(f"TMUX_SESSION: {TMUX_SESSION}")
    
    # 状態を復元
    load_state()
    
    # tmuxセッションを確保
    ensure_session()
    
    print("Monitoring mailboxes...")
    
    # メインループ
    try:
        while True:
            process_mailbox_once()
            time.sleep(POLLING_INTERVAL)  # 500msポーリング
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    main()