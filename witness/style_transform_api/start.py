#!/usr/bin/env python3
"""
图像风格变换API服务启动脚本
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import run_server

if __name__ == "__main__":
    print("启动图像风格变换API服务...")
    run_server() 