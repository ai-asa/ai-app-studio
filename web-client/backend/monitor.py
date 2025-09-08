"""
File monitoring module for AI App Studio Web Client.
Monitors bus.jsonl and tasks.json for changes and sends WebSocket notifications.
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Callable, Set
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
import queue

from backend.models import WebSocketMessage, MessageType, TaskStatus

logger = logging.getLogger(__name__)


class FileChangeHandler(FileSystemEventHandler):
    """ファイル変更を検出するハンドラ"""
    
    def __init__(self, change_queue: queue.Queue):
        self.change_queue = change_queue
        self.bus_jsonl_name = "bus.jsonl"
        self.tasks_json_name = "tasks.json"
    
    def on_modified(self, event):
        """ファイル変更イベントを処理"""
        if event.is_directory:
            return
            
        filename = Path(event.src_path).name
        
        if filename == self.bus_jsonl_name:
            logger.info("Detected bus.jsonl change")
            self.change_queue.put(("bus", filename))
        elif filename == self.tasks_json_name:
            logger.info("Detected tasks.json change")
            self.change_queue.put(("tasks", filename))


class FileMonitor:
    """AI App Studioのファイルを監視してWebSocket通知を送信"""
    
    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.ai_app_dir = self.project_dir / ".ai-app-studio"
        self.bus_jsonl_path = self.ai_app_dir / "logs" / "bus.jsonl"
        self.tasks_json_path = self.ai_app_dir / "state" / "tasks.json"
        
        # 既知のタスクIDを追跡（新規タスク検出用）
        self.known_tasks: Set[str] = set()
        
        # bus.jsonlの最終読み込み位置
        self.bus_last_position = 0
        
        # 初期化時に既存のタスクを記録
        if self.tasks_json_path.exists():
            try:
                with open(self.tasks_json_path) as f:
                    tasks = json.load(f)
                    self.known_tasks = set(tasks.keys())
            except Exception as e:
                logger.error(f"Error loading initial tasks: {e}")
        
        # bus.jsonlの現在の位置を記録
        if self.bus_jsonl_path.exists():
            self.bus_last_position = self.bus_jsonl_path.stat().st_size
    
    def parse_bus_message(self, bus_line: dict) -> Optional[WebSocketMessage]:
        """bus.jsonlの行をWebSocketメッセージに変換"""
        msg_type = bus_line.get("type")
        task_id = bus_line.get("task", "")
        data = bus_line.get("data", {})
        
        if msg_type == "result":
            # resultメッセージをtask_updateに変換
            is_error = data.get("is_error", False)
            status = "error" if is_error else "completed"
            message = data.get("message", "")
            
            return WebSocketMessage(
                type=MessageType.TASK_UPDATE,
                task_id=task_id,
                status=status,
                message=message
            )
        elif msg_type == "log":
            # 進捗ログをtask_updateに変換
            return WebSocketMessage(
                type=MessageType.TASK_UPDATE,
                task_id=task_id,
                status="running",
                message=data.get("message", "")
            )
        
        return None
    
    def detect_new_tasks(self, tasks: Dict[str, dict]) -> List[WebSocketMessage]:
        """新しいタスクを検出してメッセージを生成"""
        messages = []
        
        for task_id, task_info in tasks.items():
            if task_id not in self.known_tasks:
                # 新しいタスクを検出
                self.known_tasks.add(task_id)
                
                # 親タスクIDを推測（root-api → root）
                parent_id = None
                if "-" in task_id:
                    parts = task_id.split("-")
                    if len(parts) > 1:
                        parent_id = parts[0]
                
                messages.append(WebSocketMessage(
                    type=MessageType.TASK_ADDED,
                    task_id=task_id,
                    parent_id=parent_id,
                    status=task_info.get("status", "pending")
                ))
        
        return messages
    
    async def process_bus_changes(self, broadcast_func: Callable):
        """bus.jsonlの新しい行を処理"""
        try:
            if not self.bus_jsonl_path.exists():
                return
            
            with open(self.bus_jsonl_path, "r") as f:
                # 最後に読んだ位置まで移動
                f.seek(self.bus_last_position)
                
                # 新しい行を読む
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        bus_data = json.loads(line)
                        message = self.parse_bus_message(bus_data)
                        
                        if message:
                            await broadcast_func(message.to_dict())
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing bus.jsonl line: {e}")
                
                # 現在の位置を記録
                self.bus_last_position = f.tell()
        
        except Exception as e:
            logger.error(f"Error processing bus changes: {e}")
    
    async def process_tasks_changes(self, broadcast_func: Callable):
        """tasks.jsonの変更を処理"""
        try:
            if not self.tasks_json_path.exists():
                return
            
            with open(self.tasks_json_path, "r") as f:
                tasks = json.load(f)
            
            # 新しいタスクを検出
            messages = self.detect_new_tasks(tasks)
            
            # メッセージを送信
            for message in messages:
                await broadcast_func(message.to_dict())
        
        except Exception as e:
            logger.error(f"Error processing tasks changes: {e}")
    
    async def start_monitoring(self, broadcast_func: Callable):
        """ファイル監視を開始"""
        logger.info(f"Starting file monitoring for: {self.ai_app_dir}")
        
        # 変更通知用のキュー
        change_queue = queue.Queue()
        
        # ファイル変更ハンドラを作成
        handler = FileChangeHandler(change_queue)
        
        # 監視対象ディレクトリ
        watch_dirs = []
        if self.bus_jsonl_path.parent.exists():
            watch_dirs.append(str(self.bus_jsonl_path.parent))
        if self.tasks_json_path.parent.exists():
            watch_dirs.append(str(self.tasks_json_path.parent))
        
        if not watch_dirs:
            logger.warning("No directories to watch")
            return
        
        # Observerを作成して監視開始
        observer = Observer()
        for watch_dir in set(watch_dirs):  # 重複を除去
            observer.schedule(handler, watch_dir, recursive=False)
        
        observer.start()
        logger.info("File monitoring started")
        
        try:
            # 監視を継続
            while True:
                # キューから変更通知を取得（非ブロッキング）
                try:
                    change_type, filename = change_queue.get_nowait()
                    
                    if change_type == "bus":
                        await self.process_bus_changes(broadcast_func)
                    elif change_type == "tasks":
                        await self.process_tasks_changes(broadcast_func)
                    
                except queue.Empty:
                    # キューが空の場合は少し待つ
                    await asyncio.sleep(0.1)
                    
        except asyncio.CancelledError:
            # 正常なキャンセル
            observer.stop()
            observer.join()
            logger.info("File monitoring stopped")
        except Exception as e:
            logger.error(f"Error in file monitoring: {e}")
            observer.stop()
            observer.join()
            raise