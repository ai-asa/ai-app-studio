// AI App Studio Monitor - React Application

const { useState, useEffect, useRef } = React;

// ステータスアイコンを返す関数
function getStatusIcon(status) {
    switch (status) {
        case 'pending':
            return '⏳';
        case 'running':
            return '🔄';
        case 'completed':
            return '✅';
        case 'error':
            return '❌';
        default:
            return '❓';
    }
}

// タスクツリーコンポーネント
function TaskTree({ tasks, selectedTaskId, onSelectTask }) {
    const renderTask = (taskId, level = 0) => {
        const task = tasks[taskId];
        if (!task) return null;

        const isSelected = taskId === selectedTaskId;
        const indent = `${level * 20}px`;

        return (
            <div key={taskId}>
                <div
                    className={`task-item ${isSelected ? 'bg-blue-100' : 'hover:bg-gray-100'} 
                                cursor-pointer py-1 px-2 flex items-center`}
                    style={{ paddingLeft: indent }}
                    onClick={() => onSelectTask(taskId)}
                >
                    <span className="mr-2">{getStatusIcon(task.status)}</span>
                    <span className="font-mono text-sm">{taskId}</span>
                    {task.message && (
                        <span className="ml-2 text-gray-600 text-sm">{task.message}</span>
                    )}
                </div>
                
                {/* 子タスクを再帰的にレンダリング */}
                {task.children && task.children.map(childId => 
                    renderTask(childId, level + 1)
                )}
            </div>
        );
    };

    // ルートタスクから開始
    const rootTaskIds = Object.keys(tasks).filter(id => 
        !Object.values(tasks).some(t => t.children && t.children.includes(id))
    );

    return (
        <div className="task-tree">
            {rootTaskIds.map(rootId => renderTask(rootId))}
        </div>
    );
}

// ログビューアコンポーネント
function LogViewer({ taskId, logs }) {
    const logEndRef = useRef(null);
    const [autoScroll, setAutoScroll] = useState(true);

    useEffect(() => {
        if (autoScroll && logEndRef.current) {
            logEndRef.current.scrollIntoView({ behavior: "smooth" });
        }
    }, [logs, autoScroll]);

    if (!taskId) {
        return (
            <div className="p-4 text-gray-500">
                タスクを選択してログを表示
            </div>
        );
    }

    const taskLogs = logs[taskId] || '';

    return (
        <div className="log-viewer flex flex-col h-full">
            <div className="flex justify-between items-center p-2 bg-gray-100 border-b">
                <h3 className="font-mono text-sm">{taskId} のログ</h3>
                <label className="text-sm">
                    <input
                        type="checkbox"
                        checked={autoScroll}
                        onChange={(e) => setAutoScroll(e.target.checked)}
                        className="mr-1"
                    />
                    自動スクロール
                </label>
            </div>
            <div className="flex-1 overflow-auto p-4 bg-gray-900 text-green-400 font-mono text-xs">
                <pre>{taskLogs || 'ログがありません'}</pre>
                <div ref={logEndRef} />
            </div>
        </div>
    );
}

// メインアプリケーションコンポーネント
function App() {
    const [tasks, setTasks] = useState({});
    const [selectedTaskId, setSelectedTaskId] = useState(null);
    const [logs, setLogs] = useState({});
    const [wsConnected, setWsConnected] = useState(false);
    const wsRef = useRef(null);
    const reconnectTimeoutRef = useRef(null);

    // タスクデータを取得
    const fetchTasks = async () => {
        try {
            const response = await fetch('/api/tasks');
            if (response.ok) {
                const data = await response.json();
                setTasks(data);
            }
        } catch (error) {
            console.error('Failed to fetch tasks:', error);
        }
    };

    // ログデータを取得
    const fetchLogs = async (taskId) => {
        try {
            const response = await fetch(`/api/logs/${taskId}?lines=100`);
            if (response.ok) {
                const data = await response.json();
                setLogs(prev => ({
                    ...prev,
                    [taskId]: data.content
                }));
            }
        } catch (error) {
            console.error('Failed to fetch logs:', error);
        }
    };

    // WebSocket接続を確立
    const connectWebSocket = () => {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
            console.log('WebSocket connected');
            setWsConnected(true);
        };

        ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            console.log('WebSocket message:', message);

            switch (message.type) {
                case 'connection':
                    // 接続確認メッセージ
                    break;
                
                case 'task_update':
                    // タスクの状態更新
                    setTasks(prev => ({
                        ...prev,
                        [message.task_id]: {
                            ...prev[message.task_id],
                            status: message.status || prev[message.task_id]?.status,
                            message: message.message || prev[message.task_id]?.message
                        }
                    }));
                    break;
                
                case 'task_added':
                    // 新しいタスクの追加
                    setTasks(prev => {
                        const newTasks = { ...prev };
                        
                        // 新しいタスクを追加
                        newTasks[message.task_id] = {
                            id: message.task_id,
                            status: message.status || 'pending',
                            children: [],
                            message: message.message
                        };
                        
                        // 親タスクの子リストに追加
                        if (message.parent_id && newTasks[message.parent_id]) {
                            if (!newTasks[message.parent_id].children) {
                                newTasks[message.parent_id].children = [];
                            }
                            if (!newTasks[message.parent_id].children.includes(message.task_id)) {
                                newTasks[message.parent_id].children.push(message.task_id);
                            }
                        }
                        
                        return newTasks;
                    });
                    break;
                
                case 'log_update':
                    // ログの更新
                    if (message.task_id === selectedTaskId) {
                        fetchLogs(message.task_id);
                    }
                    break;
            }
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        ws.onclose = () => {
            console.log('WebSocket disconnected');
            setWsConnected(false);
            
            // 5秒後に再接続を試みる
            reconnectTimeoutRef.current = setTimeout(() => {
                console.log('Attempting to reconnect...');
                connectWebSocket();
            }, 5000);
        };
    };

    // 初期化
    useEffect(() => {
        fetchTasks();
        connectWebSocket();

        // クリーンアップ
        return () => {
            if (wsRef.current) {
                wsRef.current.close();
            }
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
            }
        };
    }, []);

    // 選択されたタスクのログを取得
    useEffect(() => {
        if (selectedTaskId) {
            fetchLogs(selectedTaskId);
            
            // 定期的にログを更新
            const interval = setInterval(() => {
                fetchLogs(selectedTaskId);
            }, 2000);
            
            return () => clearInterval(interval);
        }
    }, [selectedTaskId]);

    return (
        <div className="flex flex-col h-screen">
            <header className="bg-gray-800 text-white p-4 flex justify-between items-center">
                <h1 className="text-xl font-bold">AI App Studio Monitor</h1>
                <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
                    <span className="text-sm">{wsConnected ? '接続中' : '切断'}</span>
                </div>
            </header>
            
            <div className="flex flex-1 overflow-hidden">
                {/* 左側：タスクツリー */}
                <div className="w-1/2 bg-white border-r overflow-auto">
                    <div className="p-2 bg-gray-100 border-b">
                        <h2 className="font-bold">タスク階層</h2>
                    </div>
                    <TaskTree
                        tasks={tasks}
                        selectedTaskId={selectedTaskId}
                        onSelectTask={setSelectedTaskId}
                    />
                </div>
                
                {/* 右側：ログビューア */}
                <div className="w-1/2 bg-gray-50">
                    <LogViewer
                        taskId={selectedTaskId}
                        logs={logs}
                    />
                </div>
            </div>
        </div>
    );
}

// アプリケーションをマウント
ReactDOM.createRoot(document.getElementById('root')).render(<App />);