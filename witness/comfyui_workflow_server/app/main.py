"""
ComfyUI工作流服务器主应用

多层安全防护的多用户图像风格转换API
银行级安全架构：API密钥 + 签名验证 + JWT令牌 + IP白名单 + 速率限制
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# 导入配置
from .config import config, security_config, validate_config

# 导入API路由
from .api.v1 import styles, tasks, files

# 导入安全中间件
from .middleware.security_middleware import SecurityMiddleware

# 导入服务初始化
from .services.user_task_service import init_task_service
from .services.user_file_service import init_file_service
from .services.jwt_service import init_jwt_service
from .utils.crypto_utils import init_crypto_utils
from .core.style_registry import style_registry
from .models.api_models import HealthResponse

# 配置日志
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    try:
        # 启动时初始化
        logger.info("=== ComfyUI工作流服务器启动 ===")
        logger.info("应用模式: 银行级安全防护")
        
        # 配置验证
        if not validate_config():
            raise RuntimeError("配置验证失败")
        
        # 初始化安全服务
        init_crypto_utils(security_config.api_secret_key)
        init_jwt_service(security_config.jwt_secret_key, security_config.token_expiry_minutes)
        logger.info("安全服务初始化完成")
        
        # 初始化风格注册表
        try:
            style_registry.reload_styles()
            style_count = style_registry.get_style_count()
            logger.info(f"成功加载 {style_count} 个风格")
        except Exception as e:
            logger.error(f"加载风格配置失败: {e}")
        
        # 确保必要的目录存在
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        
        output_dir = Path("outputs")
        output_dir.mkdir(exist_ok=True)
        
        # 初始化业务服务
        try:
            init_task_service()
            init_file_service()
            logger.info("业务服务初始化完成")
        except Exception as e:
            logger.error(f"初始化业务服务失败: {e}")
        
        # 安全配置摘要
        security_summary = security_config.get_security_summary()
        logger.info(f"安全配置: {security_summary}")
        
        logger.info("应用启动完成 - 所有安全防护已激活")
        yield
        
    except Exception as e:
        logger.error(f"应用启动失败: {e}")
        raise
    finally:
        # 清理资源
        logger.info("应用正在关闭...")

# 创建FastAPI应用
fastapi_config = config.get_fastapi_config()
app = FastAPI(
    **fastapi_config,
    lifespan=lifespan
)

# 添加统一安全中间件（五层防护）
app.add_middleware(
    SecurityMiddleware,
    api_secret_key=security_config.api_secret_key,
    allowed_ips=security_config.allowed_ips,
    signature_timeout=security_config.signature_timeout,
    rate_limit_per_ip=security_config.rate_limit_per_ip,
    rate_limit_per_user=security_config.rate_limit_per_user
)

# 添加CORS中间件（仅在开发模式或配置了CORS源时）
if config.debug or security_config.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=security_config.cors_origins if security_config.cors_origins else ["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

# 添加静态文件服务
if Path("uploads").exists():
    app.mount("/files", StaticFiles(directory="uploads"), name="files")

if Path("outputs").exists():
    app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

# 注册路由
app.include_router(styles.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(files.router, prefix="/api/v1")

# 添加请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求日志"""
    start_time = time.time()
    
    # 获取客户端IP
    client_ip = request.headers.get("x-forwarded-for", request.client.host)
    
    # 记录请求开始
    logger.info(f"请求开始: {client_ip} - {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        
        # 记录请求完成
        duration = time.time() - start_time
        logger.info(f"请求完成: {client_ip} - {request.method} {request.url.path} - {response.status_code} - {duration:.3f}s")
        
        return response
    except Exception as e:
        # 记录请求错误
        duration = time.time() - start_time
        logger.error(f"请求失败: {client_ip} - {request.method} {request.url.path} - {str(e)} - {duration:.3f}s")
        raise

@app.get("/")
async def root():
    """根路径"""
    try:
        styles_list = style_registry.get_all_styles()
        available_styles = [style.id for style in styles_list]
    except Exception:
        available_styles = []
    
    return {
        "message": config.app_name,
        "version": config.version,
        "description": config.description,
        "status": "running",
        "architecture": "银行级安全防护架构",
        "security_enabled": True,
        "available_styles": available_styles,
        "api_endpoints": {
            "styles": "/api/v1/styles",
            "tasks": "/api/v1/tasks",
            "files": "/api/v1/files",
            "health": "/health",
            "docs": "/docs" if config.debug else None
        }
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    try:
        # 检查风格注册系统
        style_count = style_registry.get_style_count()
        
        health_data = {
            "status": "ok",
            "message": "风格转换服务运行正常",
            "timestamp": time.time(),
            "version": config.version,
            "security_layers": 5,
            "security_enabled": True
        }
        
        # 添加风格统计信息
        if style_count > 0:
            health_data["styles_loaded"] = style_count
            health_data["available_styles"] = [style.id for style in style_registry.get_all_styles()]
        else:
            health_data["warning"] = "未加载任何风格"
        
        return health_data
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "message": f"服务异常: {str(e)}",
                "timestamp": time.time(),
                "version": config.version,
                "security_enabled": True
            }
        )

@app.get("/security-info")
async def security_info():
    """安全信息端点（仅开发模式）"""
    if not config.debug:
        return {"message": "仅开发模式可用"}
    
    return {
        "security_summary": security_config.get_security_summary(),
        "environment": "development" if config.debug else "production",
        "security_layers": [
            "第1层: IP白名单控制",
            "第2层: API密钥认证",
            "第3层: 请求签名验证",
            "第4层: 速率限制保护",
            "第5层: JWT令牌验证"
        ],
        "security_features": [
            "防重放攻击",
            "防时序攻击",
            "防DDoS攻击",
            "数据加密传输",
            "令牌黑名单机制"
        ]
    }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    client_ip = request.headers.get("x-forwarded-for", request.client.host)
    logger.error(f"全局异常: {client_ip} - {request.method} {request.url.path} - {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "服务器内部错误",
            "message": str(exc) if config.debug else "请联系管理员",
            "timestamp": time.time(),
            "version": config.version
        }
    )

def run_server():
    """启动服务器"""
    # 生产模式启动提示
    if config.is_production():
        logger.warning("生产模式启动 - 确保已配置正确的安全密钥")
        logger.warning("请确保以下环境变量已正确设置:")
        logger.warning("- API_SECRET_KEY")
        logger.warning("- JWT_SECRET_KEY")
        logger.warning("- ALLOWED_IPS")
    
    # 启动服务器
    uvicorn.run(
        "app.main:app",
        host=config.host,
        port=config.port,
        log_level=config.log_level.lower(),
        reload=config.debug,
        workers=config.workers if config.is_production() else 1
    )

if __name__ == "__main__":
    run_server() 