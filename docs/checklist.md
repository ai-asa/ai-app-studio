# 開発チェックリスト - AIエージェントオーケストレーションシステム

## リファクタリング完了 (2025-09-05)
- ✅ 不要なファイル・ディレクトリを削除（discover-T*, logs, mbox, work, state）
- ✅ テスト用に作成された不要なgitブランチを削除（feat/T001〜T007）
- ✅ Pythonキャッシュファイルを削除し.gitignoreを更新
- ✅ 重複テストファイルを整理・統合
- ✅ busd.pyのリファクタリング（マジックナンバー定数化、長いメソッド分割）
- ✅ busctl.pyの機能追加（環境変数サポート、--cwdパラメータ）
- ✅ サブディレクトリ方式のテストを削除（設計に合わせて並列ディレクトリ方式に統一）
- ✅ 全22個のユニットテストが成功

## 概要
AIエージェントオーケストレーションシステムの実装チェックリスト。
- v0.9 (MVP-of-MVP): 基本的な2層構造実装 ✅
- v1.0 (Unit-based Hierarchical System): ユニットベース階層型システム 🚧

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

### worktree配置の最終修正完了（2025年9月5日 再修正）
1. **git worktreeの本来の使い方に基づく修正**
   - サブディレクトリ方式（`~/repo/test-project/T001`）から
   - 並列ディレクトリ方式（`~/repo/test-project-T001`）に戻す
   
2. **実装内容（TDDアプローチ）**
   - `get_worktree_path`関数を修正：TARGET_REPOの親ディレクトリに並列作成
   - 新しいテスト`test_busd_parallel_worktree.py`を作成
   - worktreeがメインリポジトリから完全に隔離されることを確認

3. **理由**
   - worktreeはメインリポジトリ外に作成するのが正しい使い方
   - サブディレクトリ方式では、worktreeがmainブランチにコミットされてしまう
   - 並列ディレクトリ方式により真の隔離を実現

### worktree並列ディレクトリ方式への再修正完了（2025年9月5日 最終版）
1. **問題の発見**
   - git worktreeの正しい使い方を確認
   - サブディレクトリ方式では、worktreeがmainブランチにコミットされてしまう問題が判明
   - worktreeは本来、メインリポジトリの外部に独立して作成すべき

2. **TDDアプローチによる修正**
   - 新しいテスト`test_busd_parallel_worktree.py`を作成（Red）
   - `get_worktree_path`関数を並列ディレクトリ方式に修正（Green）
   - 関連ドキュメント（design.md、checklist.md）を更新
   - 統合テストも修正し、すべて成功を確認

3. **最終的な動作**
   - worktreeは`TARGET_REPO`の親ディレクトリに`{repo-name}-{task-id}`形式で作成
   - 各worktreeは完全に独立し、メインリポジトリから隔離される
   - git本来の使い方に準拠した正しい実装

### 実装済み機能（2025年9月6日追加）

#### 統一ユニットシステムの実装
- ✅ 統一フレーム（`/frames/unit/CLAUDE.md`）作成完了
- ✅ 旧フレーム（pmai/impl）削除完了
- ✅ 詳細な実装手順と判断基準を記載
- ✅ TDD実装の具体例を追加
- ✅ エラー処理とトラブルシューティングガイド追加

#### 環境変数サポート
- ✅ busctl spawn --envオプション追加
- ✅ busdでの環境変数処理実装
- ✅ tmuxペイン内への環境変数伝達

### 設計変更（2025年9月6日）

#### ユーザーインターフェースの簡素化
- ✅ 設計ドキュメント（v1.1）に更新
- ✔️ ユーザーの操作を最小限に：
  - `cd /path/to/project`
  - `vim requirements.yml`
  - `busctl spawn` （引数不要）

#### 自動化の徹底
- ✔️ UNIT_IDの自動生成（root → root-api → root-api-users）
- ✔️ requirements.ymlの固定位置（./requirements.yml）
- ✔️ 環境変数の自動設定（busdが処理）

#### タスク管理の改善
- ✔️ task-breakdown.yml（タスク分解リスト）
- ✔️ children-status.yml（子の状態追跡）
- ✔️ scoped-requirements.yml（親からの要件）

### 次回作業内容（優先順）※更新版

#### Phase 1: システムの簡素化（最優先）
1. **busctl spawnコマンドの簡素化**
   - `--task`, `--goal` パラメータ削除
   - UNIT_IDの自動生成機能
   - 環境変数の自動設定

2. **busdの更新**
   - requirements.ymlの自動検出（./requirements.yml固定）
   - UNIT_IDの自動生成ロジック
   - 環境変数の自動設定機能

3. **CLAUDE.mdの簡素化**
   - 必要最小限の指示のみに絞る
   - 具体例を別ファイルに移動
   - 明確な判断フローの提供

#### Phase 2: タスク管理機能
1. **タスク管理ファイルの実装**
   - task-breakdown.ymlの作成・読み込み
   - children-status.ymlの自動更新
   - scoped-requirements.ymlの生成

