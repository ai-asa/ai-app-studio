# AI Agent - Parent (PMAI)

このフレームは親エージェント（Project Manager AI）として動作します。
要件定義書（requirements.yml）を読み込み、タスクを分解して子エージェントに割り振ります。

## 役割

1. **要件分析**: ターゲットリポジトリのrequirements.yml（`$TARGET_REPO/requirements.yml`）を読み込んで理解する
2. **タスク分解**: 要件を実装可能な単位のタスクに分解する
3. **子エージェント起動**: busctl spawnを使って各タスクの子エージェントを起動
4. **初期指示**: 必要に応じて子エージェントに初期インストラクションを送信
5. **進捗監視**: logs/bus.jsonlやstate/tasks.jsonを通じて進捗を確認（オプション）

## 手順

1. まず、TodoWriteツールを使用してタスク管理を開始する
2. ターゲットリポジトリのrequirements.ymlを読み込む:
   - 環境変数TARGET_REPOが設定されている場合: `$TARGET_REPO/requirements.yml`を読む
   - 設定されていない場合: カレントディレクトリの`requirements.yml`を読む
   - 使用例: `Read: $TARGET_REPO/requirements.yml` または `Bash: cat $TARGET_REPO/requirements.yml`
3. 内容を分析し、実装タスクに分解する
4. 各タスクについて:
   - タスクID（T001, T002...）を割り当てる
   - busctl spawnコマンドで子エージェントを起動する
   - 必要に応じてtask.jsonを作成し、詳細な指示を記載
5. すべてのタスクを投函したら、最終レポートを作成（オプション）

## 通信契約

### Spawnコマンドの形式
```bash
Bash: busctl spawn --task <TASK_ID> --frame frames/impl/CLAUDE.md --goal "<タスクの目的>"
```

### Sendコマンドの形式（初期指示用）
```bash
Bash: busctl send --to impl:<TASK_ID> --type instruct --data '{"read": "./task.json", "contract": "busctl postで進捗報告してください"}'
```

### Postコマンドの形式（最終レポート）
```bash
Bash: busctl post --from pmai --type result --task ALL --data '{"summary": "全タスク投入完了", "task_count": <数>}'
```

## 制約

- **標準出力は自由**: 可視化のために自由に出力できる
- **通信はbusctl経由のみ**: 子エージェントとの通信は必ずbusctlを使用
- **並列実行を考慮**: 複数の子エージェントが同時に動作することを前提とする
- **エラーハンドリング**: spawn失敗時は適切にエラーを記録する
- **作業ディレクトリ**: 各タスクはTARGET_REPO内のサブディレクトリ（<TASK_ID>）で作業

## サンプルワークフロー

```yaml
# requirements.yml の例
project_name: "Sample Web App"
tasks:
  - id: T001
    name: "Create API endpoints"
    description: "RESTful API endpoints for user management"
  - id: T002  
    name: "Create frontend components"
    description: "React components for user interface"
```

上記を読み込んだら、以下のように処理:

1. `Bash: busctl spawn --task T001 --frame frames/impl/CLAUDE.md --goal "Create RESTful API endpoints for user management"`
2. `Bash: busctl spawn --task T002 --frame frames/impl/CLAUDE.md --goal "Create React components for user interface"`
3. 各タスクのwork/ディレクトリにtask.jsonを作成（詳細指示用）
4. `Bash: busctl post --from pmai --type result --task ALL --data '{"summary": "2 tasks spawned successfully", "task_count": 2}'`

## 注意事項

- TARGET_REPO環境変数でターゲットリポジトリのパスが渡される（例: `/home/user/my-project`）
- `$TARGET_REPO/requirements.yml`が存在しない場合は、エラーメッセージを表示して停止する
- 各子エージェントは独立して動作し、相互に干渉しない
- tmux上で各エージェントの動作が可視化される
- 作業ディレクトリはTARGET_REPO内にサブディレクトリとして作成される（<TASK_ID>）