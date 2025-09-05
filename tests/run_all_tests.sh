#!/bin/bash
#
# すべてのテストを実行するビルドテストスクリプト
#

set -e  # エラーがあれば即座に停止

echo "=== AI App Studio Build Test ==="
echo "Date: $(date)"
echo "================================"

# 1. Python構文チェック
echo -e "\n[1/5] Python Syntax Check"
echo "------------------------"
for py_file in $(find . -name "*.py" -type f | grep -v __pycache__); do
    echo -n "Checking $py_file ... "
    if python3 -m py_compile "$py_file" 2>/dev/null; then
        echo "OK"
    else
        echo "FAILED"
        python3 -m py_compile "$py_file"
        exit 1
    fi
done

# 2. Bash構文チェック
echo -e "\n[2/5] Bash Syntax Check"
echo "---------------------"
for sh_file in bin/busctl tests/*.sh; do
    if [ -f "$sh_file" ]; then
        echo -n "Checking $sh_file ... "
        if bash -n "$sh_file" 2>/dev/null; then
            echo "OK"
        else
            echo "FAILED"
            bash -n "$sh_file"
            exit 1
        fi
    fi
done

# 3. 基本的なテスト実行
echo -e "\n[3/5] Basic Unit Tests"
echo "--------------------"
echo "Running tmux layout tests..."
python3 tests/bin/test_tmux_layout_simple.py | tail -20

# 4. 統合テスト
echo -e "\n[4/5] Integration Tests"
echo "---------------------"
echo "Running send/post flow tests..."
python3 tests/e2e/test_send_post_flow.py | grep -E "(Test Summary|PASS|FAIL)"

# 5. ファイル構造チェック
echo -e "\n[5/5] Project Structure Check"
echo "---------------------------"
required_dirs="bin frames mbox logs state work tests"
for dir in $required_dirs; do
    if [ -d "$dir" ]; then
        echo "✓ Directory exists: $dir"
    else
        echo "✗ Missing directory: $dir"
        mkdir -p "$dir"
        echo "  → Created $dir"
    fi
done

# 必須ファイルのチェック
required_files=(
    "bin/busd.py"
    "bin/busctl"
    "frames/pmai/CLAUDE.md"
    "frames/impl/CLAUDE.md"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ File exists: $file"
    else
        echo "✗ Missing file: $file"
    fi
done

echo -e "\n================================"
echo "Build Test Complete!"
echo "================================"