2. **親子間通信の簡素化**
   - 子の状態はファイル監視で確認
   - 緊急通知のみsend-keys方式

#### Phase 3: 実際の統合テスト
1. **簡単なテストケース**
   - 「Hello World API」の実装
   - 2階層のユニット動作確認
   - 自動化の検証

2. **デモシナリオ**
   - シンプルなWebアプリの開発
   - tmuxでの可視化確認
   
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

---

## Phase 2: ユニットベース階層型システム実装 (v1.1 - 簡素化版)

### 1. 統一フレームの作成
- ✅ `/frames/unit/CLAUDE.md` - 統一ユニットフレームの作成完了
  - ✅ 起動時のコンテキスト読み込み処理
  - ✅ タスク分解可能性の判断ロジック
  - ✅ 親としての動作（子ユニット生成・監視・待機）
  - ✅ 実装者としての動作（TDD実装）
  - ✅ PR作成・マージ処理
  - ✅ 上流への報告処理
  - [x] CLAUDE.mdの簡素化（コンテキスト圧迫を避ける）✅ 完了

### 2. busctlの簡素化
- ✅ 環境変数設定のサポート
  - ✅ `--env` オプションの追加完了
  - ✅ 複数の環境変数を設定可能
- [x] パラメータの削除 ✅ 完了
  - [x] `--task`, `--goal` パラメータを削除 ✅ 完了
  - [x] `busctl spawn` のみで動作するように更新 ✅ 完了

### 3. busdの自動化
#### 3.1 ユニット管理の簡素化
- ✅ 環境変数の自動設定機能
- ✅ ユニット用ファイルの自動管理
  - ✅ .parent_unitファイル作成（子ユニット）
  - ✅ task-breakdown.yml初期化（親ユニット）
  - ✅ children-status.yml初期化（親ユニット）
- ✅ プロジェクトファイルの自動コピー
  - ✅ CLAUDE.md、.env.local、.claudeディレクトリ
- [x] UNIT_IDの自動生成 ✅ 完了
  - [x] root → root-api → root-api-users 形式 ✅ 完了
  - [x] 親子関係の自動追跡 ✅ 完了
- [x] requirements.ymlの自動検出 ✅ 完了
  - [x] カレントディレクトリの./requirements.ymlを確認 ✅ 完了
  - [x] ない場合はエラーを発生 ✅ 完了

#### 3.2 双方向通信の実現
- [x] 親ユニットへのsend-keys通知機能 ✅ 完了
  - [x] notify_parent_unit関数の実装 ✅ 完了
  - [x] 通知フォーマット `[CHILD:unit-id] Status: status, Message: message` ✅ 完了
  - [x] shlex.quoteによる安全なエスケープ処理 ✅ 完了
  - [x] -lオプションでリテラル送信 ✅ 完了
  - [x] 連続通知時の0.1秒待機 ✅ 完了
- [x] handle_post拡張 ✅ 完了
  - [x] result/child_completedメッセージ検出 ✅ 完了
  - [x] 親ユニットIDの解決機能 ✅ 完了
  - [x] 親paneへの自動通知 ✅ 完了
- [x] エラーハンドリング ✅ 完了
  - [x] 親paneが見つからない場合の処理 ✅ 完了
  - [ ] 送信失敗時のリトライ機能（オプション）
- [x] 統一フレームへの通知受信処理の記載 ✅ 完了
  - [ ] 通知フォーマットの説明
  - [ ] 子の状態管理方法
  - [ ] すべての子完了時の処理フロー

#### 3.3 新メッセージタイプの処理
- [ ] `task_decomposed` ハンドラ
- [ ] `child_completed` ハンドラ
- [ ] `pr_created`, `merge_request` ハンドラ
- [ ] `conflict_found` ハンドラ
- [ ] `query`, `response` ハンドラ

### 4. ブランチ・worktree管理の拡張
- [ ] 階層的ブランチ名の生成
  - [ ] `feat/root-api-users` 形式
  - [ ] 親ブランチからの派生
- [ ] worktree名の階層化
  - [ ] `target-repo-root-api-users` 形式

### 5. 要件定義管理機能
- [ ] 個別要件定義書の作成・管理
  - [ ] `.ai-app-studio/requirements/unit-{id}/` 構造
  - [ ] scoped-requirements.yml テンプレート
- [ ] タスク定義ファイルの標準化
  - [ ] task.json のスキーマ定義

### 6. PR・マージ機能の実装
- [ ] ghコマンドのラッパー機能
  - [ ] PR作成の自動化
  - [ ] 親ブランチの自動判定
- [ ] マージ処理
  - [ ] 子PRの親ブランチへのマージ
  - [ ] マージコミットメッセージの標準化
- [ ] 基本的なコンフリクト検出
  - [ ] マージ試行とエラー検知
  - [ ] 親への通知

