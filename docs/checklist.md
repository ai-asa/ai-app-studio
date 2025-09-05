# 開発チェックリスト - AIエージェントオーケストレーションシステム

## 概要
展示会向けtmux可視化＋ファイルベース・メッセージバス設計（v0.9 MVP-of-MVP）の実装チェックリスト。

## Phase 1: MVP-of-MVP 実装

### 1. プロジェクト基本構造の作成
- [x] `/bin/` ディレクトリ作成
- [x] `/frames/` ディレクトリ構造作成
  - [x] `/frames/pmai/` - 親エージェント用
  - [x] `/frames/impl/` - 子エージェント用
- [x] `/mbox/` ディレクトリ構造作成
  - [x] `/mbox/bus/in/` - busデーモン受信用
  - [x] `/mbox/pmai/in/` - 親エージェント受信用
- [x] `/logs/` ディレクトリ構造作成
  - [x] `/logs/raw/` - tmux paneの生ログ
- [x] `/state/` ディレクトリ作成
- [x] `/work/` ディレクトリ作成（git worktree用）

### 2. busctl CLIの実装（投函CLI）
**ファイル:** `/bin/busctl`

#### 基本機能
- [x] shebang行とerror handlingの設定
- [x] 環境変数設定（ROOT、MBOX）
- [x] タイムスタンプ生成関数 `ts()`
- [x] ランダム文字列生成関数 `rand()`
- [x] atomic write実装 `write_json()`

#### サブコマンド実装
- [x] `spawn` コマンド
  - [x] 引数パース（--task, --cwd, --frame, --goal, --branch）
  - [x] JSON封筒の構築
  - [x] mbox/bus/in/への投函
- [x] `send` コマンド
  - [x] 引数パース（--to, --type, --data）
  - [x] 宛先別mailbox決定
  - [x] JSON封筒の構築と投函
- [x] `post` コマンド
  - [x] 引数パース（--from, --type, --task, --data）
  - [x] mbox/pmai/in/への投函
  - [x] resultタイプではis_error必須チェック

#### テスト
- [x] 各コマンドのユニットテスト作成
- [x] atomic write動作検証
- [x] JSONフォーマット検証

### 3. busd デーモンの実装（tmuxオーケストレータ）
**ファイル:** `/bin/busd.py`

#### 基本機能
- [x] メイン関数とループ実装
- [x] tmuxセッション管理 `ensure_session()`
- [x] pane_map（task_id → pane_id）管理
- [x] state/panes.json永続化

#### メッセージハンドラ
- [x] `handle_spawn()` 実装
  - [x] git branch作成（存在チェック付き）
  - [x] git worktree追加
  - [x] tmux new-window実行
  - [x] tmux pipe-pane設定
  - [x] pane_map更新
- [x] `handle_send()` 実装
  - [x] 宛先pane解決
  - [x] tmux send-keys実行
  - [x] エラーハンドリング
- [x] `handle_post()` 実装
  - [x] logs/bus.jsonl追記
  - [x] state/tasks.json更新
  - [x] statusの状態遷移

#### mailbox処理
- [x] `process_mbox_once()` 実装
- [x] ファイル名ソート処理
- [x] エラーハンドリング
- [x] 処理済みファイル削除

#### テスト
- [x] tmuxセッション作成テスト
- [x] spawn処理のE2Eテスト
- [x] send/post処理の統合テスト
- [x] 復旧処理テスト

### 4. フレーム（CLAUDE.md）の実装

#### 親フレーム `/frames/pmai/CLAUDE.md`
- [x] requirements.yml読み込み処理
- [x] タスク分解ロジック
- [x] busctl spawn呼び出しコード
- [x] 初期send処理（オプション）
- [x] 最終レポート生成

#### 子フレーム `/frames/impl/CLAUDE.md`
- [x] 開始時のbusctl postコール
- [x] task.json読み込み処理
- [x] 作業実行ロジック
- [x] 進捗報告（busctl post --type log）
- [x] 完了報告（busctl post --type result）
- [x] エラーハンドリングとis_error設定

### 5. 設定・サンプルファイル
- [x] `requirements.yml` サンプル作成
- [x] `.env` テンプレート（環境変数）
- [x] `task.json` サンプル（各タスク用）
- [x] `README.md` 簡易使い方ガイド

### 6. 統合テスト＆デバッグ
- [x] E2Eシナリオテスト
  - [x] 親起動→spawn投函→子起動確認
  - [x] send送信→子受信確認
  - [x] post投函→集約確認
  - [x] ダッシュボード表示確認
