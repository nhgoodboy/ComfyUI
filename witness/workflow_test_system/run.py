#!/usr/bin/env python3
"""
ComfyUI工作流测试系统启动脚本

使用方法:
    python run.py                    # 启动开发服务器
    python run.py --host 0.0.0.0    # 指定主机地址
    python run.py --port 8001       # 指定端口
    python run.py --prod            # 生产模式
"""

import argparse
import sys
import os
from pathlib import Path
import uvicorn
from dotenv import load_dotenv

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """
    加载.env文件并启动uvicorn服务器
    """
    # 在应用启动前从.env文件加载环境变量
    print("正在从环境变量加载配置...")
    load_dotenv()

    # 从环境变量（或默认值）中获取主机和端口
    host = os.getenv("TEST_SYSTEM_HOST", "0.0.0.0")
    port = int(os.getenv("TEST_SYSTEM_PORT", 8001))
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    debug_mode = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

    print(f"准备启动ComfyUI工作流测试系统于 http://{host}:{port}")
    print(f"调试模式: {'开启' if debug_mode else '关闭'}")
    print(f"日志级别: {log_level}")

    # 启动Uvicorn服务器
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=debug_mode
    )

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 ComfyUI工作流测试系统已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)