### 7. テスト作成
#### 7.1 ユニットテスト
- [ ] 統一フレームのテスト
  - [ ] タスク分解判断のテスト
  - [ ] 環境変数読み込みテスト
- [x] busctl拡張機能のテスト ✅ 完了
- [x] busd拡張機能のテスト ✅ 完了
  - [x] notify_parent_unit関数のテスト ✅ 完了
  - [x] send-keysエスケープ処理のテスト ✅ 完了
- [x] 親子間通信のテスト ✅ 完了
  - [x] 通知フォーマットの検証 ✅ 完了
  - [x] 複数の子からの同時通知テスト ✅ 完了
  - [x] 特殊文字を含むメッセージのテスト ✅ 完了

#### 7.2 統合テスト
- [ ] 3階層のユニット動作テスト
- [ ] 親子間send-keys通信のE2Eテスト
  - [ ] 子の完了通知が親に届く確認
  - [ ] 親が子の状態を正しく管理
  - [ ] すべての子完了後の親の動作
- [ ] PR作成・マージフローのテスト
- [ ] コンフリクト発生時のテスト

#### 7.3 E2Eテスト
- [ ] 実際のリポジトリでの階層的開発フロー
- [ ] 複数ユニットの並列動作
- [ ] 最終的な統合とmainへのマージ

### 8. ドキュメント更新
- [ ] README.mdにユニットベースシステムの説明追加
- [ ] STARTUP_GUIDE.mdの更新
- [ ] サンプルrequirements.ymlの複雑な例追加

### 9. デモシナリオ作成
- [ ] 3階層以上の開発シナリオ
- [ ] コンフリクト解決のデモ
- [ ] tmuxでの可視化最適化

## 実装順序（推奨）

### Phase 2.1: 基盤拡張（1週間目標）
1. 統一フレーム作成（最優先）
2. busctl/busdの基本拡張
3. ユニット管理機能
4. 環境変数による情報伝達

### Phase 2.2: 通信機能（1週間目標）
1. 双方向通信の実装
2. 新メッセージタイプ対応
3. ファイル監視機能
4. 親への通知機能

### Phase 2.3: PR/マージ機能（2週間目標）
1. ghコマンド統合
2. 基本的なマージ機能
3. コンフリクト検出
4. エラーハンドリング

## 成功基準

- [ ] 3階層のユニットが自律的に動作
- [ ] 親ユニットが子の完了を検知して次の行動
- [ ] 各ユニットがPRを作成し、親がマージ
- [ ] 最終的にすべての変更がmainに統合
- [ ] tmuxで階層的な動作が可視化される

## リスクと対策

### 技術的リスク
- **LLMの判断品質**: 明確な判断基準とサンプルの提供
- **無限階層の制御**: 実用的なガイドライン（3-4層推奨）
- **コンフリクト頻発**: 依存関係の明示的管理

### 実装リスク
- **複雑性の増大**: 段階的実装とテスト駆動開発
- **デバッグの困難さ**: 詳細なログとトレーサビリティ
- **パフォーマンス**: 非同期処理と最適化

---

## 次回作業メモ

優先順位：
1. 統一フレーム（unit/CLAUDE.md）の作成 - 最重要
2. busctl の --env オプション追加
3. busd のユニット管理機能追加
4. 基本的な親子間通信のテスト

---

## 本日の進捗（2025-09-05 - 設計簡素化）

### 完了事項

#### 1. 設計ドキュメントの更新（v1.1 - Simplified）
- ✅ docs/design.mdを簡素化版に更新
- ✅ 自動化の徹底（UNIT_ID自動生成、固定requirements.yml位置）
- ✅ 手動パラメータの削除方針を明記

#### 2. CLAUDE.mdの簡素化
- ✅ frames/unit/CLAUDE.md を 550行から107行に削減
- ✅ 詳細例をexamplesディレクトリに分離
  - 01-tdd-example.md: TDD実装の詳細
  - 02-task-breakdown-example.md: タスク分解の例
  - 03-pr-and-merge-example.md: PR作成とマージ
  - 04-error-handling-example.md: エラー処理
- ✅ 必要最小限の指示のみを残し、コンテキスト圧迫を回避

#### 3. busctl.pyの簡素化（部分実装）
- ✅ detect_unit_context()関数の実装
- ✅ --taskと--goalパラメータの削除
- ✅ 自動的なUNIT_ID検出ロジック
- ✅ ユニットテストの作成（test_busctl_simplified.py）

#### 4. busdの簡素化準備
- ✅ test_busd_simplified.pyでテストケース定義
- ✅ 必要な変更点の洗い出し：
  - requirements.yml自動コピー
  - .parent_unitファイル作成
  - タスク管理ファイルの初期化
  - worktreeパスのシンプル化

### 次回優先タスク

#### 1. busd.pyの自動ファイル管理実装（最優先）

