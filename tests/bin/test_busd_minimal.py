#!/usr/bin/env python3
"""
busdの最小限のテスト - 何が問題か特定する
"""

import os
import sys
import tempfile
import json
from pathlib import Path

# ai-app-studioのパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "bin"))

def test_busd_minimal():
    """最小限のbusd動作確認"""
    with tempfile.TemporaryDirectory() as test_dir:
        print(f"Test directory: {test_dir}")
        
        # 環境設定
        os.environ['ROOT'] = test_dir
        os.environ['TMUX_SESSION'] = 'test-minimal'
        os.environ['CLAUDE_CMD'] = 'echo "Mock Claude"'
        
        # 必要なディレクトリを作成
        for d in ['mbox/bus/in', 'mbox/pmai/in', 'logs/raw', 'state', 'work']:
            Path(test_dir, d).mkdir(parents=True, exist_ok=True)
        
        # busdをインポート
        try:
            import busd
            print("✓ busd imported successfully")
        except Exception as e:
            print(f"✗ Failed to import busd: {e}")
            return
        
        # mailbox処理をテスト
        # テストメッセージを作成
        test_msg = {
            "type": "log",
            "from": "test",
            "to": "pmai",
            "task_id": "TEST",
            "data": {"msg": "test message"}
        }
        
        msg_file = Path(test_dir, "mbox/pmai/in/test.json")
        msg_file.write_text(json.dumps(test_msg))
        
        print(f"Created test message: {msg_file}")
        
        # mailbox処理を一度実行
        try:
            busd.process_mailbox_once()
            print("✓ process_mailbox_once executed")
        except Exception as e:
            print(f"✗ Failed to process mailbox: {e}")
            import traceback
            traceback.print_exc()
        
        # bus.jsonlを確認
        bus_log = Path(test_dir, "logs/bus.jsonl")
        if bus_log.exists():
            print(f"✓ bus.jsonl created: {bus_log.stat().st_size} bytes")
            print(f"Content: {bus_log.read_text()}")
        else:
            print("✗ bus.jsonl not created")

if __name__ == '__main__':
    print("=== Minimal busd Test ===")
    test_busd_minimal()