#!/usr/bin/env python3
"""
E2E test for parallel worktree directory placement.
Tests the full flow with real tmux sessions and git worktrees.
"""

import unittest
import tempfile
import shutil
import subprocess
import json
import time
import os
from pathlib import Path
import sys

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestParallelWorktreeE2E(unittest.TestCase):
    """Test the full parallel worktree workflow end-to-end"""

    def setUp(self):
        """Set up test environment"""
        # Create a temporary workspace directory
        self.workspace = Path(tempfile.mkdtemp())
        
        # Create TARGET_REPO inside workspace
        self.target_repo = self.workspace / "test-project"
        self.target_repo.mkdir()
        
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=self.target_repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.target_repo, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.target_repo, check=True)
        
        # Create initial files
        (self.target_repo / "README.md").write_text("# Test Project\n")
        (self.target_repo / "requirements.yml").write_text("""project_name: Test Project
tasks:
  - id: T001
    name: Create hello.txt
    description: Create a hello.txt file
  - id: T002
    name: Create index.html
    description: Create an index.html file
""")
        
        # Initial commit
        subprocess.run(["git", "add", "."], cwd=self.target_repo, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=self.target_repo, check=True)
        
        # Set up environment variables
        self.old_env = os.environ.copy()
        os.environ["TARGET_REPO"] = str(self.target_repo)
        os.environ["ROOT"] = str(self.target_repo / ".ai-app-studio")
        os.environ["TMUX_SESSION"] = f"test-{os.getpid()}"
        
        # Create test tmux session with MAIN window
        self.tmux_session = os.environ["TMUX_SESSION"]
        subprocess.run(["tmux", "new-session", "-d", "-s", self.tmux_session, "-n", "MAIN"], check=True)
        
        # Create required directories
        mbox_dir = self.target_repo / ".ai-app-studio" / "mbox"
        mbox_dir.mkdir(parents=True, exist_ok=True)
        (mbox_dir / "bus" / "in").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        """Clean up test environment"""
        # Kill tmux session
        subprocess.run(["tmux", "kill-session", "-t", self.tmux_session], capture_output=True)
        
        # Clean up worktrees
        try:
            result = subprocess.run(
                ["git", "worktree", "list", "--porcelain"],
                cwd=self.target_repo,
                capture_output=True,
                text=True,
                check=True
            )
            for line in result.stdout.strip().split('\n'):
                if line.startswith("worktree ") and line != f"worktree {self.target_repo}":
                    worktree_path = line.split(" ", 1)[1]
                    subprocess.run(["git", "worktree", "remove", worktree_path], cwd=self.target_repo)
        except:
            pass
        
        # Restore environment
        os.environ.clear()
        os.environ.update(self.old_env)
        
        # Remove temporary directory
        shutil.rmtree(self.workspace, ignore_errors=True)

    def test_spawn_creates_parallel_worktree(self):
        """Test that spawn creates worktrees in parallel directories"""
        # Start busd in background
        busd_path = Path(__file__).parent.parent.parent / "bin" / "busd.py"
        busd_proc = subprocess.Popen(
            ["python3", str(busd_path)],
            env=os.environ,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        try:
            # Give busd time to start
            time.sleep(1)
            
            # Create spawn message
            spawn_msg = {
                "id": "test-001",
                "ts": int(time.time() * 1000),
                "from": "test",
                "to": "bus",
                "type": "spawn",
                "task_id": "T001",
                "data": {
                    "branch": "feat/T001",
                    "frame": "frames/impl/CLAUDE.md",
                    "goal": "Create hello.txt file"
                }
            }
            
            # Write spawn message to mailbox
            msg_file = self.target_repo / ".ai-app-studio" / "mbox" / "bus" / "in" / "test.json"
            msg_file.write_text(json.dumps(spawn_msg))
            
            # Give busd time to process
            time.sleep(2)
            
            # Check that parallel worktree was created
            expected_worktree = self.workspace / "test-project-T001"
            self.assertTrue(expected_worktree.exists(), f"Worktree not created at {expected_worktree}")
            
            # Verify it's a git worktree
            result = subprocess.run(
                ["git", "worktree", "list"],
                cwd=self.target_repo,
                capture_output=True,
                text=True,
                check=True
            )
            self.assertIn(str(expected_worktree), result.stdout)
            
            # Check that it's NOT under .ai-app-studio
            self.assertNotIn(".ai-app-studio", str(expected_worktree))
            
            # Verify tmux pane was created
            result = subprocess.run(
                ["tmux", "list-panes", "-t", self.tmux_session, "-F", "#{pane_current_path}"],
                capture_output=True,
                text=True,
                check=True
            )
            # At least one pane should be in the worktree directory
            pane_paths = result.stdout.strip().split('\n')
            worktree_found = any(str(expected_worktree) in path for path in pane_paths)
            self.assertTrue(worktree_found, f"No tmux pane found in worktree directory. Panes: {pane_paths}")
            
        finally:
            # Terminate busd
            busd_proc.terminate()
            
            # Get output for debugging
            try:
                stdout, stderr = busd_proc.communicate(timeout=5)
                if stdout:
                    print(f"BUSD stdout:\n{stdout.decode()}")
                if stderr:
                    print(f"BUSD stderr:\n{stderr.decode()}")
            except subprocess.TimeoutExpired:
                busd_proc.kill()
                stdout, stderr = busd_proc.communicate()
                if stdout:
                    print(f"BUSD stdout (after kill):\n{stdout.decode()}")
                if stderr:
                    print(f"BUSD stderr (after kill):\n{stderr.decode()}")

    def test_multiple_spawns_create_parallel_worktrees(self):
        """Test that multiple spawns create separate parallel worktrees"""
        # Start busd in background
        busd_path = Path(__file__).parent.parent.parent / "bin" / "busd.py"
        busd_proc = subprocess.Popen(
            ["python3", str(busd_path)],
            env=os.environ,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        try:
            # Give busd time to start
            time.sleep(1)
            
            # Create multiple spawn messages
            tasks = ["T001", "T002", "T003"]
            for task_id in tasks:
                spawn_msg = {
                    "id": f"test-{task_id}",
                    "ts": int(time.time() * 1000),
                    "from": "test",
                    "to": "bus",
                    "type": "spawn",
                    "task_id": task_id,
                    "data": {
                        "branch": f"feat/{task_id}",
                        "frame": "frames/impl/CLAUDE.md",
                        "goal": f"Task {task_id}"
                    }
                }
                
                # Write spawn message to mailbox
                msg_file = self.target_repo / ".ai-app-studio" / "mbox" / "bus" / "in" / f"test-{task_id}.json"
                msg_file.write_text(json.dumps(spawn_msg))
                
                # Small delay between spawns
                time.sleep(0.5)
            
            # Give busd time to process all  
            time.sleep(5)
            
            # Check if busd is still running
            if busd_proc.poll() is not None:
                stdout, stderr = busd_proc.communicate()
                print(f"\nBUSD terminated early with code {busd_proc.returncode}")
                if stderr:
                    print(f"BUSD stderr:\n{stderr.decode()}")
            
            # Check that all parallel worktrees were created
            for task_id in tasks:
                expected_worktree = self.workspace / f"test-project-{task_id}"
                
                # Debug: Check what was actually created
                if not expected_worktree.exists():
                    print(f"\nDEBUG: Expected worktree not found at {expected_worktree}")
                    print(f"DEBUG: Contents of workspace ({self.workspace}):")
                    for item in self.workspace.iterdir():
                        print(f"  - {item}")
                    
                    # Check git worktree list
                    result = subprocess.run(
                        ["git", "worktree", "list"],
                        cwd=self.target_repo,
                        capture_output=True,
                        text=True
                    )
                    print(f"DEBUG: Git worktree list:\n{result.stdout}")
                
                self.assertTrue(expected_worktree.exists(), f"Worktree not created at {expected_worktree}")
                
                # Verify each is a separate directory at the same level
                self.assertEqual(expected_worktree.parent, self.workspace)
            
            # Verify git knows about all worktrees
            result = subprocess.run(
                ["git", "worktree", "list"],
                cwd=self.target_repo,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Should have main + 3 worktrees = 4 total
            worktree_lines = [line for line in result.stdout.strip().split('\n') if line]
            self.assertGreaterEqual(len(worktree_lines), 4)
            
        finally:
            # Terminate busd
            busd_proc.terminate()
            
            # Get output for debugging
            try:
                stdout, stderr = busd_proc.communicate(timeout=5)
                if stdout:
                    print(f"BUSD stdout:\n{stdout.decode()}")
                if stderr:
                    print(f"BUSD stderr:\n{stderr.decode()}")
            except subprocess.TimeoutExpired:
                busd_proc.kill()
                stdout, stderr = busd_proc.communicate()
                if stdout:
                    print(f"BUSD stdout (after kill):\n{stdout.decode()}")
                if stderr:
                    print(f"BUSD stderr (after kill):\n{stderr.decode()}")


if __name__ == "__main__":
    unittest.main()