handle_spawn関数の修正ポイント：
```python
def handle_spawn(self, message):
    # 1. worktree作成後、requirements.ymlをコピー
    worktree_path = self.ensure_worktree(unit_id, branch)
    shutil.copy(
        Path(env_dict.get('TARGET_REPO')) / 'requirements.yml',
        worktree_path / 'requirements.yml'
    )
    
    # 2. 子ユニットの場合、.parent_unitファイル作成
    if parent_id := env_dict.get('PARENT_UNIT_ID'):
        (worktree_path / '.parent_unit').write_text(parent_id)
        
    # 3. 親ユニットの場合、タスク管理ファイル初期化
    if not parent_id:
        self.init_task_files(worktree_path)
```

#### 2. タスク管理ファイルのサポート
- task-breakdown.ymlの読み込みと子ユニット生成
- children-status.ymlの自動更新
- 子の完了検知と親への通知

#### 3. 統合テスト
- cd → vim requirements.yml → busctl spawn の流れ
- 自動UNIT_ID生成の確認
- 親子関係の正しい追跡

### テスト確認項目
1. **busctl spawn（引数なし）**
   - requirements.ymlの存在確認
   - 自動的にrootユニット作成
   - 環境変数の正しい設定

2. **子ユニット作成**
   - .parent_unitファイルから親を検出
   - UNIT_IDの自動生成（root-api形式）
   - requirements.ymlの自動コピー

3. **エラーケース**
   - requirements.ymlが存在しない
   - 権限がない
   - 既存のworktreeとの競合

### 設計思想の確認
- **ユーザーの手間を最小化**: cd → vim → spawn のみ
- **Claude Codeのコンテキスト節約**: CLAUDE.md簡素化
- **自動化の徹底**: すべての設定を自動検出/生成

## 本日の進捗（2025-09-06 - busd自動ファイル管理実装）

### 完了事項

#### 1. busd.pyの自動ファイル管理機能実装（Phase 2.1）
- ✅ setup_unit_files()関数の実装
  - 子ユニット: .parent_unitファイル作成（親のUNIT_ID記録）
  - 親ユニット: task-breakdown.yml、children-status.yml初期化
- ✅ copy_project_files()関数の実装
  - CLAUDE.mdをworktreeにコピー
  - .env.localをworktreeにコピー
  - .claudeディレクトリをworktreeにコピー
- ✅ requirements.ymlのコピー削除（worktreeが自動的に持つため不要）

#### 2. test_busd_simplified.pyの実装と成功
- ✅ test_spawn_root_unit: 親ユニットのタスク管理ファイル作成確認
- ✅ test_spawn_child_unit: 子ユニットの.parent_unitファイル作成確認
- ✅ test_automatic_file_management: プロジェクトファイルのコピー確認
- ✅ test_task_management_files_templates: YAMLテンプレートの内容確認
- ✅ すべてのテストが成功（tmux pane IDのモック問題も解決）

#### 3. 既存テストの成功確認
- ✅ test_busd_empty_repo.py: 空リポジトリ対応機能の動作確認
- ✅ test_busd_env_support.py: 環境変数サポートの動作確認
- ✅ test_busd_parallel_worktree.py: 並列ディレクトリ方式の動作確認
- ✅ test_busd_worktree.py: worktree基本機能の動作確認
- ✅ ビルドテスト（Python構文チェック）成功

### 実装の技術ポイント
1. **git worktreeの特性を活用**: requirements.ymlは自動的に各worktreeに存在するため、コピー不要
2. **条件分岐による適切なファイル作成**: 親/子ユニットで異なるファイルセット
3. **プロジェクト設定の伝播**: CLAUDE.md、.env.local、.claudeを各worktreeへコピー

### 本日の進捗（2025-09-06 - busctl簡素化と親子間通信実装）

#### 1. busctl spawnコマンドの簡素化実装（引数なし動作）
- ✅ detect_unit_context()関数の改善
  - .parent_unitファイルによる親ユニット検出
  - ディレクトリ名からのタスクID抽出
  - task-breakdown.ymlからのタスクID検証
- ✅ 階層的UNIT_ID生成（root → root-api → root-api-users）
- ✅ yamlモジュールを使用したtask-breakdown.yml読み込み機能
- ✅ test_busctl_simplified.pyに新テストケース追加（全6テスト成功）

#### 2. UNIT_IDの完全自動生成機能の実装
- ✅ ユーザー操作を最小限に簡素化
  ```bash
  cd /path/to/project
  vim requirements.yml
  busctl spawn  # 引数なしで自動的に全てを検出
  ```
- ✅ コンテキストベースの自動判定
  - .parent_unitがない → "root"
  - .parent_unitがある → "{parent_id}-{task_id}"
- ✅ エラーハンドリングとフォールバック機能

#### 3. 親子間send-keys通信の実装
- ✅ notify_parent_unit関数の実装
  - 通知フォーマット: `[CHILD:unit-id] Status: status, Message: message`
  - shlex.quoteによる安全なエスケープ処理
  - -lオプションでリテラル送信
  - 連続通知時の0.1秒待機
