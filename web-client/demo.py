"""
AI App Studio Web Client デモスクリプト
モニタリング機能の動作を確認するためのデモ
"""
import json
import time
from pathlib import Path
from datetime import datetime


def setup_demo_project():
    """デモ用のプロジェクト構造を作成"""
    demo_dir = Path("demo_project")
    ai_app_dir = demo_dir / ".ai-app-studio"
    
    # ディレクトリ作成
    (ai_app_dir / "logs" / "raw").mkdir(parents=True, exist_ok=True)
    (ai_app_dir / "state").mkdir(parents=True, exist_ok=True)
    
    # 初期タスクを作成
    tasks = {
        "root": {
            "status": "running",
            "goal": "メモアプリケーション開発",
            "started_at": datetime.utcnow().isoformat() + "Z"
        }
    }
    
    tasks_json = ai_app_dir / "state" / "tasks.json"
    tasks_json.write_text(json.dumps(tasks, indent=2))
    
    # bus.jsonlに初期ログ
    bus_jsonl = ai_app_dir / "logs" / "bus.jsonl"
    initial_log = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "from": "unit:root",
        "type": "spawn",
        "task": "root",
        "data": {"goal": "メモアプリケーション開発"}
    }
    bus_jsonl.write_text(json.dumps(initial_log) + "\n")
    
    # ルートタスクのログファイル
    root_log = ai_app_dir / "logs" / "raw" / "root.raw"
    root_log.write_text("""CLAUDE.mdを読んで指示に従ってください。最初のタスクはrequirements.ymlを読んでサブタスクに分解することです。

requirements.ymlを読み込んでいます...
タスクを分析しています...
サブタスクに分解します:
1. フロントエンド開発
2. バックエンド開発
3. インフラストラクチャ
""")
    
    print(f"デモプロジェクトを作成しました: {demo_dir.absolute()}")
    return demo_dir


def simulate_task_progress(demo_dir):
    """タスクの進行をシミュレート"""
    ai_app_dir = demo_dir / ".ai-app-studio"
    
    print("\n5秒後に子タスクを追加します...")
    time.sleep(5)
    
    # 新しいタスクを追加
    tasks_json = ai_app_dir / "state" / "tasks.json"
    tasks = json.loads(tasks_json.read_text())
    
    # フロントエンドタスク
    tasks["root-frontend"] = {
        "status": "running",
        "goal": "フロントエンド実装",
        "started_at": datetime.utcnow().isoformat() + "Z"
    }
    
    tasks_json.write_text(json.dumps(tasks, indent=2))
    
    # bus.jsonlに追記
    bus_jsonl = ai_app_dir / "logs" / "bus.jsonl"
    spawn_log = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "from": "unit:root",
        "type": "spawn",
        "task": "root-frontend",
        "data": {"goal": "フロントエンド実装"}
    }
    with open(bus_jsonl, "a") as f:
        json.dump(spawn_log, f)
        f.write("\n")
    
    # フロントエンドのログファイル
    frontend_log = ai_app_dir / "logs" / "raw" / "root-frontend.raw"
    frontend_log.write_text("""フロントエンド開発を開始します...
ReactとTailwind CSSを使用します。
コンポーネント作成中...
""")
    
    print("子タスク 'root-frontend' を追加しました")
    
    # さらに5秒後にタスク完了
    print("\n5秒後にタスクを完了します...")
    time.sleep(5)
    
    # タスク完了ログ
    completion_log = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "from": "unit:root-frontend",
        "type": "result",
        "task": "root-frontend",
        "data": {
            "is_error": False,
            "message": "フロントエンド実装が完了しました"
        }
    }
    with open(bus_jsonl, "a") as f:
        json.dump(completion_log, f)
        f.write("\n")
    
    # ログに完了メッセージ追加
    with open(frontend_log, "a") as f:
        f.write("\nindex.html作成完了\napp.js作成完了\nstyle.css作成完了\n✅ フロントエンド実装が完了しました！")
    
    print("タスク 'root-frontend' が完了しました")
    
    # バックエンドタスクも追加
    print("\n3秒後にバックエンドタスクを追加します...")
    time.sleep(3)
    
    tasks = json.loads(tasks_json.read_text())
    tasks["root-backend"] = {
        "status": "error",
        "goal": "バックエンドAPI実装",
        "started_at": datetime.utcnow().isoformat() + "Z"
    }
    tasks_json.write_text(json.dumps(tasks, indent=2))
    
    # エラーログ
    error_log = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "from": "unit:root-backend",
        "type": "result",
        "task": "root-backend",
        "data": {
            "is_error": True,
            "message": "モジュール 'express' が見つかりません"
        }
    }
    with open(bus_jsonl, "a") as f:
        json.dump(error_log, f)
        f.write("\n")
    
    # バックエンドのログファイル
    backend_log = ai_app_dir / "logs" / "raw" / "root-backend.raw"
    backend_log.write_text("""バックエンドAPI開発を開始します...
FastAPIを使用します。
依存関係をインストール中...
Error: Module 'express' not found
❌ エラーが発生しました
""")
    
    print("タスク 'root-backend' でエラーが発生しました")


def main():
    print("=== AI App Studio Web Client デモ ===\n")
    
    # デモプロジェクトをセットアップ
    demo_dir = setup_demo_project()
    
    print("\n以下のコマンドでWeb Clientを起動してください:")
    print(f"TARGET_REPO={demo_dir.absolute()} python -m uvicorn backend.main:app --port 8000")
    print("\nブラウザで http://localhost:8000 を開いてください")
    print("\nタスクの進行をシミュレートします...")
    
    # タスク進行をシミュレート
    simulate_task_progress(demo_dir)
    
    print("\n=== デモ完了 ===")
    print("Webインターフェースでタスクの状態変化を確認してください！")


if __name__ == "__main__":
    main()