#!/usr/bin/env python3
"""Test for busd.py with empty repository"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bin.busd import ensure_worktree


class TestBusdEmptyRepo(unittest.TestCase):
    """Test cases for ensure_worktree with empty repository"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary directories
        self.test_dir = tempfile.mkdtemp()
        self.target_repo = Path(self.test_dir) / "empty_repo"
        self.work_dir = Path(self.test_dir) / ".ai-app-studio"
        
        # Initialize empty git repo (no commits)
        self.target_repo.mkdir(parents=True)
        subprocess.run(['git', 'init'], cwd=self.target_repo, capture_output=True)
        
        # Set up environment
        self.work_dir.mkdir(parents=True)
        os.environ['TARGET_REPO'] = str(self.target_repo)
        
        # Patch ROOT in busd module
        import bin.busd
        self.original_root = bin.busd.ROOT
        bin.busd.ROOT = self.work_dir
    
    def tearDown(self):
        """Clean up test environment"""
        import bin.busd
        bin.busd.ROOT = self.original_root
        
        if 'TARGET_REPO' in os.environ:
            del os.environ['TARGET_REPO']
        shutil.rmtree(self.test_dir)
    
    def test_ensure_worktree_creates_initial_commit(self):
        """Test that ensure_worktree creates initial commit for empty repo"""
        task_id = "T001"
        cwd = f"work/{task_id}"
        branch = f"feat/{task_id}"
        
        # Call ensure_worktree
        ensure_worktree(task_id, cwd, branch)
        
        # Check that initial commit was created
        result = subprocess.run(
            ['git', 'log', '--oneline'],
            cwd=self.target_repo,
            capture_output=True,
            text=True
        )
        self.assertIn("Initial commit", result.stdout, "Initial commit should be created")
        
        # Check .gitignore was created
        gitignore_path = self.target_repo / ".gitignore"
        self.assertTrue(gitignore_path.exists(), ".gitignore should be created")
        self.assertIn(".ai-app-studio/", gitignore_path.read_text())
        
        # Check branch was created
        result = subprocess.run(
            ['git', 'branch', '--list', branch],
            cwd=self.target_repo,
            capture_output=True,
            text=True
        )
        self.assertIn(branch, result.stdout, "Branch should be created")
        
        # Check worktree was created
        worktree_path = self.work_dir / cwd
        self.assertTrue(worktree_path.exists(), "Worktree should be created")
    
    def test_ensure_worktree_with_no_git_config(self):
        """Test that ensure_worktree sets default git config if needed"""
        # Remove any existing git config
        subprocess.run(['git', 'config', '--unset', 'user.name'], 
                      cwd=self.target_repo, capture_output=True, check=False)
        subprocess.run(['git', 'config', '--unset', 'user.email'], 
                      cwd=self.target_repo, capture_output=True, check=False)
        
        task_id = "T002"
        cwd = f"work/{task_id}"
        branch = f"feat/{task_id}"
        
        # Call ensure_worktree
        ensure_worktree(task_id, cwd, branch)
        
        # Check git config was set
        result = subprocess.run(
            ['git', 'config', 'user.name'],
            cwd=self.target_repo,
            capture_output=True,
            text=True
        )
        self.assertEqual(result.stdout.strip(), "AI App Studio")
        
        result = subprocess.run(
            ['git', 'config', 'user.email'],
            cwd=self.target_repo,
            capture_output=True,
            text=True
        )
        self.assertEqual(result.stdout.strip(), "ai-app-studio@localhost")


if __name__ == '__main__':
    unittest.main()