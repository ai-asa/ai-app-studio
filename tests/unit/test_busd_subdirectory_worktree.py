#!/usr/bin/env python3
"""
Test for subdirectory worktree placement.
Tests that worktrees are created inside the TARGET_REPO directory
instead of in parallel directories.
"""

import unittest
import tempfile
import shutil
import subprocess
import json
from pathlib import Path
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bin.busd import ensure_worktree, get_worktree_path


class TestSubdirectoryWorktree(unittest.TestCase):
    """Test subdirectory worktree placement"""

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
        self.old_target_repo = os.environ.get("TARGET_REPO")
        os.environ["TARGET_REPO"] = str(self.target_repo)

    def tearDown(self):
        """Clean up test environment"""
        # Restore original TARGET_REPO
        if self.old_target_repo:
            os.environ["TARGET_REPO"] = self.old_target_repo
        else:
            os.environ.pop("TARGET_REPO", None)
            
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
            
        # Remove temporary directory
        shutil.rmtree(self.workspace, ignore_errors=True)

    def test_get_worktree_path_returns_subdirectory(self):
        """Test that get_worktree_path returns a path inside TARGET_REPO"""
        task_id = "T001"
        
        # This function should return a subdirectory path
        worktree_path = get_worktree_path(task_id)
        
        # Expected path: target_repo/T001
        expected_path = self.target_repo / task_id
        self.assertEqual(worktree_path, expected_path)
        
        # Ensure it's inside TARGET_REPO
        self.assertEqual(worktree_path.parent, self.target_repo)
        
        # Ensure it's NOT in the parent directory
        self.assertNotEqual(worktree_path.parent, self.workspace)

    def test_ensure_worktree_creates_subdirectory(self):
        """Test that ensure_worktree creates worktree as subdirectory"""
        task_id = "T002"
        branch = f"feat/{task_id}"
        
        # Call ensure_worktree with the new logic
        worktree_path = ensure_worktree(task_id, branch)
        
        # Check that worktree was created as subdirectory
        expected_path = self.target_repo / task_id
        self.assertEqual(worktree_path, expected_path)
        self.assertTrue(worktree_path.exists())
        
        # Verify it's inside TARGET_REPO
        self.assertTrue(str(worktree_path).startswith(str(self.target_repo)))
        
        # Verify it's a valid git worktree
        result = subprocess.run(
            ["git", "worktree", "list"],
            cwd=self.target_repo,
            capture_output=True,
            text=True,
            check=True
        )
        self.assertIn(str(worktree_path), result.stdout)

    def test_multiple_worktrees_as_subdirectories(self):
        """Test creating multiple worktrees as subdirectories"""
        tasks = ["T003", "T004", "T005"]
        created_paths = []
        
        for task_id in tasks:
            branch = f"feat/{task_id}"
            worktree_path = ensure_worktree(task_id, branch)
            created_paths.append(worktree_path)
            
            # Each should be a subdirectory of TARGET_REPO
            expected_path = self.target_repo / task_id
            self.assertEqual(worktree_path, expected_path)
            self.assertTrue(worktree_path.exists())
        
        # All should have TARGET_REPO as parent
        parents = [p.parent for p in created_paths]
        self.assertTrue(all(p == self.target_repo for p in parents))

    def test_worktree_with_prefix_to_avoid_conflicts(self):
        """Test worktree creation with prefix to avoid name conflicts"""
        # Create a regular directory that might conflict
        conflict_dir = self.target_repo / "src"
        conflict_dir.mkdir()
        
        # If we want to use a prefix like 'task-' or 'worktree-'
        task_id = "T006"
        worktree_path = get_worktree_path(task_id)
        
        # Should not conflict with existing directories
        self.assertNotEqual(worktree_path, conflict_dir)
        
        # Create the worktree
        branch = f"feat/{task_id}"
        actual_path = ensure_worktree(task_id, branch)
        self.assertTrue(actual_path.exists())

    def test_worktree_not_ignored_by_gitignore(self):
        """Test that worktrees can be committed even with .gitignore"""
        # Create .gitignore that might affect worktrees
        gitignore_content = """# Common ignores
*.pyc
__pycache__/
.DS_Store

# AI App Studio
.ai-app-studio/
"""
        (self.target_repo / ".gitignore").write_text(gitignore_content)
        subprocess.run(["git", "add", ".gitignore"], cwd=self.target_repo, check=True)
        subprocess.run(["git", "commit", "-m", "Add .gitignore"], cwd=self.target_repo, check=True)
        
        # Create worktree
        task_id = "T007"
        branch = f"feat/{task_id}"
        worktree_path = ensure_worktree(task_id, branch)
        
        # Create a file in the worktree
        test_file = worktree_path / "feature.py"
        test_file.write_text("def feature():\n    pass\n")
        
        # The file should be trackable
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=True
        )
        self.assertIn("feature.py", result.stdout)


if __name__ == "__main__":
    unittest.main()