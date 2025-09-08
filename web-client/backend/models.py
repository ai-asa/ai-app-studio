"""
Data models for AI App Studio Web Client.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any


class TaskStatus(Enum):
    """タスクの実行状態"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


class MessageType(Enum):
    """WebSocketメッセージタイプ"""
    TASK_UPDATE = "task_update"
    TASK_ADDED = "task_added"
    LOG_UPDATE = "log_update"


@dataclass
class Task:
    """タスク情報を表すモデル"""
    id: str
    status: TaskStatus
    children: List[str] = field(default_factory=list)
    message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    pr_number: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "id": self.id,
            "status": self.status.value,
            "children": self.children,
            "message": self.message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "pr_number": self.pr_number
        }


@dataclass
class TaskHierarchy:
    """タスクの階層構造を管理"""
    tasks: Dict[str, Task] = field(default_factory=dict)
    
    def add_task(self, task: Task) -> None:
        """タスクを追加"""
        self.tasks[task.id] = task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """タスクを取得"""
        return self.tasks.get(task_id)
    
    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """階層全体を辞書形式に変換"""
        return {
            task_id: task.to_dict() 
            for task_id, task in self.tasks.items()
        }


@dataclass
class LogContent:
    """ログ内容を表すモデル"""
    task_id: str
    content: str
    last_updated: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "task_id": self.task_id,
            "content": self.content,
            "last_updated": self.last_updated.isoformat()
        }


@dataclass
class WebSocketMessage:
    """WebSocketで送信するメッセージ"""
    type: MessageType
    task_id: str
    status: Optional[str] = None
    message: Optional[str] = None
    parent_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        result = {
            "type": self.type.value,
            "task_id": self.task_id
        }
        if self.status is not None:
            result["status"] = self.status
        if self.message is not None:
            result["message"] = self.message
        if self.parent_id is not None:
            result["parent_id"] = self.parent_id
        return result