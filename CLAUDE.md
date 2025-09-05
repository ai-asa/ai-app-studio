
## 重要な開発ルール

### 1. 開発方針
- **MVP単位**: 最小限の実装単位で段階的に開発
- **TypeScript**: 型安全性を重視し、strictモードを使用
- **モジュラー設計**: エージェント、ツール、ワークフローを分離
- **テスト駆動開発（TDD）**: API開発のすべての工程で必須
  - 実装前に必ずテストを先に書く
  - Red-Green-Refactorサイクルを厳守
  - カバレッジ80%以上を維持

### 2. 開発手順
1. 必ず`docs/design.md`で現在の設計を確認
2. TodoWriteツールで作業中のタスクを管理
3. **TDDサイクルで開発**:
   - テストファースト: 失敗するテストを先に書く（Red）
   - 最小限の実装: テストを通す最小限のコードを書く（Green）
   - リファクタリング: コードを改善する（Refactor）
4. **1機能・2ファイル制限**:
   - 1回の実装で1つの機能のみを完成させる
   - 作成/変更するファイルは最大2つ（テスト1つ + 実装1つ）
   - 各機能を独立して実装・テスト可能にする
5. 段階的に機能を実装（Phase 1から順に）
6. 動作確認は自動テストと実機テストの両方で行う

### 3. テスト駆動開発（TDD）の実践
**すべてのAPI開発でTDDは必須です。例外はありません。**

#### TDDの実施手順
1. **ユーザーストーリーの理解**: 機能要件を明確にする
2. **テスト設計**: テストケースを洗い出す
3. **Red**: 失敗するテストを書く
4. **Green**: テストを通す最小限のコードを書く
5. **Refactor**: コードを改善する（テストは常にGreen）

#### テストの種類
- **ユニットテスト**: 個別の関数・メソッド
- **統合テスト**: 複数コンポーネントの連携
- **APIテスト**: エンドポイントの動作確認
- **E2Eテスト**: 完全なユーザーフロー

#### テストの命名規則
```typescript
describe('ComponentName', () => {
  describe('methodName', () => {
    it('should return expected result when given valid input', () => {
      // テストコード
    });
    
    it('should throw error when given invalid input', () => {
      // エラーケースのテスト
    });
  });
});
```

### 4. コミット・プッシュ・PR作成

**GitHub操作の手順：**
1. ブランチ作成: `git checkout -b ブランチ名`
2. 変更をステージング: `git add .` -> 基本的に変更内容は全てコミットするため、`.`でOK
3. コミット: `git commit -m "コミットメッセージ"`
4. リモートURL設定: `git remote set-url origin https://ai-asa:$GH_TOKEN@github.com/ai-asa/ai-app-studio.git`
5. プッシュ: `git push -u origin ブランチ名`
6. PR作成: `export GH_TOKEN="..." && gh pr create --base main --title "..." --body "..."`
7. セキュリティのため元に戻す: `git remote set-url origin https://github.com/ai-asa/ai-app-studio.git`

**注意：** GH_TOKENは`.env.local`に保存されています。

**コミットメッセージ規約:**
- feat: 新機能
- fix: バグ修正
- test: テスト追加
- docs: ドキュメント更新
- refactor: リファクタリング

