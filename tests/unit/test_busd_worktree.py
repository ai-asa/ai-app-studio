#!/usr/bin/env python3
"""Test for busd.py worktree functionality"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bin.busd import ensure_worktree


class TestBusdWorktree(unittest.TestCase):
    """Test cases for ensure_worktree function"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary directories
        self.test_dir = tempfile.mkdtemp()
        self.target_repo = Path(self.test_dir) / "target_repo"
        self.work_dir = Path(self.test_dir) / ".ai-app-studio"
        
        # Initialize git repo
        self.target_repo.mkdir(parents=True)
        subprocess.run(['git', 'init'], cwd=self.target_repo, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=self.target_repo, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=self.target_repo, capture_output=True)
        
        # Create initial commit on main branch
        (self.target_repo / "README.md").write_text("# Test Repo")
        subprocess.run(['git', 'add', '.'], cwd=self.target_repo, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=self.target_repo, capture_output=True)
        
        # Set up environment variables
        self.work_dir.mkdir(parents=True)
        os.environ['TARGET_REPO'] = str(self.target_repo)
        
        # Patch ROOT in busd module
        self.root_patch = patch('bin.busd.ROOT', self.work_dir)
        self.root_patch.start()
    
    def tearDown(self):
        """Clean up test environment"""
        self.root_patch.stop()
        if 'TARGET_REPO' in os.environ:
            del os.environ['TARGET_REPO']
        shutil.rmtree(self.test_dir)
    
    def test_ensure_worktree_creates_branch_in_target_repo(self):
        """Test that ensure_worktree creates branch in TARGET_REPO"""
        task_id = "T001"
        cwd = f"work/{task_id}"
        branch = f"feat/{task_id}"
        
        # Call ensure_worktree
        ensure_worktree(task_id, cwd, branch)
        
        # Check branch exists in target repo
        result = subprocess.run(
            ['git', 'branch', '--list', branch],
            cwd=self.target_repo,
            capture_output=True,
            text=True
        )
        self.assertIn(branch, result.stdout, "Branch should be created in TARGET_REPO")
    
    def test_ensure_worktree_creates_worktree_in_work_dir(self):
        """Test that worktree is created in .ai-app-studio/work/"""
        task_id = "T002"
        cwd = f"work/{task_id}"
        branch = f"feat/{task_id}"
        
        # Call ensure_worktree
        ensure_worktree(task_id, cwd, branch)
        
        # Check worktree exists
        worktree_path = self.work_dir / cwd
        self.assertTrue(worktree_path.exists(), "Worktree directory should exist")
        
        # Verify it's a git worktree
        git_file = worktree_path / ".git"
        self.assertTrue(git_file.exists(), ".git file should exist in worktree")
        
        # Check worktree is listed
        result = subprocess.run(
            ['git', 'worktree', 'list'],
            cwd=self.target_repo,
            capture_output=True,
            text=True
        )
        self.assertIn(str(worktree_path), result.stdout, "Worktree should be listed")
    
    def test_ensure_worktree_handles_existing_branch(self):
        """Test that ensure_worktree handles existing branch gracefully"""
        task_id = "T003"
        cwd = f"work/{task_id}"
        branch = f"feat/{task_id}"
        
        # Create branch manually
        subprocess.run(['git', 'branch', branch], cwd=self.target_repo, capture_output=True)
        
        # Call ensure_worktree - should not fail
        ensure_worktree(task_id, cwd, branch)
        
        # Check worktree exists
        worktree_path = self.work_dir / cwd
        self.assertTrue(worktree_path.exists(), "Worktree should be created even with existing branch")
    
    def test_ensure_worktree_handles_existing_directory(self):
        """Test that ensure_worktree handles existing directory"""
        task_id = "T004"
        cwd = f"work/{task_id}"
        branch = f"feat/{task_id}"
        
        # Create directory manually
        (self.work_dir / cwd).mkdir(parents=True)
        
        # Call ensure_worktree - should not fail
        ensure_worktree(task_id, cwd, branch)
        
        # Should return early without creating branch
        result = subprocess.run(
            ['git', 'branch', '--list', branch],
            cwd=self.target_repo,
            capture_output=True,
            text=True
        )
        self.assertNotIn(branch, result.stdout, "Branch should not be created if directory exists")
    
    def test_ensure_worktree_without_target_repo(self):
        """Test ensure_worktree when TARGET_REPO is not set"""
        del os.environ['TARGET_REPO']
        
        task_id = "T005"
        cwd = f"work/{task_id}"
        branch = f"feat/{task_id}"
        
        # Should create regular directory
        ensure_worktree(task_id, cwd, branch)
        
        # Check directory exists but not as worktree
        dir_path = self.work_dir / cwd
        self.assertTrue(dir_path.exists(), "Directory should be created")
        self.assertFalse((dir_path / ".git").exists(), "Should not be a git worktree")
    
    def test_ensure_worktree_checks_current_branch(self):
        """Test that worktree is created from correct base branch"""
        task_id = "T006"
        cwd = f"work/{task_id}"
        branch = f"feat/{task_id}"
        
        # Create and checkout develop branch
        subprocess.run(['git', 'branch', 'develop'], cwd=self.target_repo, capture_output=True)
        subprocess.run(['git', 'checkout', 'develop'], cwd=self.target_repo, capture_output=True)
        (self.target_repo / "develop.txt").write_text("develop branch")
        subprocess.run(['git', 'add', '.'], cwd=self.target_repo, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Develop commit'], cwd=self.target_repo, capture_output=True)
        
        # Call ensure_worktree
        ensure_worktree(task_id, cwd, branch)
        
        # Check that new branch is based on current branch (develop)
        worktree_path = self.work_dir / cwd
        develop_file = worktree_path / "develop.txt"
        self.assertTrue(develop_file.exists(), "Branch should be created from current branch")


if __name__ == '__main__':
    unittest.main()