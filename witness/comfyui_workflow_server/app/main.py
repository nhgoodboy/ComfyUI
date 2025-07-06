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
from typing import Dict, List

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# 导入配置
from .config import get_settings, validate_config, AppConfig

# 导入API路由
from .api.v1 import styles, tasks, files, auth

# 导入安全中间件
from .middleware.security_middleware import SecurityMiddleware
from .middleware.rate_limit import RateLimitMiddleware

# 导入服务类
from .services import (
    UserService,
    ComfyUIService,
    UserFileService,
    UserTaskService,
    StyleService,
    style_registry
)

# 导入新添加的模块
from .services.style_service import StyleService
from .services.jwt_service import JWTService, jwt_service, init_jwt_service
from .utils.crypto_utils import CryptoUtils, init_crypto_utils, get_crypto_utils
from .core.workflow_registry import workflow_registry
from .services.user_service import user_service

# 服务实例将在lifespan中创建并附加到app.state
from .models.api_models import HealthResponse

# 日志将在lifespan中配置
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # --- 1. 初始化配置 ---
    settings = get_settings()
    
    # --- 2. 配置日志 ---
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    try:
        # --- 3. 启动时初始化 ---
        logger.info("=== ComfyUI工作流服务器启动 ===")
        logger.info(f"应用模式: {'开发' if settings.debug else '生产'}")
        
        # --- 4. 配置验证 ---
        if not validate_config(settings):
            raise RuntimeError("配置验证失败")
        
        # --- 5. 初始化服务 ---
        app.state.settings = settings
        app.state.style_registry = style_registry
        
        # 服务初始化
        logger.info("初始化服务...")
        
        # 实例化所有服务
        comfyui_service = ComfyUIService()
        user_file_service = UserFileService(
            base_upload_dir=settings.storage.uploads_dir,
            base_output_dir=settings.storage.outputs_dir
        )
        user_task_service = UserTaskService(
            comfyui_service=comfyui_service, 
            style_registry=style_registry
        )
        
        # 初始化加密工具，它将创建并持有一个内部实例
        init_crypto_utils(settings.security.api_secret_key)
        # 通过getter获取该实例
        crypto_utils = get_crypto_utils()
        
        # 现在可以将实例附加到app.state
        app.state.comfyui_service = comfyui_service
        app.state.user_file_service = user_file_service
        app.state.user_task_service = user_task_service
        app.state.user_service = user_service
        app.state.style_service = StyleService()
        app.state.jwt_service = jwt_service
        app.state.crypto_utils = crypto_utils
        app.state.style_registry = style_registry

        init_jwt_service(settings.security.jwt_secret_key, settings.security.token_expiry_minutes)
        logger.info("安全服务初始化完成")
        
        style_registry.reload_styles()
        style_count = style_registry.get_style_count()
        logger.info(f"成功加载 {style_count} 个风格")

        settings.storage.uploads_dir.mkdir(exist_ok=True)
        settings.storage.outputs_dir.mkdir(exist_ok=True)
        
        logger.info("业务服务初始化完成")
        
        security_summary = settings.security.get_security_summary()
        logger.info(f"安全配置: {security_summary}")
        
        logger.info("应用启动完成 - 所有安全防护已激活")
        
        # 启动后台任务
        # ... existing code ...
        
        await comfyui_service.initialize()
        
        # 将服务实例附加到app.state
        app.state.comfyui_service = comfyui_service
        app.state.user_file_service = user_file_service
        app.state.user_task_service = user_task_service
        app.state.user_service = user_service
        app.state.style_service = StyleService()
        app.state.jwt_service = jwt_service
        app.state.crypto_utils = crypto_utils
        app.state.style_registry = style_registry

        yield
        
        # 应用关闭时清理资源
        if hasattr(app.state, 'comfyui_service'):
            await app.state.comfyui_service.close()

    except Exception as e:
        logger.error(f"应用启动失败: {e}")
        raise
    finally:
        # 清理资源
        logger.info("应用正在关闭...")

# 在lifespan之外获取配置，用于FastAPI应用和中间件的初始化
# get_settings() 是带缓存的，所以不会重复创建实例
settings = get_settings()

# 创建FastAPI应用
fastapi_config = settings.get_fastapi_config()
app = FastAPI(
    **fastapi_config,
    lifespan=lifespan
)

# 添加统一安全中间件（五层防护）
app.add_middleware(
    SecurityMiddleware,
    api_users=settings.security.api_users,
    api_secret_key=settings.security.api_secret_key,
    allowed_ips=settings.security.allowed_ips,
    signature_timeout=settings.security.signature_timeout,
    rate_limit_per_ip=settings.security.rate_limit_per_ip,
    rate_limit_per_user=settings.security.rate_limit_per_user
)

# 添加CORS中间件（仅在开发模式或配置了CORS源时）
if settings.debug or settings.security.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.security.cors_origins if settings.security.cors_origins else ["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

# 添加静态文件服务
app.mount(f"/{settings.storage.uploads_dir.name}", StaticFiles(directory=settings.storage.uploads_dir), name=settings.storage.uploads_dir.name)
app.mount(f"/{settings.storage.outputs_dir.name}", StaticFiles(directory=settings.storage.outputs_dir), name=settings.storage.outputs_dir.name)

# 注册路由
app.include_router(styles.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(files.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")

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
        "message": settings.app_name,
        "version": settings.version,
        "description": settings.description,
        "status": "running",
        "architecture": "银行级安全防护架构",
        "security_enabled": True,
        "available_styles": available_styles,
        "api_endpoints": {
            "styles": "/api/v1/styles",
            "tasks": "/api/v1/tasks",
            "files": "/api/v1/files",
            "health": "/health",
            "docs": "/docs" if settings.debug else None
        }
    }

@app.get("/health", response_model=HealthResponse)
async def health_check(request: Request):
    """健康检查"""
    try:
        style_count = request.app.state.style_registry.get_style_count()
        health_data = {
            "status": "ok",
            "message": "风格转换服务运行正常",
            "timestamp": time.time(),
            "version": request.app.state.settings.version,
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
                "version": settings.version,
                "security_enabled": True
            }
        )

@app.get("/security-info")
async def security_info():
    """安全信息端点（仅开发模式）"""
    if not settings.debug:
        return {"message": "仅开发模式可用"}
    
    return {
        "security_summary": settings.security.get_security_summary(),
        "environment": "development" if settings.debug else "production",
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
            "message": str(exc) if settings.debug else "请联系管理员",
            "timestamp": time.time(),
            "version": settings.version
        }
    )

def run_server():
    """启动服务器"""
    # 生产模式启动提示
    if settings.is_production():
        logger.warning("生产模式启动 - 确保已配置正确的安全密钥")
        logger.warning("请确保以下环境变量已正确设置:")
        logger.warning("- API_SECRET_KEY")
        logger.warning("- JWT_SECRET_KEY")
        logger.warning("- ALLOWED_IPS")
    
    # 启动服务器
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.debug,
        workers=settings.workers if settings.is_production() else 1
    )

if __name__ == "__main__":
    run_server() 