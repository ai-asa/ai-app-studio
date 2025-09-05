#!/usr/bin/env bash
# busctl CLIの簡易テストスクリプト（jq不要版）

set -euo pipefail

# テスト用の環境設定
export TEST_ROOT=$(mktemp -d)
export ROOT="$TEST_ROOT"
trap 'rm -rf "$TEST_ROOT"' EXIT

# カラー出力
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# テスト結果カウンター
PASS=0
FAIL=0

# busctlのパス
BUSCTL="./bin/busctl"

# テスト関数
test_command() {
    local name="$1"
    local command="$2"
    local expected_exit="${3:-0}"
    
    echo -e "\n--- $name ---"
    
    set +e
    eval "$command" >/dev/null 2>&1
    local actual_exit=$?
    set -e
    
    if [[ $actual_exit -eq $expected_exit ]]; then
        echo -e "${GREEN}✓${NC} exit code: $actual_exit (expected)"
        ((PASS++))
        return 0
    else
        echo -e "${RED}✗${NC} exit code: $actual_exit (expected: $expected_exit)"
        ((FAIL++))
        return 1
    fi
}

test_file_exists() {
    local pattern="$1"
    local message="$2"
    
    if ls $pattern >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $message"
        ((PASS++))
        return 0
    else
        echo -e "${RED}✗${NC} $message"
        ((FAIL++))
        return 1
    fi
}

test_file_contains() {
    local pattern="$1"
    local search="$2"
    local message="$3"
    
    local file=$(ls $pattern 2>/dev/null | head -n 1)
    if [[ -z "$file" ]]; then
        echo -e "${RED}✗${NC} No file found: $pattern"
        ((FAIL++))
        return 1
    fi
    
    if grep -q "$search" "$file"; then
        echo -e "${GREEN}✓${NC} $message"
        ((PASS++))
        return 0
    else
        echo -e "${RED}✗${NC} $message"
        echo "  File: $file"
        echo "  Looking for: $search"
        ((FAIL++))
        return 1
    fi
}

echo "=== busctl Simple Tests ==="

# テスト1: busctl実行可能チェック
if [[ -x "$BUSCTL" ]]; then
    echo -e "${GREEN}✓${NC} busctl is executable"
    ((PASS++))
else
    echo -e "${RED}✗${NC} busctl is not executable"
    ((FAIL++))
    exit 1
fi

# テスト2: spawn コマンド
test_command "spawn with all parameters" \
    "$BUSCTL spawn --task T001 --cwd work/T001 --frame frames/impl/CLAUDE.md --goal 'Create hello.txt'" \
    0

test_file_exists "$ROOT/mbox/bus/in/*.json" "JSON file created in bus mailbox"
test_file_contains "$ROOT/mbox/bus/in/*.json" '"type": "spawn"' "File contains spawn type"
test_file_contains "$ROOT/mbox/bus/in/*.json" '"task_id": "T001"' "File contains task_id"
test_file_contains "$ROOT/mbox/bus/in/*.json" '"goal": "Create hello.txt"' "File contains goal"

# クリーンアップ
rm -rf "$ROOT/mbox/bus/in"/*

# テスト3: spawn without task (should fail)
test_command "spawn without task" \
    "$BUSCTL spawn --cwd work/T001" \
    1

# テスト4: send コマンド
test_command "send with all parameters" \
    "$BUSCTL send --to impl:T001 --type instruct --data '{\"text\":\"Start working\"}'" \
    0

test_file_exists "$ROOT/mbox/impl-T001/in/*.json" "JSON file created in impl-T001 mailbox"
test_file_contains "$ROOT/mbox/impl-T001/in/*.json" '"type": "instruct"' "File contains instruct type"
test_file_contains "$ROOT/mbox/impl-T001/in/*.json" '"to": "impl:T001"' "File contains to field"

# クリーンアップ
rm -rf "$ROOT/mbox/impl-T001"

# テスト5: post コマンド
test_command "post result" \
    "$BUSCTL post --from impl:T001 --type result --task T001 --data '{\"is_error\":false,\"summary\":\"done\"}'" \
    0

test_file_exists "$ROOT/mbox/pmai/in/*.json" "JSON file created in pmai mailbox"
test_file_contains "$ROOT/mbox/pmai/in/*.json" '"type": "result"' "File contains result type"
test_file_contains "$ROOT/mbox/pmai/in/*.json" '"task_id": "T001"' "File contains task_id"

# クリーンアップ
rm -rf "$ROOT/mbox/pmai/in"/*

# テスト6: post log
test_command "post log" \
    "$BUSCTL post --from impl:T001 --type log --task T001 --data '{\"msg\":\"Starting task\"}'" \
    0

test_file_exists "$ROOT/mbox/pmai/in/*.json" "JSON file created for log"

# テスト7: 無効なコマンド
test_command "invalid command" \
    "$BUSCTL invalid" \
    1

echo -e "\n=== Test Summary ==="
echo -e "Passed: ${GREEN}$PASS${NC}"
echo -e "Failed: ${RED}$FAIL${NC}"

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi

exit 0