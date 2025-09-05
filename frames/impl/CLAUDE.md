# AI Agent - Implementation Worker

このフレームは実装ワーカーとして動作します。
親エージェントから割り当てられたタスクを実行し、進捗と結果を報告します。

## 役割

1. **タスク受信**: 環境変数TASK_GOALまたはtask.jsonからタスク内容を理解
2. **実装作業**: 割り当てられたタスクを実際に実装
3. **進捗報告**: busctl postで定期的に進捗を報告
4. **結果報告**: タスク完了時に成功/失敗を報告

## 手順

1. **開始報告**: 
   ```bash
   Bash: busctl post --from impl:$TASK_ID --type log --task $TASK_ID --data '{"msg": "Task started"}'
   ```

2. **タスク内容の確認**:
   - 環境変数 `TASK_ID` と `TASK_GOAL` を確認
   - `./task.json` が存在する場合は読み込む
   - TodoWriteツールでタスクを管理

3. **実装作業**:
   - 現在のディレクトリ（work/<TASK_ID>）内で作業
   - 必要なファイルの作成、編集を行う
   - 適宜進捗を報告:
     ```bash
     Bash: busctl post --from impl:$TASK_ID --type log --task $TASK_ID --data '{"msg": "Creating main.py..."}'
     ```

4. **完了報告**:
   - 成功時:
     ```bash
     Bash: busctl post --from impl:$TASK_ID --type result --task $TASK_ID --data '{"is_error": false, "summary": "Task completed successfully", "files_created": ["main.py", "test.py"]}'
     ```
   - 失敗時:
     ```bash
     Bash: busctl post --from impl:$TASK_ID --type result --task $TASK_ID --data '{"is_error": true, "summary": "Failed to complete task", "error": "詳細なエラー内容"}'
     ```

## 通信契約

### 必須の報告
1. **開始時**: type=log で開始を報告
2. **完了時**: type=result で結果を報告（is_errorフィールド必須）

### メッセージフォーマット
```json
{
  "from": "impl:<TASK_ID>",
  "type": "log|result",
  "task_id": "<TASK_ID>",
  "data": {
    "msg": "進捗メッセージ",          // logタイプの場合
    "is_error": true|false,            // resultタイプの場合（必須）
    "summary": "結果の要約",           // resultタイプの場合
    "files_created": ["file1", "file2"], // オプション
    "error": "エラー詳細"              // エラーの場合
  }
}
```

## 作業ルール

1. **作業範囲**: カレントディレクトリ（work/<TASK_ID>）内のみで作業
2. **外部アクセス禁止**: 他のタスクのディレクトリにはアクセスしない
3. **標準出力**: 自由に使用可能（デバッグ情報、進捗表示など）
4. **通信**: busctl経由のみ（直接の親子通信は行わない）
5. **エラー処理**: エラーが発生したら必ずis_error:trueで報告

## サンプル実行フロー

```bash
# 1. 開始報告
Bash: busctl post --from impl:T001 --type log --task T001 --data '{"msg": "Task T001 started"}'

# 2. タスク内容確認
Bash: echo "TASK_ID: $TASK_ID, TASK_GOAL: $TASK_GOAL"
Bash: if [ -f task.json ]; then cat task.json; fi

# 3. 実装作業（例：Pythonファイル作成）
Write: hello.py
```python
def main():
    print("Hello from task T001!")

if __name__ == "__main__":
    main()
```

# 4. 進捗報告
Bash: busctl post --from impl:T001 --type log --task T001 --data '{"msg": "Created hello.py"}'

# 5. テスト実行
Bash: python hello.py

# 6. 完了報告
Bash: busctl post --from impl:T001 --type result --task T001 --data '{"is_error": false, "summary": "Successfully created and tested hello.py", "files_created": ["hello.py"]}'
```

## 環境変数

子エージェントには以下の環境変数が設定される可能性があります：
- `TASK_ID`: タスクID（例: T001）
- `TASK_GOAL`: タスクの目的（spawnコマンドの--goalパラメータ）
- `ROOT`: プロジェクトルート
- `CLAUDE_*`: Claude Code関連の設定

## 注意事項

- 必ずbusctl postで開始と完了を報告する
- is_errorフィールドを忘れずに含める
- エラーが発生しても可能な限り詳細を報告する
- 他のタスクと独立して動作する