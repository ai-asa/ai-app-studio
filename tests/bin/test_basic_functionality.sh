#!/usr/bin/env bash
# 基本機能の簡単なテスト

set -euo pipefail

echo "=== Basic Functionality Test ==="

# ai-app-studioのパス  
AI_APP_STUDIO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
echo "AI App Studio: $AI_APP_STUDIO"

# 1. busctlの基本動作確認
echo -e "\n--- Test 1: busctl basic execution ---"
OUTPUT=$("$AI_APP_STUDIO/bin/busctl" 2>&1 || true)
if echo "$OUTPUT" | grep -q "Usage: busctl"; then
    echo "✓ busctl shows usage"
else
    echo "✗ busctl failed"
    echo "$OUTPUT"
fi

# 2. フレームファイルの存在確認
echo -e "\n--- Test 2: Frame files exist ---"
if [[ -f "$AI_APP_STUDIO/frames/pmai/CLAUDE.md" ]]; then
    echo "✓ Parent frame exists"
else
    echo "✗ Parent frame missing"
fi

if [[ -f "$AI_APP_STUDIO/frames/impl/CLAUDE.md" ]]; then
    echo "✓ Implementation frame exists"
else
    echo "✗ Implementation frame missing"
fi

# 3. Python構文チェック
echo -e "\n--- Test 3: Python syntax check ---"
if python3 -m py_compile "$AI_APP_STUDIO/bin/busd.py" 2>&1; then
    echo "✓ busd.py syntax is valid"
else
    echo "✗ busd.py has syntax errors"
fi

# 4. 一時ディレクトリでbusctlをテスト
echo -e "\n--- Test 4: busctl in temporary directory ---"
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

"$AI_APP_STUDIO/bin/busctl" spawn --task TEST --goal "test goal" || true

if ls mbox/bus/in/*.json 2>/dev/null; then
    echo "✓ busctl created message file"
    cat mbox/bus/in/*.json | python3 -m json.tool | head -10
else
    echo "✗ No message file created"
fi

rm -rf "$TEMP_DIR"

echo -e "\n✓ Basic functionality test completed"