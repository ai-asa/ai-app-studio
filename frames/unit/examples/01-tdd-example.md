# TDD実装の詳細例

## 認証機能の実装例

### 1. テストファイル作成（Red）

```python
# test_auth.py
import pytest
from app.auth import generate_token, verify_token, refresh_token

class TestAuthentication:
    def test_generate_token(self):
        """JWT token生成テスト"""
        user_id = "user123"
        token = generate_token(user_id)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_token_valid(self):
        """有効なトークンの検証"""
        user_id = "user123"
        token = generate_token(user_id)
        
        payload = verify_token(token)
        assert payload is not None
        assert payload['user_id'] == user_id
    
    def test_verify_token_invalid(self):
        """無効なトークンの検証"""
        invalid_token = "invalid.token.here"
        
        payload = verify_token(invalid_token)
        assert payload is None
```

### 2. 最小限の実装（Green）

```python
# app/auth.py
import jwt
import datetime
from typing import Optional, Dict

SECRET_KEY = "your-secret-key"  # 本番環境では環境変数から

def generate_token(user_id: str) -> str:
    """JWTトークン生成"""
    payload = {
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def verify_token(token: str) -> Optional[Dict]:
    """JWTトークン検証"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.InvalidTokenError:
        return None

def refresh_token(old_token: str) -> Optional[str]:
    """JWTトークン更新"""
    payload = verify_token(old_token)
    if payload:
        return generate_token(payload['user_id'])
    return None
```

### 3. テスト実行とリファクタリング

```bash
# テスト実行
python -m pytest test_auth.py -v

# カバレッジ確認
coverage run -m pytest test_auth.py
coverage report

# リンター実行
flake8 app/auth.py --max-line-length=100

# 型チェック
mypy app/auth.py
```

### 4. 進捗報告

```bash
busctl post --from unit:$UNIT_ID --type log --task $UNIT_ID \
  --data '{"msg": "Authentication tests created", "files": ["test_auth.py"]}'

busctl post --from unit:$UNIT_ID --type log --task $UNIT_ID \
  --data '{"msg": "Authentication implementation completed", "files": ["app/auth.py"], "coverage": "100%"}'
```