#!/usr/bin/env python3
"""
フレーム（CLAUDE.md）の動作確認テスト
"""

import os
import tempfile
import shutil
from pathlib import Path

def test_parent_frame():
    """親フレーム（pmai）のテスト"""
    print("=== Parent Frame (PMAI) Test ===")
    
    # フレームファイルの存在確認
    parent_frame = Path("frames/pmai/CLAUDE.md")
    if parent_frame.exists():
        print(f"✓ Parent frame exists: {parent_frame}")
        
        # 内容確認
        content = parent_frame.read_text()
        
        # 必須要素のチェック
        checks = [
            ("busctl spawn", "spawn command usage"),
            ("requirements.yml", "requirements file reading"),
            ("Bash", "Bash tool usage"),
            ("task", "task processing")
        ]
        
        for keyword, desc in checks:
            if keyword in content:
                print(f"✓ Contains {desc}")
            else:
                print(f"✗ Missing {desc}")
                
    else:
        print(f"✗ Parent frame not found at {parent_frame}")
        print("  This is expected in TDD Red phase")


def test_child_frame():
    """子フレーム（impl）のテスト"""
    print("\n=== Child Frame (Impl) Test ===")
    
    # フレームファイルの存在確認
    child_frame = Path("frames/impl/CLAUDE.md")
    if child_frame.exists():
        print(f"✓ Child frame exists: {child_frame}")
        
        # 内容確認
        content = child_frame.read_text()
        
        # 必須要素のチェック
        checks = [
            ("busctl post", "post command usage"),
            ("--type log", "progress reporting"),
            ("--type result", "result reporting"),
            ("is_error", "error handling"),
            ("TASK_GOAL", "task goal reference")
        ]
        
        for keyword, desc in checks:
            if keyword in content:
                print(f"✓ Contains {desc}")
            else:
                print(f"✗ Missing {desc}")
                
    else:
        print(f"✗ Child frame not found at {child_frame}")
        print("  This is expected in TDD Red phase")


def test_sample_requirements():
    """サンプルrequirements.ymlのテスト"""
    print("\n=== Sample Requirements Test ===")
    
    req_file = Path("requirements.yml")
    if req_file.exists():
        print(f"✓ Requirements file exists: {req_file}")
        
        # YAML形式の基本チェック
        content = req_file.read_text()
        if "tasks:" in content:
            print("✓ Contains tasks section")
        else:
            print("✗ Missing tasks section")
            
    else:
        print(f"✗ Requirements file not found at {req_file}")
        print("  This is expected before implementation")


def test_frame_structure():
    """フレームの構造テスト"""
    print("\n=== Frame Structure Test ===")
    
    # 親フレームの構造要素
    parent_elements = [
        "# AI Agent - Parent (PMAI)",
        "## 役割",
        "## 手順",
        "## 通信契約",
        "## 制約"
    ]
    
    # 子フレームの構造要素
    child_elements = [
        "# AI Agent - Implementation Worker",
        "## 役割",
        "## 手順", 
        "## 通信契約",
        "## 作業ルール"
    ]
    
    # ここでは構造のみチェック（実装前なので存在しないはず）
    print("Expected structure for parent frame:")
    for elem in parent_elements:
        print(f"  - {elem}")
        
    print("\nExpected structure for child frame:")
    for elem in child_elements:
        print(f"  - {elem}")


if __name__ == '__main__':
    print("=== Frame (CLAUDE.md) Tests ===\n")
    
    test_parent_frame()
    test_child_frame()
    test_sample_requirements()
    test_frame_structure()
    
    print("\n✓ Frame structure tests completed")
    print("Note: All tests should fail in TDD Red phase")