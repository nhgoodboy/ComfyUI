#!/usr/bin/env python3
"""
ComfyUIå\AKÕûß/¨,
"""

import uvicorn
from app.config import config

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=config.TEST_SYSTEM_HOST,
        port=config.TEST_SYSTEM_PORT,
        reload=True,
        log_level=config.LOG_LEVEL.lower()
    )