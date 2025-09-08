"""
FastAPI main application for AI App Studio Web Client.
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import logging
import json
from typing import Set
import asyncio

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPIアプリケーションの作成
app = FastAPI(
    title="AI App Studio Monitor",
    description="Real-time monitoring for AI App Studio",
    version="1.0.0"
)

# WebSocket接続管理
connected_clients: Set[WebSocket] = set()

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開発用に全許可
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ヘルスチェックエンドポイント
@app.get("/health")
async def health_check():
    """システムの健全性を確認"""
    return {"status": "healthy"}

# APIルーターの登録
from .api import router as api_router
app.include_router(api_router, prefix="/api")

# フロントエンドの静的ファイル配信
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")
    
    # ルートパスでindex.htmlを返す
    @app.get("/")
    async def read_index():
        index_path = frontend_path / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        else:
            # index.htmlがまだない場合のフォールバック
            return {"message": "Frontend not yet implemented"}
else:
    # フロントエンドディレクトリがない場合のフォールバック
    @app.get("/")
    async def read_root():
        return {"message": "AI App Studio Web Client API"}

# WebSocketエンドポイント
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket接続を管理"""
    await websocket.accept()
    connected_clients.add(websocket)
    
    # 接続確認メッセージを送信
    await websocket.send_json({
        "type": "connection",
        "status": "connected"
    })
    
    try:
        while True:
            # クライアントからのメッセージを待機
            # （今回は主にサーバー→クライアントの通信なので、単に接続を維持）
            data = await websocket.receive_text()
            # ping/pongなどの処理が必要な場合はここに追加
    except WebSocketDisconnect:
        # クライアント切断時の処理
        connected_clients.remove(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        # その他のエラー
        logger.error(f"WebSocket error: {e}")
        if websocket in connected_clients:
            connected_clients.remove(websocket)

# メッセージブロードキャスト関数
async def broadcast_message(message: dict):
    """接続中の全クライアントにメッセージを送信"""
    disconnected_clients = set()
    
    for client in connected_clients:
        try:
            await client.send_json(message)
        except Exception as e:
            logger.error(f"Error broadcasting to client: {e}")
            disconnected_clients.add(client)
    
    # 切断されたクライアントを削除
    for client in disconnected_clients:
        connected_clients.remove(client)

# アプリケーション状態に関数を追加（テスト用）
app.state.broadcast_message = broadcast_message

# ファイル監視タスク
file_monitor_task = None

# 開発用: 起動時のログとファイル監視開始
@app.on_event("startup")
async def startup_event():
    logger.info("AI App Studio Web Client started")
    logger.info(f"Frontend path: {frontend_path}")
    logger.info(f"Frontend exists: {frontend_path.exists()}")
    
    # ファイル監視を開始
    try:
        from .monitor import FileMonitor
        import os
        
        # プロジェクトディレクトリを環境変数から取得（デフォルトは現在のディレクトリ）
        project_dir = os.environ.get("TARGET_REPO", os.getcwd())
        logger.info(f"Starting file monitor for project: {project_dir}")
        
        monitor = FileMonitor(project_dir)
        global file_monitor_task
        file_monitor_task = asyncio.create_task(monitor.start_monitoring(broadcast_message))
        logger.info("File monitor started successfully")
    except Exception as e:
        logger.error(f"Failed to start file monitor: {e}")

# シャットダウン時の処理
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("AI App Studio Web Client shutting down")
    
    # ファイル監視タスクを停止
    if file_monitor_task and not file_monitor_task.done():
        file_monitor_task.cancel()
        try:
            await file_monitor_task
        except asyncio.CancelledError:
            pass
        logger.info("File monitor stopped")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)