import websocket
import json
from threading import Thread
from .utils.logger import get_logger

class ComfyUIWebSocketClient:
    """
    处理 WebSocket 连接和消息处理。
    """
    def __init__(self, url):
        self.url = url
        self.ws = websocket.WebSocketApp(
            url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )
        self.logger = get_logger("ComfyUIWebSocketClient")
        self.is_connected = False
        self.progress_callback = None
        self.completion_callback = None

    def on_message(self, ws, message):
        """
        处理传入消息。根据消息类型调用相应的回调。
        """
        try:
            data = json.loads(message)
            if isinstance(data, dict):
                event_type = data.get("type")
                event_data = data.get("data", {})
                
                if event_type == "progress" and self.progress_callback:
                    prompt_id = event_data.get("prompt_id")
                    if prompt_id:
                        self.progress_callback(prompt_id, event_data)
                
                elif event_type == "executed" and self.completion_callback:
                    prompt_id = event_data.get("prompt_id")
                    if prompt_id:
                        self.completion_callback(prompt_id, event_data)
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