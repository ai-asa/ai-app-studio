#!/usr/bin/env bash
# busd + tmuxの統合テスト

set -euo pipefail

# テスト環境設定
export TEST_ROOT=$(mktemp -d)
export ROOT="$TEST_ROOT"
export TMUX_SESSION="test-$(date +%s)"
export CLAUDE_CMD="echo 'Mock Claude Code started for task \$TASK_ID'; sleep 3600"

# クリーンアップ
cleanup() {
    tmux kill-session -t "$TMUX_SESSION" 2>/dev/null || true
    rm -rf "$TEST_ROOT"
}
trap cleanup EXIT

echo "=== busd + tmux Integration Test ==="
echo "Test ROOT: $ROOT"
echo "TMUX Session: $TMUX_SESSION"

# busdをバックグラウンドで起動
echo -e "\n--- Starting busd daemon ---"
python3 bin/busd.py &
BUSD_PID=$!
sleep 2

# tmuxセッションの確認
if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    echo "✓ TMUX session created: $TMUX_SESSION"
else
    echo "✗ TMUX session not created"
fi

# spawn テスト
echo -e "\n--- Testing spawn ---"
./bin/busctl spawn --task T001 --goal "Test task 1"
sleep 2

# pane確認
if tmux list-windows -t "$TMUX_SESSION" | grep -q "T001"; then
    echo "✓ Window T001 created"
else
    echo "✗ Window T001 not created"
fi

# state確認
if [[ -f "$ROOT/state/tasks.json" ]]; then
    echo "✓ tasks.json created:"
    cat "$ROOT/state/tasks.json" | python3 -m json.tool | head -10
fi

# bus.jsonl確認
echo -e "\n--- Testing post ---"
./bin/busctl post --from impl:T001 --type log --task T001 --data '{"msg":"Task started"}'
sleep 1

if [[ -f "$ROOT/logs/bus.jsonl" ]]; then
    echo "✓ bus.jsonl created:"
    tail -n 1 "$ROOT/logs/bus.jsonl" | python3 -m json.tool | head -10
fi

# tmuxセッション一覧
echo -e "\n--- TMUX session status ---"
tmux list-windows -t "$TMUX_SESSION" 2>/dev/null || true

# busdを停止
echo -e "\n--- Stopping busd ---"
kill $BUSD_PID 2>/dev/null || true
wait $BUSD_PID 2>/dev/null || true

echo -e "\n✓ Integration test completed"