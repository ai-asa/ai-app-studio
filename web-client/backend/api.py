"""
API endpoints for AI App Studio Web Client.
"""
from fastapi import APIRouter, HTTPException, Query
from pathlib import Path
from typing import Dict, Any, Optional, List
import json
import yaml
import logging
from datetime import datetime
import os

from .models import Task, TaskStatus, TaskHierarchy, LogContent

logger = logging.getLogger(__name__)

# APIルーター
router = APIRouter()

# AI App Studioのルートディレクトリを取得
def get_ai_app_studio_root() -> Path:
    """AI App Studioのワークディレクトリを取得"""
    # 環境変数から取得（busdから設定される）
    target_repo = os.environ.get("TARGET_REPO", Path.cwd())
    return Path(target_repo) / ".ai-app-studio"


@router.get("/tasks", response_model=Dict[str, Dict[str, Any]])
async def get_tasks():
    """タスク階層を取得"""
    ai_root = get_ai_app_studio_root()
    tasks_file = ai_root / "state" / "tasks.json"
    
    if not tasks_file.exists():
        logger.warning(f"Tasks file not found: {tasks_file}")
        return {}
    
    try:
        # tasks.jsonを読み込み
        with open(tasks_file, 'r') as f:
            tasks_data = json.load(f)
        
        # TaskHierarchyを構築
        hierarchy = TaskHierarchy()
        
        for task_id, task_info in tasks_data.items():
            # ステータスの変換
            status_str = task_info.get("status", "pending")
            try:
                status = TaskStatus(status_str)
            except ValueError:
                # 旧形式のステータスマッピング
                if status_str == "spawned":
                    status = TaskStatus.RUNNING
                else:
                    status = TaskStatus.PENDING
            
            # タスク作成
            task = Task(
                id=task_id,
                status=status,
                message=task_info.get("goal", "")
            )
            
            # 環境変数から追加情報を取得
            env = task_info.get("env", {})
            parent_id = env.get("PARENT_UNIT_ID")
            
            # 親タスクの子リストに追加
            if parent_id and parent_id in hierarchy.tasks:
                parent_task = hierarchy.get_task(parent_id)
                if parent_task and task_id not in parent_task.children:
                    parent_task.children.append(task_id)
            
            # worktreeパスから children-status.yml を読む
            worktree_path = task_info.get("worktree_path") or task_info.get("cwd")
            if worktree_path:
                worktree = Path(worktree_path)
                children_status_file = worktree / "children-status.yml"
                
                if children_status_file.exists():
                    try:
                        with open(children_status_file, 'r') as f:
                            children_data = yaml.safe_load(f) or {}
                        
                        # 子タスクのリストを更新
                        children = children_data.get("children", [])
                        for child in children:
                            child_id = child.get("unit_id")
                            if child_id and child_id not in task.children:
                                task.children.append(child_id)
                            
                            # 子タスクの詳細情報を更新（既に存在する場合）
                            if child_id in hierarchy.tasks:
                                child_task = hierarchy.get_task(child_id)
                                if child_task:
                                    # PR番号の更新
                                    if child.get("pr_number"):
                                        child_task.pr_number = child["pr_number"]
                                    # エラーメッセージの更新
                                    if child.get("error_message"):
                                        child_task.message = child["error_message"]
                                    # ステータスの更新
                                    if child.get("status") == "completed":
                                        child_task.status = TaskStatus.COMPLETED
                                    elif child.get("status") == "error":
                                        child_task.status = TaskStatus.ERROR
                    except Exception as e:
                        logger.warning(f"Failed to read children-status.yml: {e}")
            
            hierarchy.add_task(task)
        
        # 階層を再度走査して子タスクの情報を更新
        for task_id, task_info in tasks_data.items():
            worktree_path = task_info.get("worktree_path") or task_info.get("cwd")
            if worktree_path:
                worktree = Path(worktree_path)
                children_status_file = worktree / "children-status.yml"
                
                if children_status_file.exists():
                    try:
                        with open(children_status_file, 'r') as f:
                            children_data = yaml.safe_load(f) or {}
                        
                        children = children_data.get("children", [])
                        for child in children:
                            child_id = child.get("unit_id")
                            if child_id and child_id in hierarchy.tasks:
                                child_task = hierarchy.get_task(child_id)
                                if child_task:
                                    # 詳細情報を更新
                                    if child.get("pr_number"):
                                        child_task.pr_number = child["pr_number"]
                                    if child.get("error_message"):
                                        child_task.message = child["error_message"]
                                    if child.get("status") == "completed":
                                        child_task.status = TaskStatus.COMPLETED
                                    elif child.get("status") == "error":
                                        child_task.status = TaskStatus.ERROR
                    except Exception as e:
                        logger.warning(f"Failed to update child info: {e}")
        
        return hierarchy.to_dict()
    
    except Exception as e:
        logger.error(f"Failed to load tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs/{task_id}", response_model=Dict[str, Any])
async def get_logs(
    task_id: str,
    lines: Optional[int] = Query(None, description="Number of lines to return from the end")
):
    """特定タスクのログを取得"""
    ai_root = get_ai_app_studio_root()
    log_file = ai_root / "logs" / "raw" / f"{task_id}.raw"
    
    if not log_file.exists():
        raise HTTPException(status_code=404, detail="Log file not found")
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 行数制限がある場合
        if lines is not None and lines > 0:
            content_lines = content.strip().split('\n')
            if len(content_lines) > lines:
                content_lines = content_lines[-lines:]
            content = '\n'.join(content_lines)
        
        # ファイルの最終更新時刻
        last_updated = datetime.fromtimestamp(log_file.stat().st_mtime)
        
        log = LogContent(
            task_id=task_id,
            content=content,
            last_updated=last_updated
        )
        
        return log.to_dict()
    
    except Exception as e:
        logger.error(f"Failed to read log file: {e}")
        raise HTTPException(status_code=500, detail=str(e))