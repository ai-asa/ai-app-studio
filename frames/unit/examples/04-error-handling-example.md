# エラー処理の詳細例

## よくあるエラーと対処法

### 1. 環境エラー

#### busctl: command not found
```bash
# 原因：PATHが通っていない
# 解決：
export PATH="$HOME/tools/ai-app-studio/bin:$PATH"

# または、フルパスで実行
~/tools/ai-app-studio/bin/busctl post --from unit:$UNIT_ID --type log --data '{"msg": "test"}'
```

#### requirements.yml not found
```bash
# エラー報告
busctl post --from unit:$UNIT_ID --type result --task $UNIT_ID \
  --data '{
    "is_error": true,
    "error_type": "configuration_error",
    "error": "requirements.yml not found in current directory",
    "attempted_locations": ["./requirements.yml", "../requirements.yml"],
    "recommendation": "Please create requirements.yml in the project root",
    "working_directory": "'$(pwd)'"
  }'
```

### 2. Git関連エラー

#### not a git repository
```bash
# 初期化試行
git init
git add .
git commit -m "Initial commit"

# それでも失敗する場合
busctl post --from unit:$UNIT_ID --type result --task $UNIT_ID \
  --data '{
    "is_error": true,
    "error_type": "git_error",
    "error": "Not a git repository",
    "context": {
      "directory": "'$(pwd)'",
      "parent_exists": "'$(test -d ../.git && echo true || echo false)'"
    },
    "recommendation": "Initialize git repository or check working directory"
  }'
```

#### ブランチ作成エラー
```bash
# ブランチが既に存在する場合
if git checkout feat/$UNIT_ID 2>/dev/null; then
    echo "Branch already exists, using existing branch"
else
    git checkout -b feat/$UNIT_ID
fi
```

### 3. 依存関係エラー

#### Pythonモジュール不足
```bash
# インストール試行
pip install pyjwt bcrypt

# 失敗した場合の詳細報告
busctl post --from unit:$UNIT_ID --type result --task $UNIT_ID \
  --data '{
    "is_error": true,
    "error_type": "dependency_error",
    "error": "Failed to import required modules",
    "details": {
      "missing_modules": ["jwt", "bcrypt"],
      "python_version": "'$(python --version 2>&1)'",
      "pip_version": "'$(pip --version 2>&1)'"
    },
    "attempted_fixes": [
      "pip install pyjwt bcrypt",
      "pip install --user pyjwt bcrypt",
      "python -m pip install pyjwt bcrypt"
    ],
    "recommendation": "Install dependencies manually or update requirements.txt"
  }'
```

### 4. テスト失敗

#### テストエラーの詳細報告
```bash
# pytestの出力をキャプチャ
TEST_OUTPUT=$(python -m pytest test_auth.py -v 2>&1)
TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -ne 0 ]; then
    busctl post --from unit:$UNIT_ID --type log --task $UNIT_ID \
      --data "{
        \"msg\": \"Test failures detected\",
        \"test_output\": \"$TEST_OUTPUT\",
        \"failed_count\": \"$(echo \"$TEST_OUTPUT\" | grep -c FAILED)\",
        \"passed_count\": \"$(echo \"$TEST_OUTPUT\" | grep -c PASSED)\"
      }"
      
    # 修正を試みる...
fi
```

### 5. API/ネットワークエラー

#### GitHub API エラー
```bash
# PR作成失敗
if ! gh pr create --base main --title "test" 2>/dev/null; then
    ERROR_MSG=$(gh pr create --base main --title "test" 2>&1)
    
    busctl post --from unit:$UNIT_ID --type result --task $UNIT_ID \
      --data "{
        \"is_error\": true,
        \"error_type\": \"github_api_error\",
        \"error\": \"Failed to create PR\",
        \"details\": \"$ERROR_MSG\",
        \"possible_causes\": [
          \"No GitHub token configured\",
          \"No push access to repository\",
          \"Network connectivity issues\"
        ],
        \"recommendation\": \"Check gh auth status and repository permissions\"
      }"
fi
```

### 6. リカバリー戦略

#### 一時的なエラーの場合
```bash
# リトライ機能
retry_command() {
    local max_attempts=3
    local delay=5
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if "$@"; then
            return 0
        fi
        
        echo "Attempt $attempt failed. Retrying in ${delay}s..."
        sleep $delay
        ((attempt++))
        ((delay*=2))  # 指数バックオフ
    done
    
    return 1
}

# 使用例
retry_command gh pr create --base main --title "[$UNIT_ID] Implementation"
```

#### 致命的エラーの場合
```bash
# 状態を保存して終了
save_state() {
    cat > emergency_state.json <<EOF
{
  "unit_id": "$UNIT_ID",
  "parent_unit_id": "$PARENT_UNIT_ID",
  "last_action": "$1",
  "error": "$2",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "work_completed": [
    "task_analysis",
    "test_creation"
  ],
  "work_pending": [
    "implementation",
    "pr_creation"
  ]
}
EOF

    busctl post --from unit:$UNIT_ID --type result --task $UNIT_ID \
      --data '{
        "is_error": true,
        "error_type": "fatal_error",
        "state_saved": true,
        "state_file": "emergency_state.json",
        "recovery_possible": true,
        "recovery_instructions": "Resume from emergency_state.json"
      }'
}
```