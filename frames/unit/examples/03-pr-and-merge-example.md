# PR作成とマージの詳細例

## 実装ユニットのPR作成

### 1. 変更のコミット

```bash
# 変更確認
git status
git diff

# ステージング
git add -A

# コミット（詳細なメッセージ）
git commit -m "feat($UNIT_ID): implement authentication system

- JWT token generation and validation
- Role-based access control (Admin, Customer, Guest)  
- Refresh token mechanism
- Password hashing with bcrypt
- Rate limiting (5 requests/minute)

Tests:
- ✅ Unit tests: 100% coverage
- ✅ Integration tests: all passing
- ✅ Security tests: OWASP compliance checked

🤖 Generated with Claude Code"
```

### 2. PR作成

```bash
# 親ブランチの決定
if [ -z "$PARENT_UNIT_ID" ]; then
    PARENT_BRANCH="main"
else
    PARENT_BRANCH="feat/$PARENT_UNIT_ID"
fi

# PR作成
gh pr create \
  --base "$PARENT_BRANCH" \
  --title "[$UNIT_ID] Authentication system implementation" \
  --body "## Summary
Implemented JWT-based authentication system with role-based access control.

## Changes
- Created auth module with JWT handling
- Implemented user authentication endpoints
- Added role-based middleware
- Comprehensive test coverage

## Test Results
\`\`\`
test_auth.py::TestAuthentication::test_generate_token PASSED
test_auth.py::TestAuthentication::test_verify_token_valid PASSED
test_auth.py::TestAuthentication::test_verify_token_invalid PASSED
test_auth.py::TestAuthentication::test_refresh_token PASSED
test_auth.py::TestRoleBasedAccess::test_admin_access PASSED
test_auth.py::TestRoleBasedAccess::test_customer_access PASSED
\`\`\`

## Checklist
- [x] Tests written and passing
- [x] Documentation updated
- [x] Security review completed
- [x] No breaking changes

## Dependencies
- PyJWT==2.8.0
- bcrypt==4.1.2

🤖 Generated with Claude Code"
```

### 3. PR作成の報告

```bash
# PR番号取得
PR_NUMBER=$(gh pr list --head "feat/$UNIT_ID" --json number --jq '.[0].number')
PR_URL=$(gh pr view $PR_NUMBER --json url --jq .url)

# 報告
busctl post --from unit:$UNIT_ID --type pr_created --task $UNIT_ID \
  --data "{
    \"pr_number\": \"$PR_NUMBER\",
    \"pr_url\": \"$PR_URL\",
    \"base_branch\": \"$PARENT_BRANCH\",
    \"files_changed\": 12,
    \"additions\": 450,
    \"deletions\": 20
  }"
```

## 親ユニットのマージ処理

### 1. 子のPR確認

```bash
# 子ユニットのPRリスト
gh pr list --state open --search "base:feat/$UNIT_ID"
```

### 2. PRレビューとマージ

```bash
# PR詳細確認
gh pr view $PR_NUMBER

# 差分確認
gh pr diff $PR_NUMBER

# CI/CDステータス確認
gh pr checks $PR_NUMBER

# マージ
gh pr merge $PR_NUMBER --merge --delete-branch
```

### 3. コンフリクト解決

```bash
# コンフリクトが発生した場合
git checkout feat/$UNIT_ID
git merge feat/${UNIT_ID}-users

# コンフリクト確認
git status --porcelain | grep "^UU"

# ファイルごとに解決
# 例：package.jsonのコンフリクト
git checkout --theirs package-lock.json  # 子の変更を採用
git add package-lock.json

# コード内のコンフリクトは手動で解決
vim src/api/routes.js
# <<<<<<< HEAD から >>>>>>> までを確認し、適切に統合

# 解決完了
git add -A
git commit -m "resolve: merge conflicts from child units

- Resolved route definitions conflict in routes.js
- Merged dependencies in package.json
- Kept both authentication and user management endpoints"
```

### 4. 最終PR作成（ルートユニットの場合）

```bash
# すべての子をマージ後、mainへのPR作成
gh pr create \
  --base main \
  --title "[root] E-Commerce API Implementation" \
  --body "## Overview
Complete implementation of E-Commerce API with all features.

## Included Features
- ✅ Authentication system (JWT, RBAC)
- ✅ User management API
- ✅ Product catalog API  
- ✅ Shopping cart functionality
- ✅ Order processing and payment integration

## Architecture
- Microservice-based design
- RESTful API standards
- Comprehensive test coverage (avg 95%)

## Performance
- Response time: < 100ms (p95)
- Throughput: 1000 req/s tested

## Security
- OWASP compliance
- Rate limiting implemented
- Input validation on all endpoints

## Deployment Notes
See deployment guide in docs/deployment.md

🤖 Generated with Claude Code"
```