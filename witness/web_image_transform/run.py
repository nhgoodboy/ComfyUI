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

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="网页版图像风格变换测试平台")
    parser.add_argument("--host", default="0.0.0.0", help="服务器主机地址")
    parser.add_argument("--port", type=int, default=8080, help="服务器端口")
    parser.add_argument("--prod", action="store_true", help="生产模式（关闭调试和重载）")
    parser.add_argument("--workers", type=int, default=1, help="工作进程数（生产模式）")
    
    args = parser.parse_args()
    
    # 设置环境变量
    os.environ["HOST"] = args.host
    os.environ["PORT"] = str(args.port)
    
    if args.prod:
        os.environ["DEBUG"] = "false"
        print(f"🚀 启动生产服务器: http://{args.host}:{args.port}")
        print(f"📊 工作进程数: {args.workers}")
        
        import uvicorn
        uvicorn.run(
            "app.main:app",
            host=args.host,
            port=args.port,
            workers=args.workers,
            log_level="info"
        )
    else:
        os.environ["DEBUG"] = "true"
        print(f"🔧 启动开发服务器: http://{args.host}:{args.port}")
        print("📝 调试模式已启用，代码变更将自动重载")
        
        import uvicorn
        uvicorn.run(
            "app.main:app",
            host=args.host,
            port=args.port,
            reload=True,
            log_level="debug"
        )

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1) 