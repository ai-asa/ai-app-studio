#!/usr/bin/env python3
"""Unit tests for busctl.py"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestBusctl(unittest.TestCase):
    """Test cases for busctl command line tool"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.mbox_dir = Path(self.test_dir) / "mbox"
        self.mbox_dir.mkdir(parents=True)
        
        # Create mailbox directories
        (self.mbox_dir / "bus" / "in").mkdir(parents=True)
        (self.mbox_dir / "pmai" / "in").mkdir(parents=True)
        
        # Set environment variable
        os.environ['BUSCTL_ROOT'] = self.test_dir
        
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.test_dir)
        if 'BUSCTL_ROOT' in os.environ:
            del os.environ['BUSCTL_ROOT']
    
    def test_spawn_command_basic(self):
        """Test spawn command with basic parameters"""
        # Run busctl spawn command
        cmd = [
            sys.executable, "bin/busctl.py", "spawn",
            "--task", "T001",
            "--cwd", "work/T001",
            "--frame", "frames/impl/CLAUDE.md",
            "--goal", "Create hello.txt"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        
        # Check if message was written to mailbox
        files = list((self.mbox_dir / "bus" / "in").glob("*.json"))
        self.assertEqual(len(files), 1)
        
        # Verify message content
        with open(files[0], 'r') as f:
            msg = json.load(f)
        
        self.assertEqual(msg['from'], 'pmai')
        self.assertEqual(msg['to'], 'bus')
        self.assertEqual(msg['type'], 'spawn')
        self.assertEqual(msg['task_id'], 'T001')
        self.assertEqual(msg['data']['cwd'], 'work/T001')
        self.assertEqual(msg['data']['frame'], 'frames/impl/CLAUDE.md')
        self.assertEqual(msg['data']['goal'], 'Create hello.txt')
        self.assertEqual(msg['data']['branch'], 'feat/T001')  # default
    
    def test_spawn_command_with_branch(self):
        """Test spawn command with custom branch"""
        cmd = [
            sys.executable, "bin/busctl.py", "spawn",
            "--task", "T002",
            "--cwd", "work/T002",
            "--frame", "frames/impl/CLAUDE.md",
            "--goal", "Create index.html",
            "--branch", "feature/custom-branch"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        
        files = list((self.mbox_dir / "bus" / "in").glob("*.json"))
        with open(files[0], 'r') as f:
            msg = json.load(f)
        
        self.assertEqual(msg['data']['branch'], 'feature/custom-branch')
    
    def test_send_command(self):
        """Test send command"""
        # Create destination mailbox
        (self.mbox_dir / "impl-T001" / "in").mkdir(parents=True)
        
        cmd = [
            sys.executable, "bin/busctl.py", "send",
            "--to", "impl:T001",
            "--type", "instruct",
            "--data", '{"text": "Read ./task.json"}'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        
        # Check message in impl-T001 mailbox
        files = list((self.mbox_dir / "impl-T001" / "in").glob("*.json"))
        self.assertEqual(len(files), 1)
        
        with open(files[0], 'r') as f:
            msg = json.load(f)
        
        self.assertEqual(msg['from'], 'pmai')
        self.assertEqual(msg['to'], 'impl:T001')
        self.assertEqual(msg['type'], 'instruct')
        self.assertEqual(msg['data']['text'], 'Read ./task.json')
    
    def test_post_command_with_special_characters(self):
        """Test post command with special characters in JSON"""
        # Test with various special characters
        special_messages = [
            'Hello "World"',  # Double quotes
            "Hello 'World'",  # Single quotes
            'Line 1\nLine 2',  # Newline
            'Tab\tSeparated',  # Tab
            'Back\\slash',     # Backslash
            'Unicode: 你好世界 🌍',  # Unicode
            '{"nested": {"json": "value"}}',  # Nested JSON
        ]
        
        for i, msg_text in enumerate(special_messages):
            # Clean previous files
            for f in (self.mbox_dir / "pmai" / "in").glob("*.json"):
                f.unlink()
            
            data = {"msg": msg_text, "index": i}
            cmd = [
                sys.executable, "bin/busctl.py", "post",
                "--from", "impl:T001",
                "--type", "log",
                "--task", "T001",
                "--data", json.dumps(data)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, 
                           f"Failed for message: {msg_text}\nStderr: {result.stderr}")
            
            # Verify message was written correctly
            files = list((self.mbox_dir / "pmai" / "in").glob("*.json"))
            self.assertEqual(len(files), 1)
            
            with open(files[0], 'r') as f:
                msg = json.load(f)
            
            self.assertEqual(msg['data']['msg'], msg_text)
            self.assertEqual(msg['data']['index'], i)
    
    def test_post_result_with_is_error(self):
        """Test post command with result type requires is_error"""
        cmd = [
            sys.executable, "bin/busctl.py", "post",
            "--from", "impl:T001",
            "--type", "result",
            "--task", "T001",
            "--data", '{"is_error": false, "summary": "Task completed"}'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        
        files = list((self.mbox_dir / "pmai" / "in").glob("*.json"))
        with open(files[0], 'r') as f:
            msg = json.load(f)
        
        self.assertEqual(msg['type'], 'result')
        self.assertFalse(msg['data']['is_error'])
        self.assertEqual(msg['data']['summary'], 'Task completed')
    
    def test_post_result_without_is_error_fails(self):
        """Test post command with result type fails without is_error"""
        cmd = [
            sys.executable, "bin/busctl.py", "post",
            "--from", "impl:T001",
            "--type", "result", 
            "--task", "T001",
            "--data", '{"summary": "Missing is_error"}'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("is_error", result.stderr)
    
    def test_missing_required_arguments(self):
        """Test commands fail with missing required arguments"""
        # spawn without --task
        cmd = [sys.executable, "bin/busctl.py", "spawn", "--cwd", "work/T001"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        
        # send without --to
        cmd = [sys.executable, "bin/busctl.py", "send", "--type", "instruct"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        
        # post without --from
        cmd = [sys.executable, "bin/busctl.py", "post", "--type", "log"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
    
    def test_atomic_write(self):
        """Test that writes are atomic (no partial files)"""
        import threading
        import time
        
        def write_many_messages():
            for i in range(10):
                cmd = [
                    sys.executable, "bin/busctl.py", "post",
                    "--from", f"impl:T{i:03d}",
                    "--type", "log",
                    "--task", f"T{i:03d}",
                    "--data", json.dumps({"msg": f"Message {i}"})
                ]
                subprocess.run(cmd, capture_output=True)
        
        # Run multiple threads writing concurrently
        threads = []
        for _ in range(3):
            t = threading.Thread(target=write_many_messages)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # All files should be valid JSON
        files = list((self.mbox_dir / "pmai" / "in").glob("*.json"))
        self.assertGreater(len(files), 0)
        
        for f in files:
            with open(f, 'r') as fp:
                try:
                    json.load(fp)
                except json.JSONDecodeError:
                    self.fail(f"File {f} contains invalid JSON")
    
    def test_complex_json_data(self):
        """Test handling of complex nested JSON data"""
        complex_data = {
            "arrays": [1, 2, 3, ["nested", "array"]],
            "objects": {
                "nested": {
                    "deeply": {
                        "value": "found"
                    }
                }
            },
            "mixed": [
                {"id": 1, "name": "Item 1"},
                {"id": 2, "name": "Item 2", "tags": ["a", "b", "c"]}
            ],
            "special_chars": "Line1\nLine2\tTabbed\"Quoted'Single",
            "unicode": "émojis 😀🎉 and 中文字符"
        }
        
        cmd = [
            sys.executable, "bin/busctl.py", "post",
            "--from", "impl:T001",
            "--type", "log",
            "--task", "T001",
            "--data", json.dumps(complex_data)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        
        files = list((self.mbox_dir / "pmai" / "in").glob("*.json"))
        with open(files[0], 'r') as f:
            msg = json.load(f)
        
        # Verify complex data is preserved exactly
        self.assertEqual(msg['data'], complex_data)


if __name__ == '__main__':
    unittest.main()