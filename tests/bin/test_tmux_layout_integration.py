#!/usr/bin/env python3
"""
tmuxレイアウト機能の包括的なテスト
展示会向けの4分割レイアウトの動作を詳細に検証
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


class TestTmuxLayoutComprehensive:
    """tmuxレイアウト機能の包括的テスト"""
    
    def setup_env(self):
        """テスト環境のセットアップ"""
        tmppath = Path(tempfile.mkdtemp())
        
        # 必要なディレクトリ構造を作成
        (tmppath / "logs" / "raw").mkdir(parents=True)
        (tmppath / "state").mkdir()
        (tmppath / "work").mkdir()
        (tmppath / "mbox" / "bus" / "in").mkdir(parents=True)
        (tmppath / "mbox" / "pmai" / "in").mkdir(parents=True)
        (tmppath / "logs" / "bus.jsonl").touch()
        
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
        
        # グローバル変数をリセット
        busd.child_count = 0
        busd.pane_map = {}
        
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
    
    def test_full_layout_with_pmai_and_children(self):
        """PMAIと複数の子エージェントを含む完全なレイアウトをテスト"""
        print("\n[TEST] test_full_layout_with_pmai_and_children")
        tmppath, test_session = self.setup_env()
        
        try:
            # tmuxセッションを作成
            busd.ensure_session()
            time.sleep(0.5)
            
            # 作業ディレクトリを作成
            for task in ["PMAI", "T001", "T002", "T003"]:
                (tmppath / "work" / task).mkdir(parents=True)
            
            # PMAIを起動（左上ペインに配置）
            pmai_pane = busd.spawn_child("PMAI", "work/PMAI", 
                                        "frames/pmai/CLAUDE.md", "Parent Agent")
            print(f"  PMAI pane: {pmai_pane}")
            
            # 子エージェントを3つ起動
            child_panes = []
            for i in range(1, 4):
                task_id = f"T00{i}"
                pane = busd.spawn_child(task_id, f"work/{task_id}", 
                                      "frames/impl/CLAUDE.md", f"Task {i}")
                child_panes.append(pane)
                print(f"  {task_id} pane: {pane}")
                time.sleep(0.2)
            
            # ペイン数を確認
            cmd = f"tmux list-panes -t {test_session}:MAIN -F '#{{pane_index}}:#{{pane_width}}x#{{pane_height}}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                panes = result.stdout.strip().split('\n')
                print(f"  Total panes: {len(panes)}")
                for pane in panes:
                    print(f"    {pane}")
                
                # 期待値：初期3ペイン + 子3つで分割 = 5ペイン以上
                if len(panes) >= 5:
                    print("  ✓ PASS: All agents spawned successfully")
                else:
                    print(f"  ✗ FAIL: Expected at least 5 panes, got {len(panes)}")
            else:
                print(f"  ✗ FAIL: Could not list panes: {result.stderr}")
            
            # pane_mapの内容を確認
            print(f"  pane_map: {busd.pane_map}")
            
            # 各エージェントがpane_mapに登録されているか確認
            expected_agents = ["PMAI", "T001", "T002", "T003"]
            all_registered = all(agent in busd.pane_map for agent in expected_agents)
            
            if all_registered:
                print("  ✓ PASS: All agents registered in pane_map")
            else:
                missing = [agent for agent in expected_agents if agent not in busd.pane_map]
                print(f"  ✗ FAIL: Missing agents in pane_map: {missing}")
            
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            traceback.print_exc()
        finally:
            self.teardown_env(tmppath, test_session)
    
    def test_layout_visual_structure(self):
        """レイアウトの視覚的構造をテスト"""
        print("\n[TEST] test_layout_visual_structure")
        tmppath, test_session = self.setup_env()
        
        try:
            # tmuxセッションを作成
            busd.ensure_session()
            time.sleep(0.5)
            
            # レイアウト文字列を取得
            cmd = f"tmux display-message -p -F '#{{window_layout}}' -t {test_session}:MAIN"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                layout = result.stdout.strip()
                print(f"  Layout string: {layout}")
                
                # レイアウト文字列に縦分割（,）と横分割（[］）が含まれているか確認
                if ',' in layout and '[' in layout:
                    print("  ✓ PASS: Layout contains both vertical and horizontal splits")
                else:
                    print("  ✗ FAIL: Layout structure is not as expected")
            else:
                print(f"  ✗ FAIL: Could not get layout: {result.stderr}")
            
            # 各ペインの役割を確認
            print("\n  Verifying pane roles:")
            
            # ペイン0（左上）の内容確認
            result = subprocess.run(f"tmux capture-pane -t {test_session}:MAIN.0 -p",
                                  shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                content = result.stdout[:100]
                print(f"    Pane 0 (PMAI): {content.strip()[:50] or '[empty]'}...")
            
            # ペイン1（左下）の内容確認
            result = subprocess.run(f"tmux capture-pane -t {test_session}:MAIN.1 -p",
                                  shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                content = result.stdout[:100]
                if "tail -F" in content or "Waiting for logs" in content:
                    print(f"    Pane 1 (Dashboard): ✓ Dashboard running")
                else:
                    print(f"    Pane 1 (Dashboard): ✗ Unexpected content")
            
            # ペイン2（右側）の確認
            result = subprocess.run(f"tmux capture-pane -t {test_session}:MAIN.2 -p",
                                  shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"    Pane 2 (Child area): Ready for children")
            
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            traceback.print_exc()
        finally:
            self.teardown_env(tmppath, test_session)
    
    def test_dynamic_child_placement(self):
        """子エージェントの動的配置をテスト"""
        print("\n[TEST] test_dynamic_child_placement")
        tmppath, test_session = self.setup_env()
        
        try:
            # tmuxセッションを作成
            busd.ensure_session()
            time.sleep(0.5)
            
            # 初期ペイン数を記録
            cmd = f"tmux list-panes -t {test_session}:MAIN -F '#{{pane_index}}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            initial_count = len(result.stdout.strip().split('\n'))
            print(f"  Initial pane count: {initial_count}")
            
            # 5つの子エージェントを順次追加
            for i in range(1, 6):
                task_id = f"T{i:03d}"
                (tmppath / "work" / task_id).mkdir(parents=True)
                
                pane = busd.spawn_child(task_id, f"work/{task_id}",
                                      "frames/impl/CLAUDE.md", f"Task {i}")
                
                # 現在のペイン数を確認
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                current_count = len(result.stdout.strip().split('\n'))
                
                print(f"  Added {task_id}: panes {initial_count} -> {current_count}")
                
                # child_countが正しく増加しているか確認
                if busd.child_count == i:
                    print(f"    ✓ child_count correctly = {i}")
                else:
                    print(f"    ✗ child_count = {busd.child_count}, expected {i}")
                
                time.sleep(0.1)
            
            # 最終的なペイン構成を表示
            cmd = f"tmux list-panes -t {test_session}:MAIN -F '#{{pane_index}}:#{{pane_title}}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            print("\n  Final pane configuration:")
            for line in result.stdout.strip().split('\n'):
                print(f"    {line}")
            
            # すべての子がpane_mapに登録されているか確認
            registered_count = sum(1 for k in busd.pane_map if k.startswith('T'))
            if registered_count == 5:
                print(f"  ✓ PASS: All 5 children registered")
            else:
                print(f"  ✗ FAIL: Only {registered_count} children registered")
            
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            traceback.print_exc()
        finally:
            self.teardown_env(tmppath, test_session)


def run_all_tests():
    """すべてのテストを実行"""
    print("=" * 60)
    print("Running comprehensive tmux layout tests")
    print("=" * 60)
    
    test = TestTmuxLayoutComprehensive()
    
    # 各テストを実行
    test.test_full_layout_with_pmai_and_children()
    test.test_layout_visual_structure()
    test.test_dynamic_child_placement()
    
    print("\n" + "=" * 60)
    print("Comprehensive test run completed")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()