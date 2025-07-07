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
import logging.config

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
from .core.style_registry import StyleRegistry
from .services.comfyui_service import ComfyUIService
from .services.user_file_service import UserFileService
from .services.user_task_service import UserTaskService
from .services.user_service import UserService
from .services.style_service import StyleService
from .services.jwt_service import JWTService, init_jwt_service, get_jwt_service
from .utils.crypto_utils import CryptoUtils, init_crypto_utils, get_crypto_utils

# 服务实例将在lifespan中创建并附加到app.state
from .models.api_models import HealthResponse, ApiResponse

# 日志将在lifespan中配置
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # --- 1. 初始化配置 ---
    logger.info("应用启动流程开始...")
    settings = get_settings()
    logger.info("配置加载完成。")
    
    # --- 2. 配置日志 ---
    logging.config.dictConfig(settings.get_logging_config())
    logger.info("日志配置完成。")
    
    try:
        # --- 3. 启动时初始化 ---
        logger.info("服务初始化开始...")
        
        # # 初始化数据库
        # logger.debug("正在初始化数据库...")
        # await init_db()
        # logger.info("数据库初始化完成。")

        # 初始化服务
        logger.debug("正在初始化 ComfyUI 服务...")
        comfyui_service = ComfyUIService()
        await comfyui_service.initialize()
        logger.info("ComfyUI 服务初始化完成。")

        logger.debug("正在初始化样式注册表...")
        style_registry = StyleRegistry(
            config_file=str(settings.style_config_path),
            comfyui_service=comfyui_service
        )
        app.state.style_registry = style_registry
        logger.info("样式注册表初始化完成。")

        logger.debug("正在初始化用户文件服务...")
        user_file_service = UserFileService(
            base_upload_dir=settings.storage.uploads_dir,
            base_output_dir=settings.storage.outputs_dir
        )
        app.state.user_file_service = user_file_service
        logger.info("用户文件服务初始化完成。")
        
        logger.debug("正在初始化用户任务服务...")
        user_task_service = UserTaskService(
            comfyui_service=comfyui_service,
            style_registry=style_registry
        )
        app.state.user_task_service = user_task_service
        logger.info("用户任务服务初始化完成。")
        
        logger.debug("正在初始化JWT服务...")
        jwt_service = init_jwt_service(
            secret_key=settings.security.jwt_secret_key,
            token_expiry_minutes=settings.security.token_expiry_minutes
        )
        logger.info("JWT服务初始化完成。")
        
        logger.debug("正在初始化用户服务...")
        user_service = UserService(api_users=settings.security.api_users)
        app.state.user_service = user_service
        logger.info("用户服务初始化完成。")

        logger.debug("正在初始化加密工具...")
        crypto_utils = CryptoUtils(secret_key=settings.security.api_secret_key)
        logger.info("加密工具初始化完成。")

        logger.debug("正在初始化样式服务...")
        style_service = StyleService(style_registry=style_registry)
        logger.info("样式服务初始化完成。")

        # --- 4. 挂载服务到 app.state ---
        logger.debug("正在将服务挂载到应用状态...")
        app.state.comfyui_service = comfyui_service
        app.state.style_registry = style_registry
        app.state.user_file_service = user_file_service
        app.state.user_task_service = user_task_service
        app.state.jwt_service = jwt_service
        app.state.user_service = user_service
        app.state.crypto_utils = crypto_utils
        app.state.style_service = style_service
        app.state.settings = settings  # 将配置也挂载到state

        # 注入依赖：将UserTaskService实例提供给ComfyUIService用于回调
        comfyui_service.set_user_task_service(user_task_service)

        logger.info("服务挂载完成。")
        
        logger.info("应用启动流程成功完成。")
        yield
        
    except Exception as e:
        logger.critical(f"应用启动失败: {e}", exc_info=True)
        # 可以在这里添加清理逻辑
        
    finally:
        # --- 5. 关闭时清理 ---
        logger.info("应用关闭流程开始...")
        if hasattr(app.state, 'comfyui_service') and app.state.comfyui_service:
            await app.state.comfyui_service.close()
            logger.info("ComfyUI 服务已关闭。")
        
        # await close_db()
        # logger.info("数据库连接已关闭。")
        logger.info("应用关闭流程完成。")

# 在lifespan之外获取配置，用于FastAPI应用和中间件的初始化
# get_settings() 是带缓存的，所以不会重复创建实例
settings = get_settings()

# 创建FastAPI应用
fastapi_config = settings.get_fastapi_config()
app = FastAPI(
    **fastapi_config,
    lifespan=lifespan
)

# 添加中间件 - 安全第一
app.add_middleware(
    SecurityMiddleware,
    api_users=settings.security.api_users,
    api_secret_key=settings.security.api_secret_key,
    allowed_ips=settings.security.allowed_ips,
    signature_timeout=settings.security.signature_timeout
)
app.add_middleware(RateLimitMiddleware)

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
async def root(request: Request):
    """根路径"""
    try:
        styles_list = request.app.state.style_registry.get_all_styles()
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
            health_data["available_styles"] = [style.id for style in request.app.state.style_registry.get_all_styles()]
        else:
            health_data["warning"] = "未加载任何风格"
        
        return HealthResponse(**health_data)
        
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
    """全局异常处理器"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ApiResponse(
            success=False, 
            error="Internal Server Error",
            data=None
        ).model_dump()
    ) 