- ✅ handle_post拡張
  - resultメッセージ時に親へ自動通知
  - task情報にenv保存（PARENT_UNIT_ID参照用）
  - エラー時はstatus: errorで通知
- ✅ test_busd_parent_child_comm.pyによる包括的テスト（6テスト成功）

#### 4. 実装の技術ポイント
- **TDDアプローチの徹底**: Red → Green → Refactor
- **定数化によるメンテナンス性向上**: NOTIFICATION_FORMAT, NOTIFICATION_DELAY
- **特殊文字対応**: 改行、引用符、Unicode絵文字を含むメッセージも安全に送信

### 残タスク（Phase 2）
- [x] busctl spawnの完全な簡素化（引数なしで動作）✅ 完了
- [x] UNIT_IDの完全自動生成 ✅ 完了
- [x] 親子間通信の実装（send-keys方式）✅ 完了
- [x] タスク管理ファイルの活用（子ユニットの状態追跡）✅ 完了

### 本日の進捗（2025-09-09 - children-status.yml自動更新機能）

#### 1. children-status.yml自動更新機能の実装（TDD）
- ✅ test_busd_children_status.pyの作成
  - 4つの包括的なテストケース
  - 正常系、エラー系、複数子ユニット、既存エントリ更新
- ✅ busd.pyにupdate_children_status関数を追加
  - YAMLファイルの読み書き
  - 既存エントリの更新、新規エントリの追加
  - エラーハンドリング
- ✅ handle_postでresultメッセージ時に自動呼び出し
  - 親ユニットへの通知と同時に状態ファイルも更新
  - error_messageのサポート（エラー時）

#### 2. 実装の技術ポイント
- **TDDアプローチ**: Red（失敗するテスト）→ Green（最小限の実装）→ 完了
- **YAMLモジュールの活用**: 安全なファイル読み書き
- **worktree_pathの保存**: handle_spawnでタスク情報に追加
- **後方互換性の確保**: cwdフィールドからのフォールバック

#### 3. 動作確認
- ✅ 全テスト成功（17個のbusd関連テスト）
- ✅ 構文チェック成功
- ✅ 既存機能への影響なし

### 本日の進捗（2025-01-10 - busctl spawn --from-breakdown機能実装）

#### 1. busctl spawn --from-breakdown機能の実装（完了）
**問題**: ルートユニットが子ユニットを生成できない問題を解決

**実装内容**:
- ✅ busctl.pyに`--from-breakdown`オプションを追加
- ✅ task-breakdown.ymlを読み込んでパースする機能
- ✅ 各タスクに対して自動的に子ユニットをspawnする処理
  - UNIT_ID: `{parent_id}-{task_id}` 形式で生成
  - PARENT_UNIT_ID: 現在のユニットIDを設定
- ✅ **重複回避方式の実装**:
  - children-status.ymlを読み込んで既存の子ユニットIDをチェック
  - busctl spawn --from-breakdownの処理フロー：
    1. task-breakdown.ymlから全タスクを読み込み
    2. children-status.ymlから既存の子ユニット一覧を取得
    3. 未生成のタスクのみをspawn
  - 注意: task-breakdown.ymlのstatusはタスクの完了状態管理用（spawn状態とは別）
- ✅ テストの作成（test_busctl_from_breakdown.py）
  - 5つの包括的なテストケース作成
  - TDDアプローチで実装（Red→Green→Refactor）
  - すべてのテストが成功

**使用方法**:
```bash
# ルートユニットのworktreeで実行
busctl spawn --from-breakdown

# task-breakdown.ymlから自動的に子ユニットを生成
# 例: backend, frontend, infrastructure → root-backend, root-frontend, root-infrastructure
```

#### 2. frames/root/CLAUDE.mdの詳細更新（完了）
- ✅ ステップ4（子ユニット生成）の全面改訂：
  ```bash
  # 旧: busctl spawn
  # 新: busctl spawn --from-breakdown
  ```
  - コマンドの説明：task-breakdown.ymlから自動的に子ユニットを生成
  - children-status.ymlで重複チェックされることの説明
- ✅ エラーや追加要件時のコマンドも更新：
  - `busctl spawn --from-breakdown` （既存の子は再生成されない）

#### 3. frames/unit/CLAUDE.mdの更新（完了）
- ✅ 親ユニットとして動作する場合の子ユニット生成コマンドを更新
  - 2箇所の`busctl spawn`を`busctl spawn --from-breakdown`に変更
- ✅ 新しいタスク追加時のコマンドも更新

#### 4. test_busctl.pyの修正（完了）
- ✅ 古いspawnテストケースを新形式に修正
  - `test_spawn_command_basic` - requirements.ymlを作成してからspawnを実行する形式に変更
  - `test_spawn_command_with_branch` → `test_spawn_command_with_env` - 環境変数のテストに変更
  - `test_missing_required_arguments` - requirements.ymlがない場合のエラーテストに変更
