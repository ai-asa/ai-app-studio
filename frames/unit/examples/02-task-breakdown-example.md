# タスク分解の詳細例

## WebアプリケーションのAPIサーバー実装

### 1. 要件分析

requirements.yml から以下のような要件を読み取った場合：

```yaml
project_name: "E-Commerce API"
description: "電子商取引プラットフォームのバックエンドAPI"
features:
  - ユーザー管理（登録、ログイン、プロフィール）
  - 商品カタログ管理
  - カート機能
  - 注文処理
  - 決済連携
```

### 2. タスク分解ファイルの作成

```yaml
# task-breakdown.yml
parent_unit: root
total_tasks: 5
tasks:
  - id: auth
    description: "認証・認可システムの実装"
    complexity: high
    details:
      - JWTベースの認証
      - ロール基準のアクセス制御
      - セッション管理
      
  - id: users
    description: "ユーザー管理APIの実装"
    complexity: medium
    details:
      - ユーザー登録・更新・削除
      - プロフィール管理
      - パスワードリセット
    dependencies: [auth]
    
  - id: products
    description: "商品カタログAPIの実装"
    complexity: medium
    details:
      - 商品CRUD操作
      - カテゴリ管理
      - 在庫管理
      - 検索・フィルタリング
    dependencies: [auth]
    
  - id: cart
    description: "カート機能の実装"
    complexity: medium
    details:
      - カート操作（追加・削除・更新）
      - セッション管理
      - 価格計算
    dependencies: [auth, users, products]
    
  - id: orders
    description: "注文・決済処理の実装"
    complexity: high
    details:
      - 注文作成・管理
      - 決済API連携
      - 注文履歴
      - 返品処理
    dependencies: [cart]
```

### 3. 子ユニットへのスコープされた要件

各子ユニット用のディレクトリに作成：

```yaml
# auth/scoped-requirements.yml
parent_task: "E-Commerce API"
focus_area: "認証・認可システム"
specific_requirements:
  - JWT (RS256) を使用した認証
  - リフレッシュトークンの実装
  - ロールベースアクセス制御（Admin, Customer, Guest）
  - トークン有効期限：アクセス15分、リフレッシュ30日
constraints:
  - bcryptでパスワードハッシュ化
  - rate limiting実装（5回/分）
  - OWASP準拠のセキュリティ実装
```

### 4. 子ユニット生成時の処理

```bash
# 各タスクごとに子ユニットを生成
# busdが自動的にUNIT_IDを生成し、適切な環境変数を設定

# 例：認証システムの子ユニット
# UNIT_ID=root-auth として自動生成される
# requirements.ymlとscoped-requirements.ymlが自動的にコピーされる
```

### 5. 子の状態追跡

```yaml
# children-status.yml (自動更新)
children:
  - unit_id: root-auth
    status: running
    started_at: "2025-01-09T10:00:00Z"
    branch: feat/root-auth
    
  - unit_id: root-users
    status: pending
    dependencies_waiting: [root-auth]
    
  - unit_id: root-products
    status: pending
    dependencies_waiting: [root-auth]
    
  - unit_id: root-cart
    status: blocked
    dependencies_waiting: [root-auth, root-users, root-products]
    
  - unit_id: root-orders
    status: blocked
    dependencies_waiting: [root-cart]
```