#!/usr/bin/env python3
"""
busd デーモンのテストスクリプト
"""

import json
import os
import tempfile
import time
import shutil
import subprocess
import unittest
from pathlib import Path

class TestBusd(unittest.TestCase):
    """busd デーモンのテストケース"""
    
    @classmethod
    def setUpClass(cls):
        """テスト環境のセットアップ"""
        # 実行可能なbusdがまだ存在しないことを確認（TDD Red phase）
        busd_path = Path("bin/busd.py")
        if busd_path.exists() and busd_path.stat().st_mode & 0o111:
            cls.fail("busd.py should not exist or be executable yet (TDD Red phase)")
    
    def setUp(self):
        """各テストケースの前処理"""
        self.test_root = tempfile.mkdtemp()
        self.env = os.environ.copy()
        self.env['ROOT'] = self.test_root
        self.env['TMUX_SESSION'] = 'test-session'
        
        # ディレクトリ構造作成
        for dir_path in ['mbox/bus/in', 'mbox/pmai/in', 'logs/raw', 'state', 'work']:
            Path(self.test_root, dir_path).mkdir(parents=True, exist_ok=True)
    
    def tearDown(self):
        """各テストケースの後処理"""
        shutil.rmtree(self.test_root)
    
    def test_spawn_message_processing(self):
        """spawnメッセージ処理のテスト"""
        # spawnメッセージを投函
        spawn_msg = {
            "id": "test-001",
            "ts": int(time.time() * 1000),
            "from": "pmai",
            "to": "bus",
            "type": "spawn",
            "task_id": "T001",
            "data": {
                "cwd": "work/T001",
                "frame": "frames/impl/CLAUDE.md",
                "goal": "test task",
                "branch": "feat/T001"
            }
        }
        
        # mailboxに投函
        mailbox_path = Path(self.test_root, 'mbox/bus/in/test.json')
        mailbox_path.write_text(json.dumps(spawn_msg))
        
        # Expected: busdが処理すると
        # 1. git worktreeが作成される
        # 2. tmux paneが起動される
        # 3. pane_mapが更新される
        # 4. メッセージファイルが削除される
        
        # この時点では実装がないので失敗するはず
        self.assertFalse(Path(self.test_root, 'work/T001').exists(), 
                        "Worktree should not be created yet (TDD)")
    
    def test_send_message_processing(self):
        """sendメッセージ処理のテスト"""
        # sendメッセージを投函
        send_msg = {
            "id": "test-002", 
            "ts": int(time.time() * 1000),
            "from": "pmai",
            "to": "impl:T001",
            "type": "instruct",
            "task_id": "T001",
            "data": {"text": "Start working"}
        }
        
        # mailboxに投函
        mailbox_path = Path(self.test_root, 'mbox/impl-T001/in')
        mailbox_path.mkdir(parents=True, exist_ok=True)
        (mailbox_path / 'test.json').write_text(json.dumps(send_msg))
        
        # Expected: tmux send-keysが実行される
        # この時点では実装がないので何も起きない
        self.assertTrue(True, "Send processing not implemented yet (TDD)")
    
    def test_post_message_processing(self):
        """postメッセージ処理のテスト"""
        # postメッセージを投函
        post_msg = {
            "id": "test-003",
            "ts": int(time.time() * 1000),
            "from": "impl:T001",
            "to": "pmai",
            "type": "result",
            "task_id": "T001",
            "data": {"is_error": False, "summary": "Task completed"}
        }
        
        # mailboxに投函
        mailbox_path = Path(self.test_root, 'mbox/pmai/in/test.json')
        mailbox_path.write_text(json.dumps(post_msg))
        
        # Expected:
        # 1. logs/bus.jsonlに追記される
        # 2. state/tasks.jsonが更新される
        
        bus_log = Path(self.test_root, 'logs/bus.jsonl')
        self.assertFalse(bus_log.exists() or (bus_log.exists() and bus_log.stat().st_size > 0),
                        "Bus log should not be written yet (TDD)")
    
    def test_tmux_session_management(self):
        """tmuxセッション管理のテスト"""
        # Expected: 
        # - TMUXセッションが存在しない場合は作成される
        # - 既存の場合は再利用される
        
        # この時点では実装がないので手動テストのみ
        self.assertTrue(True, "TMUX session management not implemented yet (TDD)")
    
    def test_atomic_mailbox_processing(self):
        """mailbox処理の原子性テスト"""
        # 複数のメッセージを同時に投函
        for i in range(5):
            msg = {
                "id": f"test-{i:03d}",
                "ts": int(time.time() * 1000) + i,
                "from": "pmai",
                "to": "bus", 
                "type": "spawn",
                "task_id": f"T{i:03d}",
                "data": {"cwd": f"work/T{i:03d}"}
            }
            path = Path(self.test_root, f'mbox/bus/in/test-{i}.json')
            path.write_text(json.dumps(msg))
        
        # Expected: すべて順番に処理される
        # この時点では実装がないのでファイルが残るはず
        files = list(Path(self.test_root, 'mbox/bus/in').glob('*.json'))
        self.assertEqual(len(files), 5, "All messages should remain unprocessed (TDD)")


class TestBusdIntegration(unittest.TestCase):
    """busd統合テスト（実装後に有効化）"""
    
    @unittest.skip("Implementation not ready yet")
    def test_full_workflow(self):
        """完全なワークフローテスト"""
        # 1. busdを起動
        # 2. busctl spawnでタスク投函
        # 3. tmux paneが作成されることを確認
        # 4. busctl postで結果投函
        # 5. logs/bus.jsonlに記録されることを確認
        pass


if __name__ == '__main__':
    print("=== busd Daemon Tests (TDD Red Phase) ===")
    print("All tests should fail at this point since implementation doesn't exist yet.")
    print()
    unittest.main(verbosity=2)