- ✅ すべてのテストが成功（9/9）

### 本日の進捗（2025-01-10 - CLAUDE.mdドキュメント改善）

#### frames/root/CLAUDE.mdとframes/unit/CLAUDE.mdの改善（完了）
- ✅ ステップ3（タスク分解）の更新：
  - 初期作成時はすべてのタスクを`status: pending`にする明確な指示を追加
  - statusの意味を説明（pending=未完了、completed=完了）
- ✅ ステップ5（子からの報告を待つ）の更新：
  - 報告受信時：該当タスクのstatusを`completed`に更新する手順を追加
  - 追加タスクが必要な場合：新タスクを`status: pending`で追加して再度spawn
- ✅ statusフィールドの使い方を明確化：
  - `status: pending` = タスク未完了（子がまだ作業中または未生成）
  - `status: completed` = タスクが完了（子から完了報告を受信済み）
  - spawn状態はchildren-status.ymlで管理されるため、statusとは独立

#### ドキュメントの簡潔化（完了）
- ✅ catコマンドをすべて削除（Claude CodeのReadツールを活用）
- ✅ 「現在の内容を確認」などの自明な手順を削除
- ✅ Read指示の明示的な記載を削除（Claude Codeが自分で判断）
- ✅ デバッグ用コマンドセクションを「重要なファイル」に変更
- ✅ `{親のID}` → `${PARENT_UNIT_ID}`（環境変数を活用）

### 次回作業候補（優先順）

#### 実装上の重要な設計判断
- **ファイルの役割分担を維持**：
  - task-breakdown.yml = タスクの完了状態管理（親が更新）
  - children-status.yml = 子ユニットの実行状態管理（busdが更新）
- **spawn重複回避はchildren-status.ymlで判定**：
  - 理由: spawn状態とタスク完了状態は別概念
  - busctl spawn --from-breakdownがchildren-status.ymlを読み込む
- **statusフィールドは2値のまま**：
  - pending = タスク未完了
  - completed = タスク完了
  - "spawned"のような中間状態は追加しない

#### その他の即座に必要な修正
- [x] frames/root/CLAUDE.mdの作成（ルートユニット専用）✅ 完了
  - ルートは必ずタスク分解する
  - 「requirements.ymlを読んでタスク分解」が初期タスク
- [x] frames/unit/CLAUDE.mdの再修正 ✅ 完了
  - フロー中心の明確な説明
  - 動的タスク追加の説明を含む
- [x] busd.pyの修正 ✅ 完了（2025-09-09）
  - [x] copy_project_files関数の修正 ✅ 完了
    - AI App Studioのルートディレクトリからframesディレクトリを参照
    - UNIT_ID="root"の場合はframes/root/CLAUDE.mdを使用
    - それ以外はframes/unit/CLAUDE.mdを使用
  - [x] handle_spawn関数の修正 ✅ 完了
    - envからUNIT_IDを取得してcopy_project_filesに渡す
  - [x] _send_initial_message関数の簡素化 ✅ 完了
    - frameがNoneまたは空の場合は何もしない
    - CLAUDE.mdが明確なので追加の初期メッセージは不要

#### 将来的な機能追加
- [ ] PR作成・マージ機能の実装（ghコマンドとの統合）
- [ ] コンフリクト検出・解決機能
- [ ] 3階層のユニット動作テスト
- [ ] task-breakdown.ymlからの自動子ユニット生成（busctl spawn --auto）

### 本日の進捗（2025-09-09 - CLAUDE.mdとdesign.md修正、フロー中心の改善）

#### 1. frames/unit/CLAUDE.mdの全面的な修正（第1弾）
- ✅ TARGET_REPOの確認を削除（混乱の原因となるため）
- ✅ 親ユニットのフローを明確化
  - タスク分解 → チェックリスト作成 → 子生成 → 報告受信 → 更新 → 親へ報告
- ✅ 受動的な通知受信を明記（watchやgrepは使用しない）
- ✅ TDD制限の詳細を追加
  - 1機能・2ファイル制限を明記
  - Red-Green-Refactorサイクルの説明
- ✅ task-breakdown.ymlの役割を明確化（親が作成・管理するチェックリスト）

#### 2. docs/design.md の更新
- ✅ task-breakdown.ymlの役割明確化
  - 親が作成するタスクチェックリスト
  - statusフィールドで進捗管理（pending → completed）
- ✅ children-status.ymlの役割明確化
  - busdが自動更新する状態追跡ファイル
  - 親は参照のみ、更新はbusd
- ✅ 監視方法の修正
  - 能動的な監視（watchコマンド等）を削除
  - 受動的な通知受信（send-keys）に統一

