#!/usr/bin/env python3
"""
网页版图像风格变换测试平台启动脚本

使用方法:
    python run.py                    # 启动开发服务器
    python run.py --host 0.0.0.0    # 指定主机地址
    python run.py --port 8080       # 指定端口
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
    # 这确保了app.config中的settings对象能获取到正确的值
    print("正在从 .env 文件加载配置...")
    load_dotenv()

    # 从环境变量（或默认值）中获取主机和端口
    # 注意：此时settings对象还未在主流程中实例化，因此直接从os.environ获取
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", 8080))
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    debug_mode = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

    print(f"准备启动服务器于 http://{host}:{port}")
    print(f"调试模式: {'开启' if debug_mode else '关闭'}")
    print(f"日志级别: {log_level}")

    # 启动Uvicorn服务器
    # reload=debug_mode 可以在开发时实现代码热重载
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
        print("\n👋 服务器已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1) 