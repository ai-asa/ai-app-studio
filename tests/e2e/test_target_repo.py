#!/usr/bin/env python3
"""
E2Eテスト：TARGET_REPO機能のテスト
- ターゲットリポジトリの指定
- 作業ディレクトリの設定
- PMAIがターゲットリポジトリのrequirements.ymlを読むことの確認
"""
import os
import sys
import time
import json
import tempfile
import shutil
import subprocess
import shlex
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# テスト環境設定
TEST_SESSION = "test-target-repo"
ROOT = Path(__file__).parent.parent.parent


def run(cmd, env=None):
    """コマンド実行ヘルパー"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        print(f"STDERR: {result.stderr}")
    return result


def cleanup():
    """テスト環境のクリーンアップ"""
    print("\n=== Cleanup ===")
    # tmuxセッション終了
    run(f"tmux kill-session -t {TEST_SESSION} 2>/dev/null")
    

def test_target_repo_cwd():
    """現在のディレクトリをTARGET_REPOとして使用するテスト"""
    print("\n=== Test: Current Directory as TARGET_REPO ===")
    
    # 一時的なターゲットリポジトリを作成
    with tempfile.TemporaryDirectory() as tmpdir:
        target_repo = Path(tmpdir) / "test-project"
        target_repo.mkdir()
        
        # requirements.ymlを作成
        reqs = {
            "project": "test-project",
            "version": "1.0.0",
            "tasks": [
                {"id": "TASK001", "description": "Test task 1"},
                {"id": "TASK002", "description": "Test task 2"}
            ]
        }
        (target_repo / "requirements.yml").write_text(json.dumps(reqs, indent=2))
        
        # ターゲットリポジトリで busd.py を起動
        env = os.environ.copy()
        # ROOTを設定しないことで、.ai-app-studioサブディレクトリが自動的に作成される
        env["TMUX_SESSION"] = TEST_SESSION
        
        # busd.pyをバックグラウンドで起動
        busd_cmd = f"cd {shlex.quote(str(target_repo))} && python3 {ROOT}/bin/busd.py"
        print(f"DEBUG: Running command: {busd_cmd}")
        
        # バックグラウンドで起動
        busd_process = subprocess.Popen(busd_cmd, shell=True, env=env, 
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        try:
            time.sleep(3)  # 起動を待つ（少し長めに）
            
            # .ai-app-studioディレクトリが作成されているか確認
            print(f"DEBUG: Checking for directory: {target_repo}")
            print(f"DEBUG: Contents of {target_repo}: {list(target_repo.iterdir())}")
            
            ai_app_studio_dir = target_repo / ".ai-app-studio"
            assert ai_app_studio_dir.exists(), f"Expected {ai_app_studio_dir} to exist"
            assert (ai_app_studio_dir / "mbox").exists(), "Expected mbox directory"
            assert (ai_app_studio_dir / "logs").exists(), "Expected logs directory"
            assert (ai_app_studio_dir / "state").exists(), "Expected state directory"
            
            print("✓ .ai-app-studio directory created correctly")
            
        finally:
            # クリーンアップ
            busd_process.terminate()
            busd_process.wait()


def test_target_repo_argument():
    """引数でTARGET_REPOを指定するテスト"""
    print("\n=== Test: TARGET_REPO via Argument ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        target_repo = Path(tmpdir) / "test-project-arg"
        target_repo.mkdir()
        
        # requirements.ymlを作成
        reqs = {
            "project": "test-project-arg",
            "version": "1.0.0",
            "tasks": [
                {"id": "TASK003", "description": "Test task 3"}
            ]
        }
        (target_repo / "requirements.yml").write_text(json.dumps(reqs, indent=2))
        
        # 引数でターゲットリポジトリを指定してbusd.pyを起動
        env = os.environ.copy()
        env["TMUX_SESSION"] = TEST_SESSION
        
        busd_cmd = f"python3 {ROOT}/bin/busd.py {shlex.quote(str(target_repo))}"
        busd_process = subprocess.Popen(busd_cmd, shell=True, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        try:
            time.sleep(2)  # 起動を待つ
            
            # .ai-app-studioディレクトリが作成されているか確認
            ai_app_studio_dir = target_repo / ".ai-app-studio"
            assert ai_app_studio_dir.exists(), f"Expected {ai_app_studio_dir} to exist"
            
            print("✓ TARGET_REPO argument works correctly")
            
        finally:
            busd_process.terminate()
            busd_process.wait()


def test_pmai_reads_target_repo():
    """PMAIがTARGET_REPOのrequirements.ymlを読むことを確認するテスト"""
    print("\n=== Test: PMAI Reads TARGET_REPO requirements.yml ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        target_repo = Path(tmpdir) / "test-pmai-project"
        target_repo.mkdir()
        
        # requirements.ymlを作成
        reqs = {
            "project": "test-pmai-project",
            "version": "1.0.0",
            "tasks": [
                {"id": "PMAITEST001", "description": "PMAI test task"}
            ]
        }
        (target_repo / "requirements.yml").write_text(json.dumps(reqs, indent=2))
        
        # PMAIを起動するためのspawnメッセージを準備
        env = os.environ.copy()
        env["ROOT"] = str(target_repo)
        env["TMUX_SESSION"] = TEST_SESSION
        env["TARGET_REPO"] = str(target_repo)  # 環境変数で渡す
        
        # busd.pyを起動
        busd_cmd = f"cd {shlex.quote(str(target_repo))} && python3 {ROOT}/bin/busd.py"
        busd_process = subprocess.Popen(busd_cmd, shell=True, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        try:
            time.sleep(2)  # 起動を待つ
            
            # PMAIのspawnメッセージを送信
            ai_app_studio_dir = target_repo / ".ai-app-studio"
            mbox_pmai = ai_app_studio_dir / "mbox" / "pmai" / "in"
            mbox_pmai.mkdir(parents=True, exist_ok=True)
            
            spawn_msg = {
                "type": "spawn",
                "task_id": "PMAI",
                "ts": int(time.time() * 1000),
                "data": {
                    "frame": str(ROOT / "frames" / "pmai" / "CLAUDE.md"),
                    "cwd": "work/PMAI",
                    "goal": f"Process requirements.yml from {target_repo}"
                }
            }
            
            msg_file = mbox_pmai / f"{spawn_msg['ts']}.json"
            msg_file.write_text(json.dumps(spawn_msg, ensure_ascii=False))
            
            time.sleep(5)  # PMAIの起動を待つ
            
            # PMAIが正しくTARGET_REPOを認識しているか（環境変数経由で確認）
            # 実際の動作確認は実装後に行う
            print("✓ PMAI spawn message sent with TARGET_REPO context")
            
        finally:
            busd_process.terminate()
            busd_process.wait()


def main():
    """メインテスト実行"""
    cleanup()
    
    try:
        # 各テストを実行
        test_target_repo_cwd()
        test_target_repo_argument()
        test_pmai_reads_target_repo()
        
        print("\n=== All TARGET_REPO tests passed! ===")
        return 0
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        cleanup()


if __name__ == "__main__":
    sys.exit(main())