#### 3. frames/unit/CLAUDE.mdの再修正（第2弾 - フロー中心）
- ✅ 冒頭で「あなたは何者か」を明確に説明
- ✅ 全体の流れを順番に記載（ステップ1→2→3→フロー分岐）
- ✅ 判断基準を具体化（実装可能/分解必要）
- ✅ 動的タスク追加の明記
- ✅ PR作成後のマージ処理を追加
- ✅ コンフリクト検知と対処を追加

#### 4. frames/root/CLAUDE.mdの新規作成
- ✅ ルートユニット専用の指示書
- ✅ 「requirements.ymlを読んでタスク分解」が初期タスク
- ✅ 必ずタスク分解することを明記（実装しない）
- ✅ プロジェクト全体の大タスクへの分解例を記載

#### 5. 設計の一貫性向上
- ✅ 親ユニットと子ユニット間の責任分担を明確化
- ✅ ファイルの役割と更新責任者を明確化
- ✅ Claude Codeが理解しやすいフローに整理

### 本日の進捗（2025-09-09 - busd.py フレーム選択機能実装）

#### 1. TDDアプローチによるbusd.py修正
- ✅ test_busd_frame_selection.pyの作成
  - copy_project_filesのunit_id対応テスト
  - handle_spawnの自動フレーム選択テスト
  - _send_initial_messageの簡素化テスト
- ✅ Red-Green-Refactorサイクル完了
  - Red: テストが失敗することを確認
  - Green: 最小限の実装でテストを通す
  - Refactor: 今回は最小限の変更のみ

#### 2. busd.pyの実装内容
- ✅ copy_project_files関数の修正
  - unit_idパラメータを追加
  - UNIT_ID="root"の場合はframes/root/CLAUDE.mdを使用
  - その他の場合はframes/unit/CLAUDE.mdを使用
- ✅ handle_spawn関数の修正
  - envからUNIT_IDを取得してcopy_project_filesに渡す
- ✅ _send_initial_message関数の簡素化
  - frameが指定されていない場合は何もしない
  - CLAUDE.mdが明確なので追加の初期メッセージは不要

#### 3. テスト結果
- ✅ 新しいテスト（test_busd_frame_selection.py）: 全5テスト成功
- ✅ 既存テストの確認: リグレッションなし
- ✅ ビルドテスト: Python構文チェック成功

### 本日の進捗（2025-09-09 - 統一ユニットシステムの修正）

#### 1. 統一ユニットシステムの問題修正
- ✅ ルートユニットが右ペインに配置される問題を修正
  - _determine_target_pane関数で"root"も左上ペインに配置するように変更
- ✅ 初期メッセージが送信されない問題を修正
  - _send_initial_message関数でframeがNoneでもCLAUDE.mdを読む指示を送信
  - ルートユニット: "Read CLAUDE.md... Your initial task is to read requirements.yml..."
  - 子ユニット: "You are unit {task_id}. Read CLAUDE.md..."

#### 2. ドキュメント更新
- ✅ STARTUP_GUIDE.mdにGitHub認証設定を追加
  - Personal Access Token作成手順
  - .env.localへの設定方法
  - ghコマンドによるログイン方法
- ✅ 統一ユニットシステムの簡素化された使い方を追加
  - cd → vim requirements.yml → busctl spawn の3ステップ
  - 自動的なタスク分解と並列実行の説明

#### 3. テスト更新
- ✅ test_busd_unified_system_fixes.pyを作成
- ✅ test_busd_frame_selection.pyの修正（frameがNoneの場合の挙動変更に対応）
- ✅ 全テスト成功確認

### 本日の進捗（2025-09-09 - 追加修正）

#### 1. 初期メッセージの日本語化
- ✅ _send_initial_message関数の初期メッセージを日本語に変更
  - ルートユニット: "CLAUDE.mdを読んで指示に従ってください。最初のタスクはrequirements.ymlを読んでサブタスクに分解することです。"
  - 子ユニット: "あなたはユニット {task_id} です。CLAUDE.mdを読んで指示に従ってください。"

#### 2. 初期メッセージ送信問題の修正
- ✅ busctl.pyのframeパラメータを空文字列に変更
  - 問題: busctl.pyが常に`frame: "frames/unit/CLAUDE.md"`を送信していた
  - 修正: `"frame": ""` に変更してbusdの初期メッセージ送信を有効化

#### 3. requirements.ymlコピー問題の修正
- ✅ copy_project_files関数にrequirements.ymlコピー処理を追加
  - 問題: git worktreeは未コミットファイルを含まない
  - 修正: requirements.ymlを明示的にworktreeにコピー

#### 4. サンプル要件定義の作成
- ✅ requirements.yml.sampleを「シンプルメモアプリ」に更新
  - 5つのタスクに分解される実用的な例
  - HTML/CSS/JavaScriptのみで実装可能

### 本日の進捗（2025-01-10 - busctl spawn --from-breakdown 問題修正）

