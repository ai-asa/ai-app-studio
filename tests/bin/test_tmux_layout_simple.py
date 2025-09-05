#!/usr/bin/env python3
"""
tmuxレイアウト機能のテスト（TDD - Red Phase）
展示会向けの4分割レイアウトをテストする
pytest無しで実行可能なバージョン
"""
import subprocess
import time
import os
import sys
import tempfile
from pathlib import Path
import traceback

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bin import busd


class TestTmuxLayout:
    """tmuxレイアウト機能のテスト"""
    
    def setup_env(self):
        """テスト環境のセットアップ"""
        tmppath = Path(tempfile.mkdtemp())
        
        # 必要なディレクトリ構造を作成
        (tmppath / "logs" / "raw").mkdir(parents=True)
        (tmppath / "state").mkdir()
        (tmppath / "work").mkdir()
        (tmppath / "mbox" / "bus" / "in").mkdir(parents=True)
        (tmppath / "mbox" / "pmai" / "in").mkdir(parents=True)
        
        # 環境変数を保存
        self.original_root = os.environ.get("ROOT")
        self.original_session = os.environ.get("TMUX_SESSION")
        
        # 環境変数を設定
        os.environ["ROOT"] = str(tmppath)
        test_session = f"test-{os.getpid()}"
        os.environ["TMUX_SESSION"] = test_session
        
        # モジュール変数を更新
        busd.ROOT = tmppath
        busd.MBOX = tmppath / "mbox"
        busd.LOGS = tmppath / "logs" 
        busd.STATE = tmppath / "state"
        busd.WORK = tmppath / "work"
        busd.BUS_LOG = tmppath / "logs" / "bus.jsonl"
        busd.PANES_FILE = tmppath / "state" / "panes.json"
        busd.TASKS_FILE = tmppath / "state" / "tasks.json"
        busd.TMUX_SESSION = test_session
        
        # テスト用tmuxセッションをクリーンアップ
        subprocess.run(f"tmux kill-session -t {test_session}", 
                     shell=True, capture_output=True)
        
        return tmppath, test_session
    
    def teardown_env(self, tmppath, test_session):
        """テスト環境のクリーンアップ"""
        # クリーンアップ
        subprocess.run(f"tmux kill-session -t {test_session}", 
                     shell=True, capture_output=True)
        
        # 環境変数を復元
        if self.original_root:
            os.environ["ROOT"] = self.original_root
        else:
            os.environ.pop("ROOT", None)
        
        if self.original_session:
            os.environ["TMUX_SESSION"] = self.original_session
        else:
            os.environ.pop("TMUX_SESSION", None)
        
        # 一時ディレクトリを削除
        import shutil
        shutil.rmtree(tmppath)
    
    def test_ensure_main_window_creates_panes(self):
        """ensure_main_window_layout()が複数のペインを作成することをテスト"""
        print("\n[TEST] ensure_main_window_creates_panes")
        tmppath, test_session = self.setup_env()
        
        try:
            # tmuxセッションを作成
            busd.ensure_session()
            time.sleep(0.5)  # tmuxの処理を待つ
            
            # MAINウィンドウのペイン数を確認
            cmd = f"tmux list-panes -t {test_session}:MAIN -F '#{{pane_index}}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            # 出力をパース
            if result.returncode == 0:
                panes = result.stdout.strip().split('\n')
                pane_count = len([p for p in panes if p])
            else:
                pane_count = 0
            
            # 最低3つのペインが作成されているはず
            if pane_count >= 3:
                print(f"  ✓ PASS: {pane_count} panes created")
            else:
                print(f"  ✗ FAIL: Expected at least 3 panes, got {pane_count}")
                print(f"    stdout: {result.stdout}")
                print(f"    stderr: {result.stderr}")
            
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            traceback.print_exc()
        finally:
            self.teardown_env(tmppath, test_session)
    
    def test_dashboard_starts_in_correct_pane(self):
        """ダッシュボードが正しいペイン（左下）で起動することをテスト"""
        print("\n[TEST] test_dashboard_starts_in_correct_pane")
        tmppath, test_session = self.setup_env()
        
        try:
            # bus.jsonlファイルを作成
            (tmppath / "logs" / "bus.jsonl").touch()
            
            # tmuxセッションを作成
            busd.ensure_session()
            time.sleep(1)  # ダッシュボードコマンドの実行を待つ
            
            # ペイン1（左下）のコマンドを取得
            cmd = f"tmux capture-pane -t {test_session}:MAIN.1 -p"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            # tailコマンドまたは"Waiting for logs"が実行されているか確認
            if "tail -F logs/bus.jsonl" in result.stdout or "Waiting for logs" in result.stdout:
                print("  ✓ PASS: Dashboard command found in pane 1")
            else:
                print("  ✗ FAIL: Dashboard command not found in pane 1")
                print(f"    Captured content: {result.stdout[:200]}")
                
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            traceback.print_exc()
        finally:
            self.teardown_env(tmppath, test_session)
    
    def test_spawn_children_layout(self):
        """子エージェントのレイアウト配置をテスト"""
        print("\n[TEST] test_spawn_children_layout")
        tmppath, test_session = self.setup_env()
        
        try:
            # グローバル変数をリセット
            busd.child_count = 0
            busd.pane_map = {}
            
            # tmuxセッションを作成
            busd.ensure_session()
            time.sleep(0.5)
            
            # 初期のペイン数を確認
            cmd = f"tmux list-panes -t {test_session}:MAIN -F '#{{pane_index}}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            initial_panes = len(result.stdout.strip().split('\n'))
            print(f"  Initial panes: {initial_panes}")
            
            # 子エージェント用のディレクトリを作成
            task_dir = tmppath / "work" / "T001"
            task_dir.mkdir(parents=True)
            
            # 最初の子エージェントを起動
            try:
                pane1 = busd.spawn_child("T001", "work/T001", "frames/impl/CLAUDE.md", "Task 1")
                print(f"  Spawned child T001, pane: {pane1}")
                time.sleep(0.5)
                
                # ペイン数を再確認
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                current_panes = result.stdout.strip().split('\n')
                print(f"  Current panes after spawn: {len(current_panes)}")
                print(f"  Pane indices: {current_panes}")
                
                if pane1 is not None and busd.child_count == 1:
                    print("  ✓ PASS: Child spawned successfully")
                else:
                    print(f"  ✗ FAIL: Failed to spawn child (pane={pane1}, child_count={busd.child_count})")
                    
            except Exception as spawn_error:
                print(f"  ✗ FAIL: Error spawning child: {spawn_error}")
                traceback.print_exc()
            
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            traceback.print_exc()
        finally:
            self.teardown_env(tmppath, test_session)
    
    def test_split_window_functionality(self):
        """split-window機能の基本動作をテスト"""
        print("\n[TEST] test_split_window_functionality")
        tmppath, test_session = self.setup_env()
        
        try:
            # 基本的なセッションを作成
            cmd = f"tmux new-session -d -s {test_session} -n TEST 'bash'"
            subprocess.run(cmd, shell=True, check=True)
            time.sleep(0.2)
            
            # 現在のペイン数を確認
            result = subprocess.run(f"tmux list-panes -t {test_session}:TEST", 
                                  shell=True, capture_output=True, text=True)
            initial_count = len(result.stdout.strip().split('\n'))
            print(f"  Initial panes: {initial_count}")
            
            # split-windowを試す（オプションなし）
            cmd = f"tmux split-window -t {test_session}:TEST"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                # 分割成功 - ペイン数を再確認
                result2 = subprocess.run(f"tmux list-panes -t {test_session}:TEST", 
                                       shell=True, capture_output=True, text=True)
                new_count = len(result2.stdout.strip().split('\n'))
                
                if new_count > initial_count:
                    print(f"  ✓ PASS: split-window succeeded (panes: {initial_count} -> {new_count})")
                else:
                    print(f"  ✗ FAIL: split-window did not increase pane count")
            else:
                print(f"  ✗ FAIL: split-window failed")
                print(f"    stderr: {result.stderr}")
                
                # 代替方法を試す
                print("  Trying alternative split methods...")
                
                # -p オプションを試す
                cmd_alt1 = f"tmux split-window -t {test_session}:TEST -p 50"
                result_alt1 = subprocess.run(cmd_alt1, shell=True, capture_output=True, text=True)
                print(f"    -p 50: {'OK' if result_alt1.returncode == 0 else 'FAIL'}")
                
                # -l オプションを試す
                cmd_alt2 = f"tmux split-window -t {test_session}:TEST -l 10"
                result_alt2 = subprocess.run(cmd_alt2, shell=True, capture_output=True, text=True)
                print(f"    -l 10: {'OK' if result_alt2.returncode == 0 else 'FAIL'}")
                
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            traceback.print_exc()
        finally:
            self.teardown_env(tmppath, test_session)


def run_all_tests():
    """すべてのテストを実行"""
    print("=" * 60)
    print("Running tmux layout tests (TDD - Red Phase)")
    print("=" * 60)
    
    test = TestTmuxLayout()
    
    # 各テストを実行
    test.test_ensure_main_window_creates_panes()
    test.test_dashboard_starts_in_correct_pane()
    test.test_spawn_children_layout()
    test.test_split_window_functionality()
    
    print("\n" + "=" * 60)
    print("Test run completed")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()