- [x] tmuxレイアウト検証
- [x] ログ出力検証
- [ ] エラーケーステスト
  - [ ] busd停止→再起動時の復旧
  - [ ] 不正なメッセージ形式
  - [ ] tmux pane死亡

### 7. ビルド＆デプロイ準備
- [ ] 依存関係リスト作成
- [ ] インストールスクリプト
- [ ] 起動スクリプト（systemd unit等）
- [ ] デモ用データセット準備

## 進捗メモ（2025年9月3日）

### 完了事項
- Phase 1-1〜1-5まで完了
- busctl, busd, フレーム実装完了
- 基本的なテスト作成完了
- **busdのtmux pane ID取得エラーを修正**
  - f-stringの波かっこをエスケープして解決（`#{{...}}`）
  - tmux new-windowの-Pオプションと--の使用で正しくpane IDを取得
- **E2Eテストスクリプト作成**
  - `tests/e2e/test_full_flow.py`を作成
  - pane ID取得の修正確認テストに成功
- **pane作成とClaude Code起動に成功**
  - `%410`などのpane IDが正しく取得され、ログも記録される
  - Claude Codeがログイン画面で待機している状態を確認

### 本日の成果（2025年9月4日追記）
1. **tmuxレイアウト問題を解決**
   - 「size missing」エラーを修正（-p50オプションを削除）
   - 複数pane ID取得問題を修正（display-messageを使用）
   - ペイン数上限エラーのハンドリング追加
   - リファクタリングでコード品質向上

2. **統合テストを完全実装**
   - busctlスクリプトを作成
   - send/post機能の包括的テスト作成
   - JSONエスケープ問題を修正
   - すべてのテストが成功

3. **TDDサイクルの実践**
   - Red: 失敗するテストを先に作成
   - Green: 最小限の実装でテストを通す
   - Refactor: コードを改善（定数化、コメント追加）

4. **ビルドテストの実施**
   - Python構文チェック: エラー0
   - プロジェクト構造チェック: すべてOK
   - 必須ファイルチェック: すべて存在

### 技術的なポイント
1. **tmux split-windowの互換性**
   - `-p50`オプションは環境によっては「size missing」エラー
   - オプションなしか`-l`オプションが安全

2. **pane ID取得の正しい方法**
   - `tmux list-panes -t`は複数結果を返す可能性
   - `tmux display-message -p -F`が正確

3. **busctlのJSONパラメータ**
   - シェルでのクォート処理に注意
   - テストでは適切なエスケープが必要

### 残課題
1. **Claude Codeのログイン問題**
   - 新しいリポジトリではログイン画面が表示される
   - 展示会では事前ログインまたは環境変数設定が必要

2. **TARGET_REPO問題（2025年1月9日 解決）**
   - ✅ busd.pyがターゲットリポジトリを認識する仕組みを実装
   - ✅ 作業ディレクトリを`TARGET_REPO/.ai-app-studio/`に設定
   - ✅ 環境変数TARGET_REPOを子プロセスに引き継ぐ実装
   - ✅ PMAIフレームがTARGET_REPO/requirements.ymlを読むように修正完了
   - 設計思想：AI App Studioは汎用オーケストレーターであり、任意のリポジトリに対して動作すべき

### busctlのJSONエスケープ問題の修正完了（2025年9月5日）
1. **問題の内容**
   - 現象：子エージェントがbusctl postでメッセージを送信する際、JSONパースエラーが発生
   - 原因：bashスクリプトのbusctlで`"data":$D`の部分を直接展開していたため、特殊文字でJSONが壊れる
   
2. **実施した修正**
   - PythonでbusctlをTDDアプローチで再実装（`bin/busctl.py`）
   - JSONライブラリを使用して安全なJSON処理を実現
   - 元のbashスクリプトはバックアップとして`bin/busctl.bash`に保存
   - `bin/busctl`をPython実装へのラッパースクリプトに変更
   
3. **テスト実施内容**
   - 特殊文字（改行、引用符、タブ、Unicode絵文字等）を含むメッセージのユニットテスト作成
   - atomic writeの並行実行テスト
   - 複雑なネストしたJSONデータのテスト
   - すべてのテストが成功（9 tests passed）

4. **改善点**
   - JSONエスケープ問題が根本的に解決
   - より堅牢なエラーハンドリング
   - ヘルプメッセージと使用例の追加
   - datetime deprecation warningの修正（timezone-aware UTC使用）

### 設計の期待値ギャップ判明（2025年9月5日）
1. **ユーザーの期待との相違**
   - ユーザー期待: 親と子が相互に結果をもって連動する
   - 現在の設計: プル型アーキテクチャで、親は能動的にファイルを読む必要がある
   - 設計意図: 「受け付けられないタイミング問題」を回避するため
   
