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

import bin.busd


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
        
        # Patch ROOT and TARGET_REPO in busd module
        self.original_root = bin.busd.ROOT
        self.original_target_repo = bin.busd.TARGET_REPO
        bin.busd.ROOT = self.work_dir
        bin.busd.TARGET_REPO = self.target_repo
    
    def tearDown(self):
        """Clean up test environment"""
        bin.busd.ROOT = self.original_root
        bin.busd.TARGET_REPO = self.original_target_repo
        
        if 'TARGET_REPO' in os.environ:
            del os.environ['TARGET_REPO']
        shutil.rmtree(self.test_dir)
    
    def test_ensure_worktree_creates_initial_commit(self):
        """Test that ensure_worktree creates initial commit for empty repo"""
        task_id = "T001"
        branch = f"feat/{task_id}"
        
        # Call ensure_worktree
        worktree_path = bin.busd.ensure_worktree(task_id, branch)
        
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
        
        # Check worktree was created at the correct parallel location
        expected_path = bin.busd.get_worktree_path(task_id)
        self.assertEqual(worktree_path, expected_path)
        self.assertEqual(worktree_path, self.target_repo.parent / f"{self.target_repo.name}-{task_id}")
        self.assertTrue(worktree_path.exists(), "Worktree should be created")
    
    def test_ensure_worktree_with_no_git_config(self):
        """Test that ensure_worktree sets default git config if needed"""
        # Remove any existing git config
        subprocess.run(['git', 'config', '--unset', 'user.name'], 
                      cwd=self.target_repo, capture_output=True, check=False)
        subprocess.run(['git', 'config', '--unset', 'user.email'], 
                      cwd=self.target_repo, capture_output=True, check=False)
        
        task_id = "T002"
        branch = f"feat/{task_id}"
        
        # Call ensure_worktree
        worktree_path = bin.busd.ensure_worktree(task_id, branch)
        
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