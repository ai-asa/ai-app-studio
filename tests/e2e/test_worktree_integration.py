#!/usr/bin/env python3
"""Integration test for worktree functionality"""

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

def run_cmd(cmd, cwd=None):
    """Run command and return result"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return result

def main():
    print("=== Worktree Integration Test ===")
    
    # Create temporary test repository
    test_dir = tempfile.mkdtemp()
    test_repo = Path(test_dir) / "test-repo"
    
    try:
        # Initialize test repository
        test_repo.mkdir(parents=True)
        run_cmd("git init", cwd=test_repo)
        run_cmd("git config user.name 'Test'", cwd=test_repo)
        run_cmd("git config user.email 'test@example.com'", cwd=test_repo)
        
        # Create initial commit
        (test_repo / "README.md").write_text("# Test Repository")
        run_cmd("git add .", cwd=test_repo)
        run_cmd("git commit -m 'Initial commit'", cwd=test_repo)
        
        # Set up environment
        os.environ['TARGET_REPO'] = str(test_repo)
        work_dir = test_repo / ".ai-app-studio"
        os.environ['ROOT'] = str(work_dir)
        work_dir.mkdir(parents=True)
        
        # Import and test ensure_worktree
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from bin.busd import ensure_worktree
        
        # Test 1: Create worktree
        print("\nTest 1: Creating worktree for task T001")
        ensure_worktree("T001", "work/T001", "feat/T001")
        
        # Verify branch was created
        result = run_cmd("git branch --list feat/T001", cwd=test_repo)
        if "feat/T001" in result.stdout:
            print("✓ Branch feat/T001 created in target repository")
        else:
            print("✗ Branch not created")
            print(f"Branches: {result.stdout}")
        
        # Verify worktree was created
        worktree_path = work_dir / "work" / "T001"
        if worktree_path.exists() and (worktree_path / ".git").exists():
            print("✓ Worktree created at .ai-app-studio/work/T001")
        else:
            print("✗ Worktree not created properly")
        
        # Verify worktree is listed
        result = run_cmd("git worktree list", cwd=test_repo)
        if str(worktree_path) in result.stdout:
            print("✓ Worktree is properly registered")
        else:
            print("✗ Worktree not registered")
            print(f"Worktree list: {result.stdout}")
        
        # Test 2: Create file in worktree
        print("\nTest 2: Working in worktree")
        test_file = worktree_path / "test.py"
        test_file.write_text("print('Hello from T001')")
        run_cmd("git add test.py", cwd=worktree_path)
        run_cmd("git commit -m 'Add test.py'", cwd=worktree_path)
        
        # Verify file is in branch
        result = run_cmd("git show feat/T001:test.py", cwd=test_repo)
        if "Hello from T001" in result.stdout:
            print("✓ File committed to feat/T001 branch")
        else:
            print("✗ File not found in branch")
        
        print("\n=== All tests completed ===")
        
    finally:
        # Cleanup
        if 'TARGET_REPO' in os.environ:
            del os.environ['TARGET_REPO']
        if 'ROOT' in os.environ:
            del os.environ['ROOT']
        shutil.rmtree(test_dir)

if __name__ == "__main__":
    main()