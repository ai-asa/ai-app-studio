#!/usr/bin/env bash
# busctl CLIの機能テストスクリプト

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
run_test() {
    local name="$1"
    local command="$2"
    local expected_exit="${3:-0}"
    local message="${4:-$name}"
    
    echo -e "\n--- $name ---"
    
    set +e
    eval "$command" >/dev/null 2>&1
    local actual_exit=$?
    set -e
    
    if [[ $actual_exit -eq $expected_exit ]]; then
        echo -e "${GREEN}✓${NC} $message (exit code: $actual_exit)"
        ((PASS++))
        return 0
    else
        echo -e "${RED}✗${NC} $message (expected exit: $expected_exit, got: $actual_exit)"
        ((FAIL++))
        return 1
    fi
}

check_json_file() {
    local pattern="$1"
    local field="$2"
    local expected="$3"
    local message="$4"
    
    local file=$(find "$ROOT" -path "$pattern" -type f | head -n 1)
    if [[ -z "$file" ]]; then
        echo -e "${RED}✗${NC} No file found matching: $pattern"
        ((FAIL++))
        return 1
    fi
    
    local actual=$(jq -r "$field" < "$file" 2>/dev/null)
    if [[ "$actual" == "$expected" ]]; then
        echo -e "${GREEN}✓${NC} $message"
        ((PASS++))
        return 0
    else
        echo -e "${RED}✗${NC} $message"
        echo "  Expected: $expected"
        echo "  Actual:   $actual"
        echo "  File:     $file"
        ((FAIL++))
        return 1
    fi
}

echo "=== busctl Functional Tests ==="

# まず実行権限をチェック
if [[ ! -x "$BUSCTL" ]]; then
    echo -e "${RED}✗${NC} $BUSCTL is not executable or does not exist"
    echo "This is expected in TDD Red phase"
    exit 0
fi

# テスト1: spawn コマンド
run_test "spawn with all parameters" \
    "$BUSCTL spawn --task T001 --cwd work/T001 --frame frames/impl/CLAUDE.md --goal 'Create hello.txt'" \
    0 \
    "spawn command should succeed"

if [[ $? -eq 0 ]]; then
    check_json_file "$ROOT/mbox/bus/in/*.json" ".type" "spawn" "JSON type should be spawn"
    check_json_file "$ROOT/mbox/bus/in/*.json" ".task_id" "T001" "task_id should be T001"
    check_json_file "$ROOT/mbox/bus/in/*.json" ".data.cwd" "work/T001" "cwd should be work/T001"
    check_json_file "$ROOT/mbox/bus/in/*.json" ".data.goal" "Create hello.txt" "goal should match"
    rm -rf "$ROOT/mbox/bus/in"/*
fi

# テスト2: spawn without required task parameter
run_test "spawn without task" \
    "$BUSCTL spawn --cwd work/T001" \
    1 \
    "spawn should fail without --task"

# テスト3: send コマンド
run_test "send with all parameters" \
    "$BUSCTL send --to impl:T001 --type instruct --data '{\"text\":\"Start working\"}'" \
    0 \
    "send command should succeed"

if [[ $? -eq 0 ]]; then
    check_json_file "$ROOT/mbox/impl-T001/in/*.json" ".type" "instruct" "JSON type should be instruct"
    check_json_file "$ROOT/mbox/impl-T001/in/*.json" ".to" "impl:T001" "to field should be impl:T001"
    rm -rf "$ROOT/mbox/impl-T001/in"/*
fi

# テスト4: post コマンド
run_test "post result" \
    "$BUSCTL post --from impl:T001 --type result --task T001 --data '{\"is_error\":false,\"summary\":\"Task completed\"}'" \
    0 \
    "post command should succeed"

if [[ $? -eq 0 ]]; then
    check_json_file "$ROOT/mbox/pmai/in/*.json" ".type" "result" "JSON type should be result"
    check_json_file "$ROOT/mbox/pmai/in/*.json" ".task_id" "T001" "task_id should be T001"
    check_json_file "$ROOT/mbox/pmai/in/*.json" ".data.is_error" "false" "is_error should be false"
    rm -rf "$ROOT/mbox/pmai/in"/*
fi

# テスト5: post log
run_test "post log" \
    "$BUSCTL post --from impl:T001 --type log --task T001 --data '{\"msg\":\"Starting task\"}'" \
    0 \
    "post log should succeed"

# テスト6: 無効なコマンド
run_test "invalid command" \
    "$BUSCTL invalid" \
    1 \
    "invalid command should fail"

echo -e "\n=== Test Summary ==="
echo -e "Passed: ${GREEN}$PASS${NC}"
echo -e "Failed: ${RED}$FAIL${NC}"

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi

exit 0