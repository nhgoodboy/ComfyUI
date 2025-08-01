"""
Mn¡
"""

import os
from typing import Optional

class Config:
    """”(Mn"""
    
    # ComfyUIå\A¡hMn
    COMFYUI_WORKFLOW_SERVER_URL: str = os.getenv(
        "COMFYUI_WORKFLOW_SERVER_URL", 
        "http://localhost:8000"
    )
    
    # KÕûßMn
    TEST_SYSTEM_HOST: str = os.getenv("TEST_SYSTEM_HOST", "0.0.0.0")
    TEST_SYSTEM_PORT: int = int(os.getenv("TEST_SYSTEM_PORT", "8001"))
    
    # WebSocketMn
    WEBSOCKET_PING_INTERVAL: int = 30
    WEBSOCKET_TIMEOUT: int = 60
    
    # ÝMn
    SESSION_TIMEOUT: int = 3600  # 1ö
    MAX_SESSIONS: int = 100
    
    # å×Mn
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # CORSMn
    CORS_ORIGINS: list = [
        "http://localhost:8001",
        "http://127.0.0.1:8001",
    ]

config = Config()