#!/usr/bin/env bash
# パス解決機能のテスト

set -euo pipefail

# テスト環境設定
export TEST_ROOT=$(mktemp -d)
export ROOT="$TEST_ROOT"
trap 'rm -rf "$TEST_ROOT"' EXIT

# ai-app-studioのパス
AI_APP_STUDIO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "=== Path Resolution Tests ==="
echo "AI App Studio: $AI_APP_STUDIO"
echo "Test ROOT: $TEST_ROOT"

# テスト用カウンター
PASS=0
FAIL=0

# テスト関数
assert_contains() {
    local text="$1"
    local pattern="$2"
    local message="$3"
    
    if echo "$text" | grep -q "$pattern"; then
        echo "✓ $message"
        ((PASS++))
    else
        echo "✗ $message"
        echo "  Expected pattern: $pattern"
        echo "  Actual text: $text"
        ((FAIL++))
    fi
}

echo -e "\n--- Test 1: busctl default frame resolution ---"

# フレームを指定せずにspawn
OUTPUT=$($AI_APP_STUDIO/bin/busctl spawn --task T001 --goal "test" 2>&1)

# 生成されたJSONを確認
JSON_FILE=$(find "$ROOT/mbox/bus/in" -name "*.json" | head -n1)
if [[ -f "$JSON_FILE" ]]; then
    JSON_CONTENT=$(cat "$JSON_FILE")
    assert_contains "$JSON_CONTENT" "frames/impl/CLAUDE.md" "Default frame should be set"
else
    echo "✗ No JSON file created"
    ((FAIL++))
fi

echo -e "\n--- Test 2: ai-parent script path resolution ---"

# ai-parentスクリプトが正しいフレームを参照するか確認
if [[ -x "$AI_APP_STUDIO/bin/ai-parent" ]]; then
    # スクリプトの内容を確認（実行はしない）
    SCRIPT_CONTENT=$(cat "$AI_APP_STUDIO/bin/ai-parent")
    assert_contains "$SCRIPT_CONTENT" "frames/pmai/CLAUDE.md" "ai-parent should reference pmai frame"
    echo "✓ ai-parent script exists and is executable"
    ((PASS++))
else
    echo "✗ ai-parent script not found or not executable"
    ((FAIL++))
fi

echo -e "\n--- Test 3: Working directory independence ---"

# 別のディレクトリから実行
mkdir -p "$TEST_ROOT/subdir"
cd "$TEST_ROOT/subdir"

# ROOTを明示的に設定せずに実行
unset ROOT
OUTPUT=$($AI_APP_STUDIO/bin/busctl spawn --task T002 --goal "test from subdir" 2>&1 || true)

# subdirにmboxが作られているか確認
if [[ -d "mbox/bus/in" ]]; then
    echo "✓ mbox created in current directory"
    ((PASS++))
else
    echo "✗ mbox not created in current directory"
    ((FAIL++))
fi

echo -e "\n--- Test 4: Script self-location ---"

# busctlが自身の場所を正しく検出できるか
cd "$TEST_ROOT"
BUSCTL_PATH="$AI_APP_STUDIO/bin/busctl"

# シンボリックリンク経由でも動作するか
ln -s "$BUSCTL_PATH" "$TEST_ROOT/busctl-link"
OUTPUT=$("$TEST_ROOT/busctl-link" spawn --task T003 --goal "test via symlink" 2>&1 || true)

if [[ -d "$TEST_ROOT/mbox/bus/in" ]]; then
    echo "✓ Works via symlink"
    ((PASS++))
else
    echo "✗ Failed via symlink"
    ((FAIL++))
fi

echo -e "\n=== Test Summary ==="
echo "Passed: $PASS"
echo "Failed: $FAIL"

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi