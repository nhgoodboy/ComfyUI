#!/usr/bin/env python3
"""
ComfyUI工作流服务器启动脚本

用于启动工作流处理API服务器的主要入口点。
"""

import os
import sys
import logging
from pathlib import Path
import argparse
import logging.config
import uvicorn
from dotenv import load_dotenv

# --- 配置加载 ---
# 必须在导入任何应用模块之前加载环境变量，以避免配置被过早缓存
# 优先加载.env文件，使其成为默认配置
default_env_path = Path(__file__).parent / ".env"
if default_env_path.is_file():
    # 使用 override=True 确保.env文件优先于系统环境变量
    load_dotenv(default_env_path, override=True)

# 将项目根目录添加到Python路径
# 假设start.py在项目根目录下，所以app可以直接导入
sys.path.insert(0, str(Path(__file__).parent))

from main import app
from app.config import get_settings, validate_config, get_environment_info, AppConfig

# 在导入任何其他模块之前配置基本日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """主函数，负责配置加载和服务器启动"""
    parser = argparse.ArgumentParser(description="ComfyUI Workflow Server")
    parser.add_argument("--config", type=str, default=None, help="覆盖默认配置文件的路径 (.env)")
    parser.add_argument("--host", type=str, default=None, help="覆盖服务器主机")
    parser.add_argument("--port", type=int, default=None, help="覆盖服务器端口")
    args = parser.parse_args()

    # 如果提供了 --config 参数，则用它来覆盖已加载的.env配置
    if args.config:
        if Path(args.config).is_file():
            load_dotenv(args.config, override=True)
            logger.info(f"使用 --config 参数从 {args.config} 覆盖配置")
        else:
            logger.warning(f"指定的配置文件 {args.config} 未找到，将使用已加载的配置。")
    
    # 获取配置 (此时应已正确加载)
    settings: AppConfig = get_settings()
    
    # 重新配置日志系统
    logging.config.dictConfig(settings.get_logging_config())

    # 打印环境和配置信息
    logger.info("🚀 环境信息:")
    env_info = get_environment_info()
    for key, value in env_info.items():
        logger.info(f"  - {key}: {value}")
    
    logger.info("📋 验证配置...")
    if validate_config(settings):
        logger.info("✅ 配置验证通过。")
    else:
        logger.warning("❌ 配置验证失败，请检查环境变量或.env文件。")

    # 命令行参数覆盖配置
    host = args.host or settings.host
    port = args.port or settings.port
    
    logger.info("🚀 启动服务器...")
    
    if settings.is_production():
        logger.warning("生产模式已激活。请确保所有安全设置都已配置。")
        logger.warning(f"CORS源: {settings.cors_origins}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        workers=settings.workers if not settings.debug else 1,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )

if __name__ == "__main__":
    main() 