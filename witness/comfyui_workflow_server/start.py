#!/usr/bin/env python3
"""
ComfyUI工作流服务器启动脚本

提供服务启动、配置验证和环境检查功能。
"""

import sys
import os
import logging
import signal
import argparse
from pathlib import Path
import uvicorn

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def validate_environment():
    """验证运行环境和配置"""
    logger = logging.getLogger(__name__)
    
    # 检查Python版本
    if sys.version_info < (3, 8):
        logger.error("需要Python 3.8或更高版本")
        sys.exit(1)
    
    # 检查.env文件（可选）
    env_file = Path(project_root) / '.env'
    if env_file.exists():
        logger.info(f"发现环境配置文件: {env_file}")
    else:
        logger.info("未发现.env文件，将使用默认配置")
    
    logger.info("环境验证通过")

def signal_handler(signum, frame):
    """信号处理器"""
    logger = logging.getLogger(__name__)
    logger.info(f"接收到信号 {signum}，正在优雅关闭服务...")
    sys.exit(0)

def main():
    """主函数"""
    # 基础日志配置，应用内部会进一步配置
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # 命令行参数解析
    parser = argparse.ArgumentParser(description='ComfyUI工作流服务器')
    parser.add_argument('--host', type=str, default=os.getenv('HOST', '0.0.0.0'), help='监听地址')
    parser.add_argument('--port', type=int, default=int(os.getenv('PORT', '8000')), help='监听端口')
    parser.add_argument('--workers', type=int, default=int(os.getenv('WORKERS', '1')), help='工作进程数')
    parser.add_argument('--reload', action='store_true', help='启用自动重载（开发模式）')
    parser.add_argument('--validate-only', action='store_true', help='仅验证环境配置')
    
    args = parser.parse_args()
    
    try:
        logger.info("=== ComfyUI工作流服务器启动 ===")
        
        # 验证环境
        validate_environment()
        
        if args.validate_only:
            logger.info("环境验证完成，退出")
            return
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 启动Uvicorn服务
        # 应用内部的配置（如DEBUG模式）会通过环境变量自动加载
        uvicorn_config = uvicorn.Config(
            "app.main:app",
            host=args.host,
            port=args.port,
            workers=args.workers,
            reload=args.reload,
            log_level="info",
        )
        server = uvicorn.Server(uvicorn_config)
        
        logger.info(f"启动服务 - 地址: {args.host}:{args.port}, 工作进程: {args.workers}, 重载: {args.reload}")
        server.run()
        
    except KeyboardInterrupt:
        logger.info("接收到中断信号，服务已停止")
    except Exception as e:
        logger.error(f"服务启动失败: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 