#### 1. 問題の発見と調査
- ✅ ルートユニットが`busctl spawn --from-breakdown`を実行しても子ユニットが生成されない問題を確認
- ✅ デバッグログをbusctl.pyに追加して実際のメッセージ投函を確認
- ✅ デバッグログをbusd.pyに追加してメッセージ処理フローを追跡

#### 2. 根本原因の特定
- ✅ **busctlとbusdが異なるディレクトリを使用していたことが原因**
  - busd: `TARGET_REPO/.ai-app-studio/` を監視
  - busctl: worktree内で実行されると `worktree/.ai-app-studio/` に投函
  - 結果: メッセージが届かない

#### 3. 修正の実装
- ✅ busd.pyの`_execute_in_pane`関数でBUSCTL_ROOT環境変数を設定
  ```python
  sh(f"tmux send-keys -t {target_pane} 'export BUSCTL_ROOT=\"{str(ROOT)}\"' Enter")
  ```
- ✅ これにより全てのユニットのbusctlが同じディレクトリ（busdのROOT）を使用するように

#### 4. 動作確認
- ✅ テストスクリプトで修正を検証
- ✅ 実際にルートユニットから子ユニットが正しく生成されることを確認

---

## Phase 3: Web クライアント実装

### 1. プロジェクト構造の作成
- [ ] `/web-client/` ディレクトリ作成
- [ ] `/web-client/backend/` 構造作成
- [ ] `/web-client/frontend/` 構造作成
- [ ] `requirements.txt` (FastAPI, websockets, watchdog)
- [ ] `package.json` (React, WebSocket)

### 2. バックエンド実装（FastAPI）
#### 2.1 基本セットアップ
- [ ] `main.py` - FastAPIアプリケーション基本構造
- [ ] CORS設定（フロントエンドからのアクセス許可）
- [ ] 静的ファイル配信設定

#### 2.2 データモデル
- [ ] `models.py` - Taskモデル定義
  - [ ] TaskStatus enum (pending, completed, error)
  - [ ] Task dataclass (id, status, children, message)
  - [ ] TaskHierarchy モデル

#### 2.3 API実装
- [ ] `GET /api/tasks` - タスク階層取得
  - [ ] tasks.jsonの読み込み
  - [ ] 各worktreeからchildren情報取得
  - [ ] 階層構造の構築
- [ ] `GET /api/logs/{task_id}` - ログ取得
  - [ ] logs/raw/{task_id}.rawの読み込み
  - [ ] 末尾N行のみ返す機能
  - [ ] ファイルが存在しない場合の処理

#### 2.4 WebSocket実装
- [ ] WebSocketエンドポイント `/ws`
- [ ] クライアント管理（接続/切断）
- [ ] メッセージブロードキャスト機能

#### 2.5 ファイル監視
- [ ] `monitor.py` - watchdogでのファイル監視
  - [ ] bus.jsonl監視 → task_updateイベント
  - [ ] tasks.json監視 → task_addedイベント
  - [ ] 変更をWebSocketで通知

### 3. フロントエンド実装（React）
#### 3.1 基本セットアップ
- [ ] `index.html` - 基本HTML構造
- [ ] `app.js` - Reactアプリケーション
- [ ] `style.css` - 最小限のスタイル（Tailwind CDN）

#### 3.2 コンポーネント実装
- [ ] `App` - メインコンポーネント
  - [ ] タスク階層の状態管理
  - [ ] 選択中のタスクID管理
- [ ] `TaskTree` - タスク階層表示
  - [ ] インデント表示
  - [ ] ステータスアイコン（⏳✅❌）
  - [ ] クリックイベント処理
- [ ] `LogViewer` - ログ表示
  - [ ] 選択されたタスクのログ表示
  - [ ] 自動スクロール
  - [ ] リアルタイム更新

#### 3.3 WebSocket統合
- [ ] WebSocket接続管理
- [ ] 再接続処理
- [ ] メッセージ受信時の状態更新
  - [ ] task_updateの処理
  - [ ] task_addedの処理

### 4. 統合テスト
- [ ] バックエンド単体テスト
  - [ ] API エンドポイントテスト
  - [ ] WebSocket接続テスト
- [ ] フロントエンド動作確認
  - [ ] 初期表示
  - [ ] クリック動作
  - [ ] リアルタイム更新
- [ ] E2Eテスト
  - [ ] busdと連携した動作確認
  - [ ] 実際のタスク実行時の表示確認

### 5. ドキュメント・デプロイ
- [ ] `web-client/README.md` 作成
  - [ ] セットアップ手順
  - [ ] 使用方法
- [ ] 起動スクリプト作成
  - [ ] バックエンド起動
  - [ ] フロントエンド起動
- [ ] systemdサービス定義（オプション）

### 実装優先度
1. **Phase 1**: バックエンドAPI基本実装（タスク取得、ログ取得）
2. **Phase 2**: フロントエンド基本表示（静的な階層表示）
3. **Phase 3**: WebSocketによるリアルタイム更新
4. **Phase 4**: UI改善とエラーハンドリング