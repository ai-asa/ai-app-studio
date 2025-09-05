#!/usr/bin/env python3
"""
E2Eテスト：send/post機能の統合テスト
親→子へのsend、子→親へのpostの完全な動作確認
"""
import os
import sys
import time
import json
import subprocess
import tempfile
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# テスト環境設定
TEST_SESSION = "test-sendpost"
TEST_TASK_ID = "SENDPOST001"
ROOT = Path(__file__).parent.parent.parent


def run(cmd):
    """コマンド実行ヘルパー"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"STDERR: {result.stderr}")
    return result


def create_test_message(msg_type, task_id, data):
    """テストメッセージを作成"""
    import time
    timestamp = int(time.time() * 1000)
    return {
        "id": f"test-{timestamp}",
        "ts": timestamp,
        "from": "test",
        "to": f"impl:{task_id}" if msg_type == "send" else "pmai",
        "type": msg_type,
        "task_id": task_id,
        "data": data
    }


def test_send_functionality():
    """sendメッセージの動作テスト"""
    print("\n=== Test: Send Message (Parent → Child) ===")
    
    # 1. テスト用のメッセージを作成
    print("1. Creating test send message...")
    send_data = {"text": "Hello from parent!", "command": "echo 'Test message received'"}
    
    # 2. busctl sendコマンドを実行
    print("2. Sending message via busctl...")
    # JSONデータを適切にエスケープ
    json_str = json.dumps(send_data).replace('"', '\\"')
    cmd = (f'{ROOT}/bin/busctl send '
           f'--to impl:{TEST_TASK_ID} '
           f'--type instruct '
           f'--data "{json_str}"')
    
    result = run(cmd)
    
    if result.returncode == 0:
        print("✓ Send command executed successfully")
        
        # 3. メールボックスを確認
        print("3. Checking mailbox...")
        mailbox_dir = ROOT / "mbox" / f"impl-{TEST_TASK_ID}" / "in"
        
        # メールボックス内のファイルを確認
        if mailbox_dir.exists():
            messages = list(mailbox_dir.glob("*.json"))
            if messages:
                print(f"✓ Found {len(messages)} message(s) in mailbox")
                
                # 最新のメッセージを確認
                latest_msg = sorted(messages)[-1]
                with open(latest_msg) as f:
                    msg_content = json.load(f)
                    
                if msg_content.get("data") == send_data:
                    print("✓ Message content verified")
                    return True
                else:
                    print("✗ Message content mismatch")
                    print(f"Expected: {send_data}")
                    print(f"Got: {msg_content.get('data')}")
            else:
                print("✗ No messages found in mailbox")
        else:
            print(f"✗ Mailbox directory not found: {mailbox_dir}")
    else:
        print("✗ Send command failed")
    
    return False


def test_post_functionality():
    """postメッセージの動作テスト"""
    print("\n=== Test: Post Message (Child → Parent) ===")
    
    # 1. テスト用のpostメッセージを作成
    print("1. Creating test post messages...")
    
    # ログメッセージ
    log_data = {"msg": "Starting task execution", "level": "info"}
    cmd_log = (f"{ROOT}/bin/busctl post "
               f"--from impl:{TEST_TASK_ID} "
               f"--type log "
               f"--task {TEST_TASK_ID} "
               f"--data '{json.dumps(log_data)}'")
    
    # 結果メッセージ
    result_data = {"is_error": False, "summary": "Task completed successfully", "output": "test_output.txt"}
    cmd_result = (f"{ROOT}/bin/busctl post "
                  f"--from impl:{TEST_TASK_ID} "
                  f"--type result "
                  f"--task {TEST_TASK_ID} "
                  f"--data '{json.dumps(result_data)}'")
    
    # 2. ログメッセージを投函
    print("2. Posting log message...")
    result = run(cmd_log)
    
    if result.returncode == 0:
        print("✓ Log message posted")
    else:
        print("✗ Failed to post log message")
        return False
    
    # 3. 結果メッセージを投函
    print("3. Posting result message...")
    result = run(cmd_result)
    
    if result.returncode == 0:
        print("✓ Result message posted")
    else:
        print("✗ Failed to post result message")
        return False
    
    # 4. メールボックスを確認
    print("4. Checking parent mailbox...")
    mailbox_dir = ROOT / "mbox" / "pmai" / "in"
    
    if mailbox_dir.exists():
        messages = list(mailbox_dir.glob("*.json"))
        print(f"✓ Found {len(messages)} message(s) in parent mailbox")
        
        # メッセージの内容を検証
        log_found = False
        result_found = False
        
        for msg_file in messages:
            with open(msg_file) as f:
                msg = json.load(f)
                if msg.get("type") == "log" and msg.get("data") == log_data:
                    log_found = True
                    print("✓ Log message verified")
                elif msg.get("type") == "result" and msg.get("data") == result_data:
                    result_found = True
                    print("✓ Result message verified")
        
        return log_found and result_found
    else:
        print(f"✗ Parent mailbox not found: {mailbox_dir}")
    
    return False


def test_full_send_post_flow_with_busd():
    """busdを使った完全なsend/postフロー"""
    print("\n=== Test: Full Send/Post Flow with busd ===")
    
    # 環境変数設定
    os.environ['TMUX_SESSION'] = TEST_SESSION
    os.environ['ROOT'] = str(ROOT)
    
    # 0. クリーンアップ
    print("0. Cleaning up...")
    run(f"tmux kill-session -t {TEST_SESSION} 2>/dev/null")
    run("rm -f mbox/*/in/*.json 2>/dev/null")
    run("rm -f logs/bus.jsonl 2>/dev/null")
    
    # bus.jsonlファイルを作成
    (ROOT / "logs" / "bus.jsonl").touch()
    
    # 1. busdをバックグラウンドで起動
    print("1. Starting busd daemon...")
    busd_proc = subprocess.Popen(
        ['python3', str(ROOT / 'bin' / 'busd.py')],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(2)  # 起動待ち
    
    try:
        # 2. 子タスクをspawn
        print(f"2. Spawning task {TEST_TASK_ID}...")
        spawn_cmd = (f"{ROOT}/bin/busctl spawn "
                    f"--task {TEST_TASK_ID} "
                    f"--cwd work/{TEST_TASK_ID} "
                    f"--frame frames/impl/CLAUDE.md "
                    f"--goal 'Send/Post test task'")
        
        result = run(spawn_cmd)
        if result.returncode != 0:
            print("✗ Failed to spawn task")
            return False
        
        time.sleep(3)  # spawn処理待ち
        
        # 3. sendメッセージを送信
        print("3. Sending instruction to child...")
        send_data = {"text": "Please report your status", "action": "status_check"}
        send_cmd = (f"{ROOT}/bin/busctl send "
                   f"--to impl:{TEST_TASK_ID} "
                   f"--type instruct "
                   f"--data '{json.dumps(send_data)}'")
        
        result = run(send_cmd)
        if result.returncode == 0:
            print("✓ Send message delivered")
        
        time.sleep(2)  # 処理待ち
        
        # 4. postメッセージを送信（子からの応答をシミュレート）
        print("4. Simulating child response...")
        post_data = {"status": "active", "progress": 50, "message": "Processing..."}
        post_cmd = (f"{ROOT}/bin/busctl post "
                   f"--from impl:{TEST_TASK_ID} "
                   f"--type log "
                   f"--task {TEST_TASK_ID} "
                   f"--data '{json.dumps(post_data)}'")
        
        result = run(post_cmd)
        if result.returncode == 0:
            print("✓ Post message delivered")
        
        time.sleep(2)  # 処理待ち
        
        # 5. bus.jsonlを確認
        print("5. Checking bus.jsonl...")
        bus_log = ROOT / "logs" / "bus.jsonl"
        
        if bus_log.exists():
            with open(bus_log) as f:
                lines = f.readlines()
                print(f"✓ Found {len(lines)} entries in bus.jsonl")
                
                # 最後のエントリを確認
                if lines:
                    last_entry = json.loads(lines[-1])
                    if last_entry.get("type") == "log" and last_entry.get("task_id") == TEST_TASK_ID:
                        print("✓ Post message recorded in bus.jsonl")
                        print(f"  Message data: {last_entry.get('data')}")
                    else:
                        print("✗ Unexpected entry in bus.jsonl")
                else:
                    print("✗ No entries in bus.jsonl")
        else:
            print("✗ bus.jsonl not found")
        
        # 6. state/tasks.jsonを確認
        print("6. Checking tasks.json...")
        tasks_file = ROOT / "state" / "tasks.json"
        
        if tasks_file.exists():
            with open(tasks_file) as f:
                tasks = json.load(f)
                task_found = any(t["id"] == TEST_TASK_ID for t in tasks)
                
                if task_found:
                    print("✓ Task registered in tasks.json")
                    task_info = next(t for t in tasks if t["id"] == TEST_TASK_ID)
                    print(f"  Task status: {task_info.get('status')}")
                else:
                    print("✗ Task not found in tasks.json")
        else:
            print("✗ tasks.json not found")
        
        return True
        
    finally:
        # busd停止
        print("\n7. Stopping busd...")
        busd_proc.terminate()
        busd_proc.wait(timeout=5)
        
        # クリーンアップ
        run(f"tmux kill-session -t {TEST_SESSION} 2>/dev/null")


def main():
    """メインテスト実行"""
    print("=== Send/Post Integration Test ===")
    print(f"Project root: {ROOT}")
    
    # テスト実行
    all_passed = True
    
    # 1. Send機能テスト
    if not test_send_functionality():
        all_passed = False
    
    # 2. Post機能テスト  
    if not test_post_functionality():
        all_passed = False
    
    # 3. 完全なフローテスト
    if not test_full_send_post_flow_with_busd():
        all_passed = False
    
    print("\n=== Test Summary ===")
    if all_passed:
        print("✓ All tests PASSED")
    else:
        print("✗ Some tests FAILED")
    
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()