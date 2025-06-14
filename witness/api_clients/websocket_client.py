# witness/api_clients/websocket_client.py
# 备注：此类用于管理与 ComfyUI WebSocket 服务器的连接。
import websocket # websocket-client library
import json
import threading
import time
from ..config import settings
import uuid

class WebSocketClient:
    def __init__(self, ws_url=None, client_id=None, on_message_callback=None, on_open_callback=None, on_error_callback=None, on_close_callback=None):
        self.ws_url = ws_url or settings.COMFYUI_WS_URL
        self.client_id = client_id or settings.CLIENT_ID or str(uuid.uuid4()) # 客户端 ID，用于标识 WebSocket 连接
        self.full_ws_url = f"{self.ws_url}?clientId={self.client_id}" # 完整的 WebSocket URL，包含客户端 ID
        
        self.ws_app = None # WebSocket 应用实例
        self.thread = None # 用于运行 WebSocket 连接的线程
        self.is_running = False # 标记 WebSocket 是否正在运行

        # 回调函数
        self.on_message_callback = on_message_callback or self._default_on_message # 收到消息时的回调
        self.on_open_callback = on_open_callback or self._default_on_open # 连接打开时的回调
        self.on_error_callback = on_error_callback or self._default_on_error # 发生错误时的回调
        self.on_close_callback = on_close_callback or self._default_on_close # 连接关闭时的回调

    def _default_on_message(self, ws, message):
        """默认的收到消息回调函数。"""
        try:
            data = json.loads(message)
            print(f"WebSocket 消息已接收 (客户端 ID: {self.client_id}):", data)
            # 此处可以添加基于消息类型的进一步处理
            # 例如：if data['type'] == 'status': handle_status(data['data'])
        except json.JSONDecodeError:
            print(f"WebSocket 非 JSON 消息 (客户端 ID: {self.client_id}): {message}")

    def _default_on_open(self, ws):
        """默认的连接打开回调函数。"""
        print(f"WebSocket 连接已打开 (客户端 ID: {self.client_id}) 至 {self.full_ws_url}")

    def _default_on_error(self, ws, error):
        """默认的发生错误回调函数。"""
        print(f"WebSocket 错误 (客户端 ID: {self.client_id}): {error}")

    def _default_on_close(self, ws, close_status_code, close_msg):
        """默认的连接关闭回调函数。"""
        self.is_running = False
        print(f"WebSocket 连接已关闭 (客户端 ID: {self.client_id}) - 代码: {close_status_code}, 消息: {close_msg}")

    def connect(self):
        """连接到 WebSocket 服务器。"""
        if self.is_running:
            print("WebSocket 客户端已在运行。")
            return

        self.ws_app = websocket.WebSocketApp(self.full_ws_url,
                                           on_open=self.on_open_callback,
                                           on_message=self.on_message_callback,
                                           on_error=self.on_error_callback,
                                           on_close=self.on_close_callback)
        self.is_running = True
        self.thread = threading.Thread(target=self.ws_app.run_forever)
        self.thread.daemon = True # 允许主程序退出，即使线程仍在运行
        self.thread.start()
        print(f"WebSocket 客户端线程已为 {self.client_id} 启动。")

    def disconnect(self):
        """断开 WebSocket 连接。"""
        if self.ws_app and self.is_running:
            print(f"正在为 {self.client_id} 关闭 WebSocket 连接...")
            self.ws_app.close()
            # self.thread.join() # 可选：等待线程完成
            self.is_running = False
            print(f"{self.client_id} 的 WebSocket 连接已关闭。")
        else:
            print("WebSocket 客户端未运行或已断开连接。")

    def send_message(self, message_data):
        """向 WebSocket 服务器发送 JSON 消息。"""
        if self.ws_app and self.is_running:
            try:
                self.ws_app.send(json.dumps(message_data))
                print(f"已发送 WebSocket 消息: {message_data}")
            except Exception as e:
                print(f"发送 WebSocket 消息时出错: {e}")
        else:
            print("WebSocket 客户端未连接。无法发送消息。")

# 示例用法 (可以删除或移动到测试/示例文件)
if __name__ == '__main__':
    # 此示例需要一个正在运行的 ComfyUI 实例。
    
    # 自定义回调函数示例
    def my_on_message(ws, message):
        data = json.loads(message)
        print(f"[自定义处理程序] 客户端 '{ws.client_id}' 的 WS 消息: {data['type']}")
        if data['type'] == 'status':
            print(f"[自定义处理程序] 队列剩余: {data['data']['status']['exec_info']['queue_remaining']}")
        elif data['type'] == 'progress':
            print(f"[自定义处理程序] 进度: {data['data']['value']}/{data['data']['max']}")

    def my_on_open(ws):
        print(f"[自定义处理程序] 客户端 '{ws.client_id}' 的 WebSocket 已连接！")

    try:
        print("启动 WebSocket 客户端示例...")
        # 通过回调函数的自定义属性将 client_id 传递给 WebSocketApp 实例
        ws_client = WebSocketClient(on_message_callback=lambda ws, msg: my_on_message(ws.app, msg), 
                                    on_open_callback=lambda ws: my_on_open(ws.app))
        ws_client.ws_app.app = ws_client # 使客户端可通过 ws.app 在回调中访问
        
        ws_client.connect()
        
        print("WebSocket 客户端已连接。正在监听消息，持续 15 秒...")
        print("请尝试在 ComfyUI 中排队一个提示以查看消息。")
        
        # 保持主线程活动以接收消息
        time.sleep(15) 
        
    except Exception as e:
        print(f"WebSocket 客户端示例失败: {e}")
    finally:
        if 'ws_client' in locals() and ws_client.is_running:
            print("正在断开 WebSocket 客户端连接...")
            ws_client.disconnect()
        print("WebSocket 客户端示例已完成。")