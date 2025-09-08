#!/bin/bash
# AI App Studio Web Client 起動スクリプト

# プロジェクトディレクトリの設定
if [ -z "$TARGET_REPO" ]; then
    echo "環境変数 TARGET_REPO が設定されていません。現在のディレクトリを使用します。"
    export TARGET_REPO=$(pwd)
fi

echo "AI App Studio Web Client を起動しています..."
echo "監視対象プロジェクト: $TARGET_REPO"
echo ""
echo "サーバーは http://localhost:8000 で起動します"
echo ""
echo "終了するには Ctrl+C を押してください"
echo ""

# FastAPIサーバーを起動
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload