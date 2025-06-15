import websocket
import json
from threading import Thread
from ..utils.logger import get_logger

class WebSocketClient:
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

    def on_message(self, ws, message):
        """
        处理传入消息。重写此方法以处理消息。
        """
        self.logger.info(f"收到消息: {message}")

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

    def close(self):
        """
        关闭 WebSocket 连接。
        """
        self.ws.close() 