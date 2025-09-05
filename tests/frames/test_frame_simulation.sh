#!/usr/bin/env bash
# フレーム動作のシミュレーションテスト

set -euo pipefail

# 環境設定
export TEST_ROOT=$(mktemp -d)
export ROOT="$TEST_ROOT"
trap 'rm -rf "$TEST_ROOT"' EXIT

echo "=== Frame Simulation Test ==="
echo "Test ROOT: $ROOT"

# 1. 親フレームのシミュレーション
echo -e "\n--- Parent Frame Simulation ---"

# requirements.ymlをコピー
cp requirements.yml "$ROOT/"

# 親エージェントがやることをシミュレート
echo "1. Reading requirements.yml..."
cat "$ROOT/requirements.yml" | grep -E "id:|goal:" | head -10

echo -e "\n2. Spawning child agents..."
# T001をspawn
./bin/busctl spawn --task T001 --cwd work/T001 --frame frames/impl/CLAUDE.md --goal "Create a hello.txt file with greeting message"
echo "✓ Spawned T001"

# T002をspawn  
./bin/busctl spawn --task T002 --cwd work/T002 --frame frames/impl/CLAUDE.md --goal "Create calculator.py with basic arithmetic functions"
echo "✓ Spawned T002"

# spawn確認
echo -e "\n3. Checking spawn messages..."
ls -la "$ROOT/mbox/bus/in/" | tail -5

# 2. 子フレームのシミュレーション
echo -e "\n--- Child Frame Simulation ---"

# T001のシミュレーション
export TASK_ID=T001
export TASK_GOAL="Create a hello.txt file"

echo "1. Starting task T001..."
./bin/busctl post --from impl:T001 --type log --task T001 --data '{"msg": "Task T001 started"}'

echo "2. Working on task..."
mkdir -p "$ROOT/work/T001"
echo "Hello from task T001!" > "$ROOT/work/T001/hello.txt"

echo "3. Reporting progress..."
./bin/busctl post --from impl:T001 --type log --task T001 --data '{"msg": "Created hello.txt"}'

echo "4. Completing task..."
./bin/busctl post --from impl:T001 --type result --task T001 --data '{"is_error": false, "summary": "Successfully created hello.txt", "files_created": ["hello.txt"]}'

# 結果確認
echo -e "\n--- Checking Results ---"

echo "1. Work directory contents:"
find "$ROOT/work" -type f | head -10

echo -e "\n2. Message queues:"
echo "Bus inbox:"
ls "$ROOT/mbox/bus/in/" 2>/dev/null | wc -l
echo "PMAI inbox:" 
ls "$ROOT/mbox/pmai/in/" 2>/dev/null | wc -l

echo -e "\n✓ Frame simulation test completed"