2. **docs/design.mdへの追記**
   - セクション11.1「期待と現状のギャップ」を追加
   - ユーザーの期待と現在の設計の違いを明文化
   - 改善の方向性を記載

### git worktree機能の修正完了（2025年9月5日）
1. **問題の内容**
   - 現象：ブランチやworktreeが作成されていない
   - 原因：gitコマンドを`.ai-app-studio/`で実行していた（TARGET_REPOで実行すべき）
   
2. **実施した修正（TDDアプローチ）**
   - `tests/unit/test_busd_worktree.py` - 包括的なテストケース作成
   - `ensure_worktree`関数の修正：
     - TARGET_REPOでgitコマンドを実行
     - 環境変数TARGET_REPOの優先順位を修正
     - master/mainブランチの自動判定
   - `tests/e2e/test_worktree_integration.py` - 統合テスト作成
   
3. **動作確認**
   - TARGET_REPOでブランチ（feat/T001等）が正しく作成される
   - `.ai-app-studio/work/T001`にworktreeが作成される
   - worktree内でコミットしたファイルがブランチに反映される
   - すべてのテスト（6件のユニットテスト）が成功

### 空のリポジトリ対応（2025年9月5日）
1. **問題の内容**
   - 現象：コミットがない新規リポジトリで「fatal: not a valid object name: 'main'」エラー
   - 原因：1からの開発を想定したシステムだが、空のリポジトリに対応していなかった
   
2. **実施した修正**
   - 空のリポジトリを検出した場合の自動初期化機能を追加：
     - 初期コミットを自動作成（--allow-empty）
     - `.gitignore`ファイルを作成（`.ai-app-studio/`を除外）
     - git設定がない場合はデフォルト値を設定
   - `tests/unit/test_busd_empty_repo.py` - 空のリポジトリ用テスト作成
   
3. **動作確認**
   - 空のリポジトリでも正常に動作
   - 初期コミットが自動的に作成される
   - ブランチとworktreeが正しく作成される
   - ユーザーからの動作確認済み

### ユーザー要望の実装状況（2025年9月5日）

#### 要望事項
1. タスクごとにブランチを切って、そのブランチのworktreeで各子claude codeが作業する
2. 各子が完了した段階でPRを作成してマージまで行う
3. コンフリクトが発生した場合に対処する
4. 最終的にすべてのコンフリクトを解消し、すべての開発が完了した状態になる

#### 実装状況
1. ✅ **タスクごとのブランチ・worktree機能** - 実装完了（2025年9月5日）
   - TARGET_REPOでブランチ作成（feat/T001等）
   - `.ai-app-studio/work/T001`にworktreeを作成
   - 各子エージェントが独立した環境で作業可能
   
2. ❌ **PR作成・マージ機能** - 未実装
   - 設計書で「CI/PR 自動化」は非目標（後回し）として記載
   - 子エージェントフレームにPR作成の指示なし
   - CLAUDE.mdに記載されているgh prコマンドは未統合
   
3. ❌ **コンフリクト対処機能** - 未実装
   - コンフリクト検知・解決のロジックなし
   - 現在は独立worktreeで作業するため作業中のコンフリクトは発生しない
   
4. ❌ **統合・完了機能** - 未実装
   - マージ処理自体が未実装
   - 統合テストや最終確認のフローなし

### worktree配置問題の発見（2025年9月5日）
1. **問題の内容**
   - 現象：開発成果が`.ai-app-studio/work/`内に作成される
   - 問題：`.gitignore`で`.ai-app-studio/`が除外されるため、開発成果もgitignoreされる
   - 影響：開発したコードがコミット・プッシュできない

2. **採用する解決策**
   - **並列ディレクトリ方式**を採用
   - TARGET_REPOの親ディレクトリにworktreeを作成
   - 例：`/workspace/my-project-T001/`（feat/T001ブランチ）

3. **必要な実装変更**
   - `ensure_worktree`関数：親ディレクトリにworktree作成
   - 命名規則：`{repo-name}-{task-id}`
   - spawnパラメータの調整
   - 環境変数の見直し

### worktree配置の修正完了（2025年9月5日）
1. **問題の内容と解決**
   - 問題：worktreeが`.ai-app-studio/work/`内に作成され、gitignoreされていた
   - 解決：並列ディレクトリ方式を採用（TARGET_REPOの親ディレクトリに作成）
   - 例：`/workspace/my-project-T001/`（feat/T001ブランチ）

