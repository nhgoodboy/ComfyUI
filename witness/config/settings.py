# witness/config/settings.py
# 配置文件，用于存储 ComfyUI API 和 WebSocket 的相关设置。

COMFYUI_API_URL = "http://127.0.0.1:8188"
# 如果 ComfyUI 启动时使用了 API 密钥，请在此处设置
# 例如：COMFYUI_API_KEY = "your_api_key_here"
COMFYUI_API_KEY = None

# API 请求的默认客户端 ID
CLIENT_ID = "comfyui_witness_client"

# API 请求超时时间（秒）
REQUEST_TIMEOUT = 60

# WebSocket URL (如果与 API URL 结构不同)
COMFYUI_WS_URL = "ws://127.0.0.1:8188/ws"