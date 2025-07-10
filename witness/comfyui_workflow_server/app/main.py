"""
ComfyUI工作流服务器主应用

简化的微服务架构：专注于图像风格转换的核心功能
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, List
import logging.config

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# 导入配置
from .config import get_settings, validate_config, AppConfig

# 导入API路由
from .api.v1 import v1_router

# 导入服务类
from .core.style_registry import StyleRegistry
from .services.comfyui_service import ComfyUIService
from .services.user_file_service import UserFileService
from .services.user_task_service import UserTaskService
from .services.style_service import StyleService

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

        # 初始化服务
        logger.debug("正在初始化 ComfyUI 服务...")
        comfyui_service = ComfyUIService()
        await comfyui_service.initialize()
        logger.info("ComfyUI 服务初始化完成。")

        logger.debug("正在初始化样式注册表...")
        style_config_path = settings.storage.configs_dir / "style_configs.yaml"
        style_registry = StyleRegistry(
            config_file=str(style_config_path),
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

        logger.debug("正在初始化样式服务...")
        style_service = StyleService(style_registry=style_registry)
        logger.info("样式服务初始化完成。")

        # --- 4. 挂载服务到 app.state ---
        logger.debug("正在将服务挂载到应用状态...")
        app.state.comfyui_service = comfyui_service
        app.state.style_registry = style_registry
        app.state.user_file_service = user_file_service
        app.state.user_task_service = user_task_service
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
        
        logger.info("应用关闭流程完成。")

# 在lifespan之外获取配置，用于FastAPI应用的初始化
# get_settings() 是带缓存的，所以不会重复创建实例
settings = get_settings()

# 创建FastAPI应用
fastapi_config = settings.get_fastapi_config()
app = FastAPI(
    **fastapi_config,
    lifespan=lifespan
)

# 添加CORS中间件（简化）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# 添加静态文件服务
app.mount(f"/{settings.storage.uploads_dir.name}", StaticFiles(directory=settings.storage.uploads_dir), name=settings.storage.uploads_dir.name)
app.mount(f"/{settings.storage.outputs_dir.name}", StaticFiles(directory=settings.storage.outputs_dir), name=settings.storage.outputs_dir.name)

# 注册路由
app.include_router(v1_router, prefix="/api/v1")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """请求日志中间件"""
    start_time = time.time()
    
    # 记录请求
    logger.info(f"请求开始: {request.method} {request.url}")
    
    response = await call_next(request)
    
    # 记录响应
    process_time = time.time() - start_time
    logger.info(f"请求完成: {request.method} {request.url} - {response.status_code} - {process_time:.3f}s")
    
    return response

@app.get("/")
async def root(request: Request):
    """根端点 - 提供API概览"""
    settings: AppConfig = request.app.state.settings
    
    return {
        "service": "ComfyUI Workflow Server",
        "version": "2.0.0",
        "description": "简化的ComfyUI工作流微服务",
        "environment": settings.environment,
        "comfyui_connected": hasattr(request.app.state, 'comfyui_service'),
        "api_docs": "/docs" if settings.debug else "禁用（生产模式）",
        "health_check": "/health",
        "endpoints": {
            "styles": "/api/v1/styles",
            "user_tasks": "/api/v1/users/{user_id}/tasks",
            "user_files": "/api/v1/users/{user_id}/files"
        }
    }

@app.get("/health", response_model=HealthResponse)
async def health_check(request: Request):
    """健康检查端点"""
    settings: AppConfig = request.app.state.settings
    
    # 检查ComfyUI连接
    comfyui_healthy = False
    comfyui_error = None
    
    try:
        if hasattr(request.app.state, 'comfyui_service'):
            comfyui_service: ComfyUIService = request.app.state.comfyui_service
            # 简单的健康检查
            comfyui_healthy = comfyui_service._client_id is not None
    except Exception as e:
        comfyui_error = str(e)
    
    # 检查存储目录
    storage_healthy = (
        settings.storage.uploads_dir.exists() and 
        settings.storage.outputs_dir.exists()
    )
    
    overall_status = "healthy" if comfyui_healthy and storage_healthy else "unhealthy"
    
    return HealthResponse(
        status=overall_status,
        timestamp=time.time(),
        services={
            "comfyui": "healthy" if comfyui_healthy else "unhealthy",
            "storage": "healthy" if storage_healthy else "unhealthy"
        },
        details={
            "comfyui_url": settings.comfyui.base_url,
            "comfyui_error": comfyui_error,
            "storage_paths": {
                "uploads": str(settings.storage.uploads_dir),
                "outputs": str(settings.storage.outputs_dir)
            }
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    logger.error(f"未处理的异常: {request.method} {request.url} - {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "内部服务器错误",
            "detail": "请联系管理员" if not settings.debug else str(exc)
        }
    ) 