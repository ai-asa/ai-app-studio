#!/usr/bin/env python3
"""
E2Eテスト：親起動 → spawn投函 → 子起動確認
"""
import os
import sys
import time
import json
import subprocess
import shlex
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# テスト環境設定
TEST_SESSION = "test-e2e"
TEST_TASK_ID = "E2ETEST001"
ROOT = Path(__file__).parent.parent.parent


def run(cmd):
    """コマンド実行ヘルパー"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"STDERR: {result.stderr}")
    return result


def cleanup():
    """テスト環境のクリーンアップ"""
    print("\n=== Cleanup ===")
    # tmuxセッション終了
    run(f"tmux kill-session -t {TEST_SESSION} 2>/dev/null")
    
    # メールボックスクリア
    run("rm -f mbox/*/in/*.json 2>/dev/null")
    
    # ログクリア
    run("rm -f logs/raw/*.raw 2>/dev/null")
    run("rm -f logs/bus.jsonl 2>/dev/null")
    
    # 状態クリア
    run("rm -f state/*.json 2>/dev/null")
    
    # ワークツリー削除
    run(f"rm -rf work/{TEST_TASK_ID} 2>/dev/null")
    run(f"git worktree prune 2>/dev/null")
    run(f"git branch -D feat/{TEST_TASK_ID} 2>/dev/null")


def test_pane_id_fix():
    """修正されたpane ID取得のテスト"""
    print("\n=== Test: Pane ID取得の修正確認 ===")
    
    # 1. テスト用tmuxセッション作成
    print("1. Creating test tmux session...")
    run(f"tmux new-session -d -s {TEST_SESSION} -n test 'sleep 30'")
    
    # 2. pane ID取得テスト（修正されたフォーマット）
    print("2. Testing pane ID retrieval with fixed format...")
    cmd = f"tmux list-panes -t {TEST_SESSION}:test -F '#{{session_name}}:#{{window_name}}.#{{pane_index}}'"
    result = run(cmd)
    
    if result.returncode == 0:
        pane_id = result.stdout.strip()
        print(f"✓ Pane ID successfully retrieved: {pane_id}")
        
        # 期待される形式をチェック
        if f"{TEST_SESSION}:test.0" == pane_id:
            print("✓ Pane ID format is correct")
            return True
        else:
            print(f"✗ Unexpected pane ID format: {pane_id}")
            return False
    else:
        print("✗ Failed to retrieve pane ID")
        return False


def test_full_flow():
    """完全なフロー：spawn → 子起動 → post確認"""
    print("\n=== Test: Full E2E Flow ===")
    
    # 環境変数設定
    os.environ['TMUX_SESSION'] = 'cc'
    os.environ['ROOT'] = str(ROOT)
    
    # 1. busdをバックグラウンドで起動
    print("1. Starting busd daemon...")
    busd_proc = subprocess.Popen(
        ['python3', str(ROOT / 'bin' / 'busd.py')],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(2)  # 起動待ち
    
    try:
        # 2. busctlでspawn投函
        print(f"2. Spawning task {TEST_TASK_ID}...")
        cmd = (f"{ROOT}/bin/busctl spawn "
               f"--task {TEST_TASK_ID} "
               f"--cwd work/{TEST_TASK_ID} "
               f"--frame frames/impl/CLAUDE.md "
               f"--goal 'E2E test task'")
        result = run(cmd)
        
        if result.returncode != 0:
            print("✗ Failed to spawn task")
            return False
        
        # 3. 処理待機
        print("3. Waiting for busd to process...")
        time.sleep(3)
        
        # 4. tmuxウィンドウ確認
        print("4. Checking tmux windows...")
        result = run("tmux list-windows -t cc 2>/dev/null")
        
        if TEST_TASK_ID in result.stdout:
            print(f"✓ Task window created: {TEST_TASK_ID}")
        else:
            print(f"✗ Task window not found")
            print(f"Current windows: {result.stdout}")
            
        # 5. state/panes.json確認
        print("5. Checking panes.json...")
        panes_file = ROOT / "state" / "panes.json"
        
        if panes_file.exists():
            with open(panes_file) as f:
                panes = json.load(f)
                if TEST_TASK_ID in panes:
                    print(f"✓ Task registered in panes.json: {panes[TEST_TASK_ID]}")
                else:
                    print(f"✗ Task not found in panes.json")
                    print(f"Current panes: {panes}")
        else:
            print("✗ panes.json not found")
            
        # 6. ログ確認
        print("6. Checking logs...")
        raw_log = ROOT / "logs" / "raw" / f"{TEST_TASK_ID}.raw"
        if raw_log.exists():
            print(f"✓ Raw log created: {raw_log}")
        else:
            print(f"✗ Raw log not found")
            
    finally:
        # busd停止
        print("\n7. Stopping busd...")
        busd_proc.terminate()
        busd_proc.wait(timeout=5)
        

def main():
    """メインテスト実行"""
    print("=== AI App Studio E2E Test ===")
    print(f"Project root: {ROOT}")
    
    # クリーンアップ
    cleanup()
    
    # テスト実行
    success = True
    
    # Pane ID修正テスト
    if not test_pane_id_fix():
        success = False
    
    # フルフローテスト
    test_full_flow()
    
    # 最終クリーンアップ
    cleanup()
    
    print("\n=== Test Complete ===")
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()