#!/usr/bin/env python3
"""
Simple test for subdirectory worktree functionality without tmux complexities.
"""

import unittest
import tempfile
import shutil
import subprocess
import os
from pathlib import Path
import sys

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bin.busd import ensure_worktree, get_worktree_path


class TestSubdirectoryWorktreeSimple(unittest.TestCase):
    """Simple test for subdirectory worktree functionality"""

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
        
        # Create initial commit
        (self.target_repo / "README.md").write_text("# Test Project\n")
        subprocess.run(["git", "add", "."], cwd=self.target_repo, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=self.target_repo, check=True)
        
        # Set TARGET_REPO environment variable
        self.old_env = os.environ.copy()
        os.environ["TARGET_REPO"] = str(self.target_repo)

    def tearDown(self):
        """Clean up test environment"""
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

    def test_multiple_worktrees_created_successfully(self):
        """Test that multiple worktrees can be created as subdirectories"""
        tasks = ["T001", "T002", "T003", "T004", "T005"]
        created_worktrees = []
        
        for task_id in tasks:
            branch = f"feat/{task_id}"
            worktree_path = ensure_worktree(task_id, branch)
            created_worktrees.append(worktree_path)
            
            # Verify worktree was created at expected location
            expected_path = self.target_repo / task_id
            self.assertEqual(worktree_path, expected_path)
            self.assertTrue(worktree_path.exists())
            
            # Verify it's inside target_repo
            self.assertTrue(str(worktree_path).startswith(str(self.target_repo)))
            
            # Verify we can write to the worktree
            test_file = worktree_path / f"test-{task_id}.txt"
            test_file.write_text(f"Test content for {task_id}")
            self.assertTrue(test_file.exists())
        
        # Verify all worktrees are subdirectories of target_repo
        parents = set(path.parent for path in created_worktrees)
        self.assertEqual(len(parents), 1)
        self.assertEqual(parents.pop(), self.target_repo)
        
        # Verify git knows about all worktrees
        result = subprocess.run(
            ["git", "worktree", "list"],
            cwd=self.target_repo,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Should have main + 5 worktrees = 6 total
        worktree_lines = [line for line in result.stdout.strip().split('\n') if line]
        self.assertEqual(len(worktree_lines), 6)
        
        # Check that each worktree is on the correct branch
        for task_id in tasks:
            expected_branch = f"feat/{task_id}"
            self.assertIn(expected_branch, result.stdout)

    def test_worktree_files_not_gitignored(self):
        """Test that files in subdirectory worktrees can be committed"""
        task_id = "T001"
        branch = f"feat/{task_id}"
        
        # Create worktree
        worktree_path = ensure_worktree(task_id, branch)
        
        # Create a test file
        test_file = worktree_path / "feature.py"
        test_file.write_text("def hello():\n    return 'Hello from parallel worktree'\n")
        
        # Git operations in the worktree
        subprocess.run(["git", "add", "."], cwd=worktree_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add feature.py"],
            cwd=worktree_path,
            check=True
        )
        
        # Verify the commit was created
        result = subprocess.run(
            ["git", "log", "--oneline", "-n", "1"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=True
        )
        self.assertIn("Add feature.py", result.stdout)
        
        # Verify the file is tracked
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=True
        )
        self.assertIn("feature.py", result.stdout)


if __name__ == "__main__":
    unittest.main()