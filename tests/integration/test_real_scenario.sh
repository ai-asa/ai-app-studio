#!/usr/bin/env bash
# 実際の使用シナリオでの統合テスト

set -euo pipefail

echo "=== Real Scenario Integration Test ==="

# テスト用プロジェクトディレクトリを作成
TEST_PROJECT=$(mktemp -d)
trap 'rm -rf "$TEST_PROJECT"' EXIT

# ai-app-studioのパス
AI_APP_STUDIO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "Test project: $TEST_PROJECT"
echo "AI App Studio: $AI_APP_STUDIO"

# 1. テストプロジェクトをgitリポジトリとして初期化
cd "$TEST_PROJECT"
git init
git config user.name "Test User"
git config user.email "test@example.com"
# mainブランチを使用（busdが期待している）
git checkout -b main
echo "# Test Project" > README.md
git add README.md
git commit -m "Initial commit"

# 2. requirements.ymlを作成
cat > requirements.yml << 'EOF'
project_name: "Integration Test"
tasks:
  - id: T001
    name: "Test task"
    goal: "Create test.txt file"
EOF

echo -e "\n--- Step 1: Starting busd daemon ---"
# TMUXがない環境向けの設定
export TMUX_SESSION="test-$$"
# テスト用にClaude Codeの代わりにechoを使用
export CLAUDE_CMD="echo 'Mock Claude Code started'"

# busdをバックグラウンドで起動（詳細ログ付き）
python3 "$AI_APP_STUDIO/bin/busd.py" > busd.log 2>&1 &
BUSD_PID=$!

# 起動を少し待つ
sleep 3

# busdが起動したか確認
if ps -p $BUSD_PID > /dev/null; then
    echo "✓ busd daemon started (PID: $BUSD_PID)"
else
    echo "✗ busd daemon failed to start"
    cat busd.log
    exit 1
fi

echo -e "\n--- Step 2: Spawning task with busctl ---"
# busctlでタスクを投函（フレームパスを指定しない）
"$AI_APP_STUDIO/bin/busctl" spawn --task T001 --goal "Create test.txt"

# mailboxにメッセージが作成されたか確認
sleep 1
if ls mbox/bus/in/*.json > /dev/null 2>&1; then
    echo "✓ Spawn message created"
    cat mbox/bus/in/*.json | python3 -m json.tool | head -20
else
    echo "✗ No spawn message found"
fi

# worktreeが作成されたか確認（少し待つ）
sleep 2
if [[ -d "work/T001" ]]; then
    echo "✓ Worktree created: work/T001"
else
    echo "✗ Worktree not created"
    echo "busd.log contents:"
    cat busd.log | tail -20
fi

echo -e "\n--- Step 3: Checking state files ---"
if [[ -f "state/tasks.json" ]]; then
    echo "✓ tasks.json created:"
    cat state/tasks.json | python3 -m json.tool
else
    echo "✗ tasks.json not found"
fi

echo -e "\n--- Step 4: Manual task completion ---"
# 手動でタスク完了を報告
"$AI_APP_STUDIO/bin/busctl" post \
    --from impl:T001 \
    --type result \
    --task T001 \
    --data '{"is_error": false, "summary": "Test completed"}'

sleep 1
if [[ -f "logs/bus.jsonl" ]]; then
    echo "✓ bus.jsonl updated:"
    tail -n 1 logs/bus.jsonl | python3 -m json.tool
else
    echo "✗ bus.jsonl not found"
fi

# クリーンアップ
echo -e "\n--- Cleanup ---"
kill $BUSD_PID 2>/dev/null || true
wait $BUSD_PID 2>/dev/null || true

echo -e "\n✓ Integration test completed successfully"