2. **実装内容（TDDアプローチ）**
   - `get_worktree_path`関数を追加：並列ディレクトリパスを計算
   - `ensure_worktree`関数を修正：cwdパラメータを削除、worktree_pathを返すように変更
   - `spawn_child`関数を修正：worktree_pathパラメータに対応
   - `handle_spawn`関数を修正：cwdパラメータの削除
   - PMAIフレームを修正：spawnコマンドからcwdパラメータを削除

3. **テスト結果**
   - ユニットテスト：5件すべて成功
   - 統合テスト：並列ディレクトリ作成とコミット可能性を確認
   - ビルドテスト：全Pythonファイルの構文チェック成功

### worktree配置の再修正完了（2025年9月5日 追記）
1. **ユーザーフィードバックに基づく変更**
   - 並列ディレクトリ方式（`~/repo/test-project-T001`）から
   - サブディレクトリ方式（`~/repo/test-project/T001`）に変更
   
2. **実装内容（TDDアプローチ）**
   - `get_worktree_path`関数を再修正：TARGET_REPO内のサブディレクトリを返す
   - 単体テスト・統合テストを作成・更新
   - PMAIフレームのドキュメントを更新

3. **利点**
   - すべてが1つのディレクトリ内に整理される
   - タスクごとのディレクトリが見つけやすい
   - 一般的なプロジェクト構造に準拠

### 次回作業内容（優先順）
1. **tmuxレイアウトの改善**
   - 複数タスク時のペイン制限問題の解決
   - MAINウィンドウのレイアウト最適化
   - エラーハンドリングの強化

2. **PR作成・マージ機能の実装**
   - 子エージェントフレームにPR作成処理を追加
   - busdにPR管理機能を追加
   - ghコマンドの活用
   
3. **親エージェントへの完了通知の改善**
   - 現状：子エージェントの完了メッセージが親のTTYに届かない（設計通りだが実用性に課題）
   - 対策案1：resultメッセージ受信時に親のpaneに通知を送る機能追加
   - 対策案2：親エージェントにファイル監視機能を実装
   - 対策案3：PMAIフレームに定期的なポーリング処理を追加
   
4. エラーケーステストの実装
   - busd停止→再起動時の復旧
   - 不正なメッセージ形式のハンドリング
   - tmux pane死亡時の動作

5. 展示会向けデモシナリオ作成
4. インストール・起動スクリプト作成
5. requirements.ymlサンプルの拡充

### 引き継ぎ事項（worktree配置修正）
- **実装時の注意点**：
  1. 親ディレクトリの書き込み権限確認が必要
  2. 既存のworktreeとの名前衝突を避ける仕組み
  3. 絶対パスでの管理が必要（相対パスは避ける）
  4. tmuxのcdコマンドも新しいパスに対応させる
  
- **テスト観点**：
  1. 親ディレクトリへの書き込み権限がない場合
  2. 同名のディレクトリが既に存在する場合
  3. worktree削除時のクリーンアップ
  
- **影響範囲**：
  1. busd.py: `ensure_worktree`関数
  2. busd.py: `spawn_child`関数（cd先の変更）
  3. frames/pmai/CLAUDE.md: spawn時のcwdパラメータ
  4. 全テストケース: パスの変更

### その他の引き継ぎ事項
- **tmux split-windowの「size missing」エラー対策**：
  ```bash
  # 試すべきコマンド：
  tmux attach -t cc  # アタッチしてから実行
  tmux set -g default-terminal "screen-256color"  # ターミナル設定
  tmux split-window -l 20  # -lで行数指定
  tmux split-window  # オプション無しで実行
  ```
- **展示会向け改善の方向性**：
  - 視覚的に複数AIが同時に動く様子を見せたい
  - 左上：PMAI、左下：ダッシュボード、右側：子AI（動的増加）
  - レイアウトが難しい場合は、別ウィンドウでも視覚効果は出せる

## 実装順序（推奨）
1. busctl（最も独立性が高い）
2. busd基本構造＋spawnハンドラ
3. 最小限のフレーム実装
4. send/postハンドラ追加
5. E2Eテスト実施
6. ドキュメント整備

## 完了条件（DoD）
- [ ] すべてのコンポーネントがTDD実装されている
- [ ] E2Eテストが通る
- [ ] tmux上で親子の動作が可視化される
- [ ] logs/bus.jsonlに全イベントが記録される
- [ ] state/tasks.jsonでタスク状態が追跡できる
- [ ] デモシナリオが動作する

## セキュリティチェック
- [ ] 権限設定の確認（--dangerously-skip-permissionsはデモ限定）
- [ ] atomic write実装の検証
- [ ] git操作の安全性確認
- [ ] tmuxコマンドインジェクション対策

