#!/usr/bin/env python3
"""
busdデーモンの基本動作テスト
"""

import json
import os
import tempfile
import time
import shutil
import sys
from pathlib import Path

# テストのために実際のbusdをインポート
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "bin"))

def test_message_processing():
    """メッセージ処理の基本テスト"""
    with tempfile.TemporaryDirectory() as test_root:
        # 環境設定
        os.environ['ROOT'] = test_root
        os.environ['TMUX_SESSION'] = 'test-session'
        
        # ディレクトリ構造作成
        for dir_path in ['mbox/bus/in', 'mbox/pmai/in', 'logs/raw', 'state', 'work']:
            Path(test_root, dir_path).mkdir(parents=True, exist_ok=True)
        
        # busdモジュールをインポート（ここで初期化される）
        import busd
        
        print(f"Test ROOT: {test_root}")
        
        # Test 1: Post message processing
        print("\n--- Test 1: Post message processing ---")
        post_msg = {
            "id": "test-001",
            "ts": int(time.time() * 1000),
            "from": "impl:T001",
            "to": "pmai",
            "type": "log",
            "task_id": "T001",
            "data": {"msg": "Test log message"}
        }
        
        # メッセージを投函
        msg_file = Path(test_root, 'mbox/pmai/in/test.json')
        msg_file.write_text(json.dumps(post_msg))
        
        # 処理実行
        busd.process_mailbox_once()
        
        # 確認
        bus_log = Path(test_root, 'logs/bus.jsonl')
        if bus_log.exists():
            lines = bus_log.read_text().strip().split('\n')
            print(f"✓ Bus log has {len(lines)} entries")
            if lines:
                logged_msg = json.loads(lines[0])
                print(f"✓ Logged message type: {logged_msg.get('type')}")
        else:
            print("✗ Bus log not created")
        
        # メッセージファイルが削除されたか確認
        if not msg_file.exists():
            print("✓ Message file was processed and deleted")
        else:
            print("✗ Message file still exists")
        
        # Test 2: State management
        print("\n--- Test 2: State management ---")
        
        # pane_mapのテスト
        busd.pane_map["T001"] = "test:T001.0"
        busd.save_pane_map()
        
        panes_file = Path(test_root, 'state/panes.json')
        if panes_file.exists():
            saved_panes = json.loads(panes_file.read_text())
            print(f"✓ Pane map saved: {saved_panes}")
        else:
            print("✗ Panes file not created")
        
        # tasksのテスト
        busd.tasks["T001"] = {
            "id": "T001",
            "status": "running",
            "created_at": int(time.time() * 1000)
        }
        busd.save_tasks()
        
        tasks_file = Path(test_root, 'state/tasks.json')
        if tasks_file.exists():
            saved_tasks = json.loads(tasks_file.read_text())
            print(f"✓ Tasks saved: {len(saved_tasks)} tasks")
        else:
            print("✗ Tasks file not created")
        
        print("\n✓ Basic tests completed successfully")


def test_mailbox_structure():
    """mailbox構造のテスト"""
    print("\n--- Test 3: Mailbox structure ---")
    
    with tempfile.TemporaryDirectory() as test_root:
        # busctl実行
        os.environ['ROOT'] = test_root
        
        # spawnメッセージ投函
        os.system(f'./bin/busctl spawn --task T001 --goal "test"')
        
        # 確認
        spawn_files = list(Path(test_root, 'mbox/bus/in').glob('*.json'))
        if spawn_files:
            print(f"✓ Spawn message created: {spawn_files[0].name}")
            content = json.loads(spawn_files[0].read_text())
            print(f"  Type: {content.get('type')}")
            print(f"  Task: {content.get('task_id')}")
        else:
            print("✗ No spawn message created")
        
        # sendメッセージ投函
        os.system(f'./bin/busctl send --to impl:T001 --type instruct --data \'{{"text":"hello"}}\'')
        
        send_files = list(Path(test_root, 'mbox/impl-T001/in').glob('*.json'))
        if send_files:
            print(f"✓ Send message created: {send_files[0].name}")
        else:
            print("✗ No send message created")
        
        # postメッセージ投函
        os.system(f'./bin/busctl post --from impl:T001 --type result --task T001 --data \'{{"is_error":false}}\'')
        
        post_files = list(Path(test_root, 'mbox/pmai/in').glob('*.json'))
        if post_files:
            print(f"✓ Post message created: {post_files[0].name}")
        else:
            print("✗ No post message created")


if __name__ == '__main__':
    print("=== busd Basic Tests ===")
    test_message_processing()
    test_mailbox_structure()
    print("\n✓ All basic tests completed")