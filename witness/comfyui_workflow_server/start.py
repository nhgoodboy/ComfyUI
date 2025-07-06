#!/usr/bin/env python3
"""
ComfyUI工作流服务器启动脚本
"""

import os
import sys
import argparse
import uvicorn
from pathlib import Path
from dotenv import load_dotenv

# 在读取任何配置之前加载.env文件
load_dotenv()

def main():
    """主函数"""
    # 将项目根目录添加到sys.path，以便uvicorn可以找到app模块
    # 这是必要的，因为我们是从脚本运行，而不是作为模块
    ROOT_DIR = Path(__file__).resolve().parent
    if str(ROOT_DIR) not in sys.path:
        sys.path.append(str(ROOT_DIR))

    parser = argparse.ArgumentParser(description='ComfyUI工作流服务器')
    parser.add_argument('--host', type=str, default=os.getenv('HOST', '0.0.0.0'), help='监听地址')
    parser.add_argument('--port', type=int, default=int(os.getenv('PORT', '8000')), help='监听端口')
    parser.add_argument('--workers', type=int, default=int(os.getenv('WORKERS', '1')), help='工作进程数')
    parser.add_argument('--reload', action='store_true', help='启用自动重载（开发模式）')
    
    args = parser.parse_args()

    # 应用初始化和日志记录现在完全由 app/main.py 的 lifespan 管理
    # 这个脚本只负责传递命令行参数并启动uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        workers=args.workers,
        reload=args.reload,
        lifespan="on"
    )

if __name__ == "__main__":
    main() 