## パフォーマンスチェック
- [ ] mailboxポーリング間隔の最適化（500ms）
- [ ] ログファイルサイズ管理
- [ ] tmux pane数の制限検討

## 次フェーズへの準備（Phase 2以降）
- [ ] 公平キューの設計検討
- [ ] broadcastメッセージ型の仕様策定
- [ ] 再試行/死亡検知メカニズムの設計
- [ ] 永続DB移行の計画

## 実装済み機能の詳細（2025年1月9日追記）

### TARGET_REPO機能の部分実装
#### 実装したアーキテクチャ
- **作業リポジトリベース**のアプローチを採用
- ターゲットリポジトリ内に `.ai-app-studio/` サブディレクトリを作成
- 以下の構造で管理：
  ```
  my-project/                      # ターゲットリポジトリ
  ├── requirements.yml            # プロジェクトの要件
  └── .ai-app-studio/           # AI App Studioの作業ディレクトリ
      ├── mbox/                 # メッセージボックス
      ├── logs/                 # ログ
      ├── state/                # 状態管理
      └── work/                 # worktree
  ```

#### 使用方法
```bash
# 作業したいリポジトリに移動
cd /path/to/my-project

# AI App Studioを起動（現在のディレクトリがTARGET_REPOになる）
~/tools/ai-app-studio/bin/busd.py

# または、引数で指定も可能
~/tools/ai-app-studio/bin/busd.py /path/to/my-project
```

#### TDDによる実装内容
1. **テストファイル**: `tests/e2e/test_target_repo.py`を作成
2. **busd.py の修正**:
   - コマンドライン引数でTARGET_REPOを受け取る
   - デフォルトは現在のディレクトリ（`Path.cwd()`）
   - 作業ディレクトリを `TARGET_REPO/.ai-app-studio/` に設定
   - 環境変数 `TARGET_REPO` を子プロセスに引き継ぐ
3. **テスト内容**:
   - 現在のディレクトリをTARGET_REPOとして使用するケース
   - 引数でTARGET_REPOを指定するケース
   - 環境変数TARGET_REPOの引き継ぎ確認
4. **結果**: すべてのテストが合格、既存のE2Eテストも正常動作

#### 実装済み（2025年1月9日完了）
- ✅ PMAIフレームが `$TARGET_REPO/requirements.yml` を読むように修正完了
  - 環境変数TARGET_REPOが設定されている場合、そのパスのrequirements.ymlを読む
  - 存在しない場合はエラーメッセージを表示して停止する仕様に変更
- ✅ busd.pyが環境変数TARGET_REPOを子プロセスに引き継ぐため、PMAIは自動的にターゲットリポジトリを認識
- ✅ 子エージェントへの環境変数設定（PATH、ROOT、TASK_ID、TASK_GOAL）
- ✅ tmux send-keysの段階的実行によるClaude起動問題の解決

#### 動作確認結果（2025年1月9日）
- ✅ PMAIが正しくtest_repositoryのrequirements.ymlを読み込み、2つの子エージェントをspawn
- ✅ 子エージェントがタスクを実行（T001: hello.txt作成、T002: index.html作成）
- ✅ busctl postによる進捗報告（一部成功）
- ❌ 一部のpostメッセージでJSONパースエラーが発生（JSONエスケープの問題）

#### 今後の検討事項
- busctl spawn でTARGET_REPO情報を明示的に渡す仕組み（現在は環境変数経由で十分機能）
- busctlのJSONエスケープ処理の改善（特殊文字を含むメッセージへの対応）

### 発見された技術的課題（2025年1月9日追記）

1. **busctlのJSONエスケープ問題**
   - 症状：`busctl post --data '{"msg": "メッセージ"}'`で特殊文字が含まれるとJSONが壊れる
   - 原因：busctlスクリプト内で`"data":$D`と直接展開しているため
   - 影響：子エージェントから親エージェントへの完了通知が届かない
   - 対処：問題のファイルは手動で削除（`rm .ai-app-studio/mbox/pmai/in/*.json`）
   
2. **tmux send-keysの制約**
   - `C-m`が効かない環境があり、`Enter`を使用する必要がある
   - 複雑なコマンドは段階的に送信する方が確実
   - クォーティングの問題を避けるため、シンプルなコマンドに分割

3. **環境変数の引き継ぎ**
   - tmuxペイン内は最小限の環境なので、明示的な設定が必要
   - claudeコマンドのPATH設定（`$HOME/bin:$HOME/.local/bin`）が重要
   - ROOTとTASK_IDの設定により、busctlコマンドが正しく動作