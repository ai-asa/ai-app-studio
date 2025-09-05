#!/usr/bin/env python3
"""
tmuxレイアウト機能のテスト（TDD - Red Phase）
展示会向けの4分割レイアウトをテストする
"""
import pytest
import subprocess
import time
import os
import sys
import tempfile
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bin import busd


class TestTmuxLayout:
    """tmuxレイアウト機能のテスト"""
    
    @pytest.fixture
    def setup_env(self):
        """テスト環境のセットアップ"""
        # 一時ディレクトリ作成
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # 必要なディレクトリ構造を作成
            (tmppath / "logs" / "raw").mkdir(parents=True)
            (tmppath / "state").mkdir()
            (tmppath / "work").mkdir()
            (tmppath / "mbox" / "bus" / "in").mkdir(parents=True)
            (tmppath / "mbox" / "pmai" / "in").mkdir(parents=True)
            
            # 環境変数を設定
            original_root = os.environ.get("ROOT")
            original_session = os.environ.get("TMUX_SESSION")
            
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
            
            yield tmppath, test_session
            
            # クリーンアップ
            subprocess.run(f"tmux kill-session -t {test_session}", 
                         shell=True, capture_output=True)
            
            # 環境変数を復元
            if original_root:
                os.environ["ROOT"] = original_root
            else:
                os.environ.pop("ROOT", None)
            
            if original_session:
                os.environ["TMUX_SESSION"] = original_session
            else:
                os.environ.pop("TMUX_SESSION", None)
    
    def test_ensure_main_window_creates_4_panes(self, setup_env):
        """ensure_main_window_layout()が4つのペインを作成することをテスト"""
        tmppath, test_session = setup_env
        
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
        
        # 4つのペインが作成されているはず
        # 左上: PMAI, 左下: ダッシュボード, 右上: 子AI 1, 右下: 子AI 2（初期は2つ）
        assert pane_count >= 3, f"Expected at least 3 panes, got {pane_count}"
    
    def test_main_window_layout_structure(self, setup_env):
        """MAINウィンドウのレイアウト構造をテスト"""
        tmppath, test_session = setup_env
        
        # tmuxセッションを作成
        busd.ensure_session()
        time.sleep(0.5)
        
        # ペインのレイアウト情報を取得
        cmd = f"tmux list-panes -t {test_session}:MAIN -F '#{{pane_index}} #{{pane_width}} #{{pane_height}}'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        assert result.returncode == 0, "Failed to get pane layout info"
        
        # ペイン情報をパース
        panes = []
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split()
                if len(parts) >= 3:
                    panes.append({
                        'index': int(parts[0]),
                        'width': int(parts[1]),
                        'height': int(parts[2])
                    })
        
        # 最低3つのペインがあることを確認
        assert len(panes) >= 3, f"Expected at least 3 panes, got {len(panes)}"
        
        # レイアウト構造をテスト
        # ペイン0とペイン1は左側にあり、同じ幅を持つはず
        # ペイン2は右側にあり、より広い幅を持つはず
        if len(panes) >= 3:
            # 左側のペイン（0,1）は同じ幅
            assert abs(panes[0]['width'] - panes[1]['width']) <= 5, \
                f"Left panes should have similar width: {panes[0]['width']} vs {panes[1]['width']}"
            
            # 右側のペイン（2）は左側より広い
            assert panes[2]['width'] > panes[0]['width'], \
                f"Right pane should be wider than left panes: {panes[2]['width']} vs {panes[0]['width']}"
    
    def test_dashboard_starts_in_correct_pane(self, setup_env):
        """ダッシュボードが正しいペイン（左下）で起動することをテスト"""
        tmppath, test_session = setup_env
        
        # bus.jsonlファイルを作成
        (tmppath / "logs" / "bus.jsonl").touch()
        
        # tmuxセッションを作成
        busd.ensure_session()
        time.sleep(1)  # ダッシュボードコマンドの実行を待つ
        
        # ペイン1（左下）のコマンドを取得
        cmd = f"tmux capture-pane -t {test_session}:MAIN.1 -p"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        # tailコマンドまたは"Waiting for logs"が実行されているか確認
        assert "tail -F logs/bus.jsonl" in result.stdout or \
               "Waiting for logs" in result.stdout, \
               f"Dashboard command not found in pane 1: {result.stdout[:100]}"
    
    def test_spawn_pmai_in_left_top(self, setup_env):
        """PMAIエージェントが左上ペインに配置されることをテスト"""
        tmppath, test_session = setup_env
        
        # グローバル変数をリセット
        busd.child_count = 0
        busd.pane_map = {}
        
        # tmuxセッションを作成
        busd.ensure_session()
        time.sleep(0.5)
        
        # PMAI用のディレクトリを作成
        pmai_dir = tmppath / "work" / "PMAI"
        pmai_dir.mkdir(parents=True)
        
        # PMAIエージェントを起動
        pane = busd.spawn_child("PMAI", "work/PMAI", "frames/pmai/CLAUDE.md", "Parent Agent")
        
        # ペインIDが取得できたか確認
        assert pane is not None, "Failed to get pane ID for PMAI"
        
        # pane_mapに記録されているか確認
        assert "PMAI" in busd.pane_map, "PMAI not found in pane_map"
        
        # PMAIがペイン0（左上）に配置されているか確認
        # capture-paneでペイン0の内容を確認
        cmd = f"tmux capture-pane -t {test_session}:MAIN.0 -p"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        # Claude Codeコマンドが実行されているか確認
        assert "claude code" in result.stdout or "work/PMAI" in result.stdout, \
               f"PMAI command not found in pane 0: {result.stdout[:100]}"
    
    def test_spawn_children_in_right_panes(self, setup_env):
        """子エージェントが右側ペインに順番に配置されることをテスト"""
        tmppath, test_session = setup_env
        
        # グローバル変数をリセット
        busd.child_count = 0
        busd.pane_map = {}
        
        # tmuxセッションを作成
        busd.ensure_session()
        time.sleep(0.5)
        
        # 子エージェント用のディレクトリを作成
        for i in range(1, 3):
            task_dir = tmppath / "work" / f"T00{i}"
            task_dir.mkdir(parents=True)
        
        # 最初の子エージェントを起動
        pane1 = busd.spawn_child("T001", "work/T001", "frames/impl/CLAUDE.md", "Task 1")
        assert pane1 is not None, "Failed to spawn first child"
        assert busd.child_count == 1, f"Expected child_count=1, got {busd.child_count}"
        
        time.sleep(0.5)
        
        # ペイン数を確認（最初の子で右側ペインを使用）
        cmd = f"tmux list-panes -t {test_session}:MAIN -F '#{{pane_index}}'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        initial_panes = len(result.stdout.strip().split('\n'))
        
        # 2番目の子エージェントを起動
        pane2 = busd.spawn_child("T002", "work/T002", "frames/impl/CLAUDE.md", "Task 2")
        assert pane2 is not None, "Failed to spawn second child"
        assert busd.child_count == 2, f"Expected child_count=2, got {busd.child_count}"
        
        time.sleep(0.5)
        
        # ペイン数が増えているか確認
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        final_panes = len(result.stdout.strip().split('\n'))
        assert final_panes > initial_panes, \
               f"Expected pane count to increase, but got {initial_panes} -> {final_panes}"
        
        # 両方の子がpane_mapに記録されているか確認
        assert "T001" in busd.pane_map, "T001 not found in pane_map"
        assert "T002" in busd.pane_map, "T002 not found in pane_map"
    
    def test_get_right_pane_for_child(self, setup_env):
        """get_right_pane_for_child関数の動作をテスト"""
        tmppath, test_session = setup_env
        
        # tmuxセッションを作成
        busd.ensure_session()
        time.sleep(0.5)
        
        # child_count=0の場合、ベースペイン（2）を返すはず
        pane = busd.get_right_pane_for_child(0)
        assert pane == f"{test_session}:MAIN.2", \
               f"Expected base right pane, got {pane}"
        
        # child_count>0の場合、新しいペインが作成されるはず
        initial_pane_count = len(subprocess.run(
            f"tmux list-panes -t {test_session}:MAIN -F '#{{pane_index}}'",
            shell=True, capture_output=True, text=True
        ).stdout.strip().split('\n'))
        
        pane = busd.get_right_pane_for_child(1)
        assert pane is not None, "Failed to get pane for second child"
        
        # ペイン数が増えているか確認
        final_pane_count = len(subprocess.run(
            f"tmux list-panes -t {test_session}:MAIN -F '#{{pane_index}}'",
            shell=True, capture_output=True, text=True
        ).stdout.strip().split('\n'))
        
        assert final_pane_count > initial_pane_count, \
               "New pane should have been created"
    
    def test_layout_preserves_window_size(self, setup_env):
        """レイアウト作成時にウィンドウサイズが保持されることをテスト"""
        tmppath, test_session = setup_env
        
        # tmuxセッションを作成（アタッチされた状態をシミュレート）
        # 最初に明示的なサイズでウィンドウを作成
        cmd = f"tmux new-session -d -s {test_session} -x 120 -y 40 -n TEMP 'bash'"
        subprocess.run(cmd, shell=True)
        time.sleep(0.1)
        
        # ensure_sessionを呼び出す（レイアウト作成）
        busd.ensure_session()
        time.sleep(0.5)
        
        # ウィンドウサイズを確認
        cmd = f"tmux list-windows -t {test_session} -F '#{{window_width}} #{{window_height}}'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout.strip():
            sizes = result.stdout.strip().split('\n')
            for size in sizes:
                if size:
                    width, height = map(int, size.split())
                    # サイズが0でないことを確認
                    assert width > 0, f"Window width should be positive, got {width}"
                    assert height > 0, f"Window height should be positive, got {height}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])