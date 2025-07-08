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
                
                # 正确处理进度更新事件 (当 node is None 时是全局进度)
                if event_type == "executing" and event_data.get("node") is None and self.progress_callback:
                    prompt_id = event_data.get("prompt_id")
                    if prompt_id:
                        self.progress_callback(prompt_id, event_data)
                
                # 覆盖所有完成事件
                elif event_type in ["execution_complete", "execution_cached", "executed"] and self.completion_callback:
                    prompt_id = event_data.get("prompt_id")
                    if prompt_id:
                        # 确保向回调传递一个一致的状态
                        self.completion_callback(prompt_id, {"status": "completed", "result": event_data})

                # 处理执行错误
                elif event_type == "execution_error" and self.completion_callback:
                    prompt_id = event_data.get("prompt_id")
                    if prompt_id:
                        self.completion_callback(prompt_id, {"status": "failed", "error": event_data})

                else:
                    self.logger.debug(f"收到未处理的事件: {event_type}")
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