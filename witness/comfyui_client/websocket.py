import websocket
import json
from threading import Thread
from typing import Optional, Callable
from .utils.logger import get_logger

class ComfyUIWebSocketClient:
    """
    处理 WebSocket 连接和消息处理。

    如果未直接给出完整 `url`，可以传入 host/port/client_id 自动拼接。
    """
    def __init__(self, url: Optional[str] = None, *, host: Optional[str] = None, 
                 port: Optional[int] = None, client_id: Optional[str] = None, 
                 debug: bool = False):
        # 若提供了 host/port 则组装 URL
        if url is None and host and port:
            # 若提供 client_id 则追加查询参数以订阅专属事件
            if client_id:
                url = f"ws://{host}:{port}/ws?clientId={client_id}"
            else:
                url = f"ws://{host}:{port}/ws"
        elif url is None:
            raise ValueError("必须提供 url 或 host+port 组合")

        self.url = url
        self.debug = debug
        
        # 根据调试模式设置 websocket 追踪
        if debug:
            websocket.enableTrace(True)
        
        self.ws = websocket.WebSocketApp(
            url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )
        self.logger = get_logger("ComfyUIWebSocketClient")
        self.is_connected = False
        self.progress_callback: Optional[Callable] = None
        self.completion_callback: Optional[Callable] = None

    def on_message(self, ws, message):
        """
        处理传入消息。根据消息类型调用相应的回调。
        """
        try:
            data = json.loads(message)
            if isinstance(data, dict):
                event_type = data.get("type")
                event_data = data.get("data", {})
                
                # 调试日志：记录收到的WebSocket消息
                self.logger.debug(f"收到WebSocket消息: type={event_type}, data={event_data}")
                
                # 处理真实的进度更新事件
                if event_type == "progress" and self.progress_callback:
                    prompt_id = event_data.get("prompt_id")
                    if prompt_id:
                        self.progress_callback(prompt_id, event_data)
                
                # 处理执行状态变化 (更智能的进度估算)
                elif event_type == "executing" and self.progress_callback:
                    prompt_id = event_data.get("prompt_id")
                    node_id = event_data.get("node")
                    if prompt_id:
                        # 使用简单但有效的进度估算
                        if node_id is None:
                            # 执行完成事件，设置进度为100%
                            progress_data = {"value": 100, "max": 100, "node": None, "prompt_id": prompt_id}
                            self.logger.info(f"任务完成: {prompt_id}")
                            
                            # 清理进度状态
                            if hasattr(self, '_prompt_progress') and prompt_id in self._prompt_progress:
                                del self._prompt_progress[prompt_id]
                        else:
                            # 节点开始执行，基于节点类型提供更合理的进度估算
                            if not hasattr(self, '_prompt_progress'):
                                self._prompt_progress = {}
                            
                            if prompt_id not in self._prompt_progress:
                                self._prompt_progress[prompt_id] = {
                                    "executed_nodes": set(),  # 使用集合避免重复计数
                                    "total_estimated": 20,    # 增加估算的总节点数
                                    "start_time": __import__('time').time(),
                                    "initial_sent": False     # 是否已发送初始0%进度
                                }
                                
                                # 发送初始0%进度
                                initial_progress_data = {"value": 0, "max": 100, "node": "start", "prompt_id": prompt_id}
                                self.logger.info(f"任务开始: {prompt_id}, 初始进度: 0%")
                                self.progress_callback(prompt_id, initial_progress_data)
                                self._prompt_progress[prompt_id]["initial_sent"] = True
                            
                            # 记录已执行的节点（避免重复计数）
                            progress_state = self._prompt_progress[prompt_id]
                            progress_state["executed_nodes"].add(node_id)
                            
                            executed = len(progress_state["executed_nodes"])
                            total = progress_state["total_estimated"]
                            
                            # 更保守的进度计算，避免过快到达90%
                            if executed <= 3:
                                # 前3个节点：10%-30%
                                progress_percent = 10 + (executed - 1) * 10
                            elif executed <= 10:
                                # 第4-10个节点：30%-70%
                                progress_percent = 30 + (executed - 3) * 5
                            else:
                                # 超过10个节点：逐渐增加到85%
                                progress_percent = min(85, 70 + (executed - 10) * 2)
                            
                            progress_data = {"value": progress_percent, "max": 100, "node": node_id, "prompt_id": prompt_id}
                            self.logger.info(f"节点执行: {node_id}, 进度: {progress_percent:.1f}% (节点数: {executed})")
                        self.progress_callback(prompt_id, progress_data)
                
                # 处理采样器进度事件 (ComfyUI的采样器会发送此类事件)
                elif event_type == "sampling" and self.progress_callback:
                    prompt_id = event_data.get("prompt_id")
                    if prompt_id:
                        # 采样器进度通常包含 step/total_steps
                        step = event_data.get("step", 0)
                        total_steps = event_data.get("total_steps", 1)
                        progress_data = {"value": step, "max": total_steps, "prompt_id": prompt_id}
                        self.progress_callback(prompt_id, progress_data)
                
                # 严格只在 execution_complete 时视为任务成功
                elif event_type == "execution_complete" and self.completion_callback:
                    prompt_id = event_data.get("prompt_id")
                    if prompt_id:
                        self.completion_callback(prompt_id, {"status": "completed", "result": event_data})

                # 处理执行错误
                elif event_type == "execution_error" and self.completion_callback:
                    prompt_id = event_data.get("prompt_id")
                    if prompt_id:
                        self.completion_callback(prompt_id, {"status": "failed", "error": event_data})

                else:
                    self.logger.debug(f"收到未处理的事件: {event_type} - {event_data.get('sid')}")
            else:
                self.logger.debug(f"收到非JSON消息: {message}")
        except json.JSONDecodeError:
            self.logger.warning(f"无法解析JSON消息: {message}")
        except Exception as e:
            self.logger.error(f"处理消息时出错: {e}")

    def on_error(self, ws, error):
        """
        处理 WebSocket 错误。
        """
        self.logger.error(f"WebSocket 错误: {error}")
        self.is_connected = False

    def on_close(self, ws, close_status_code, close_msg):
        """
        处理 WebSocket 连接关闭。
        """
        self.logger.info("WebSocket 连接已关闭")
        self.is_connected = False

    def on_open(self, ws):
        """
        处理连接打开后要执行的操作。
        """
        self.logger.info("WebSocket 连接已打开")
        self.is_connected = True

    def run_forever(self):
        """
        启动 WebSocket 客户端并在一个单独的线程中永久运行它。
        """
        thread = Thread(target=self.ws.run_forever, daemon=True)
        thread.start()
        self.logger.info("WebSocket 客户端已在新线程中启动。")

    def set_progress_callback(self, callback):
        """设置进度回调函数"""
        self.progress_callback = callback

    def set_completion_callback(self, callback):
        """设置完成回调函数"""
        self.completion_callback = callback

    async def disconnect(self):
        """异步关闭WebSocket连接"""
        self.close()

    def close(self):
        """
        关闭 WebSocket 连接。
        """
        self.ws.close() 