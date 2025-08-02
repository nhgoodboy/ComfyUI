"""
ComfyUI工作流服务器主应用

RPC风格的微服务架构：专注于工作流处理的核心功能
"""

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, List, Any
import logging.config
import time

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException
from starlette.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# 导入配置
from app.config import get_settings, validate_config, AppConfig

# 导入RPC处理器
from app.rpc.handler import rpc_handler

# 导入并注册RPC方法（这会自动注册所有装饰的方法）
from app.rpc.methods import *

# 导入服务类
from app.core.workflow_registry import WorkflowRegistry
from app.services.comfyui_service import ComfyUIService
from app.services.workflow_task_service import WorkflowTaskService

# 导入WebSocket推送管理器
from app.utils.websocket_push import push_manager

# 服务实例将在lifespan中创建并附加到app.state
from app.models.api_models import HealthResponse

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

        logger.debug("正在初始化工作流注册表...")
        workflow_config_path = settings.storage.workflows_dir / "workflows.yaml"
        workflow_registry = WorkflowRegistry(
            config_file=str(workflow_config_path),
            comfyui_service=comfyui_service
        )
        app.state.workflow_registry = workflow_registry
        logger.info("工作流注册表初始化完成。")

        # RPC架构下专注于工作流处理
        # 文件访问和任务管理通过RPC方法提供

        logger.debug("正在初始化工作流任务服务...")
        workflow_task_service = WorkflowTaskService(
            comfyui_service=comfyui_service,
            workflow_registry=workflow_registry
        )
        app.state.workflow_task_service = workflow_task_service  # 标准服务状态名称
        logger.info("工作流任务服务初始化完成。")

        # --- 4. 挂载服务到 app.state ---
        logger.debug("正在将服务挂载到应用状态...")
        app.state.comfyui_service = comfyui_service
        app.state.workflow_registry = workflow_registry
        app.state.workflow_task_service = workflow_task_service  # 标准服务状态名称
        app.state.settings = settings  # 将配置也挂载到state
        
        # 注入依赖：将工作流任务服务实例提供给ComfyUIService
        comfyui_service.set_workflow_task_service(workflow_task_service)
        
        # 为工作流任务服务设置ComfyUI结果回调
        if hasattr(comfyui_service, 'add_result_callback'):
            comfyui_service.add_result_callback(workflow_task_service.on_comfyui_result)

        # 记录启动时间（用于系统统计）
        app.state.start_time = time.time()

        logger.info("服务挂载完成。")
        
        logger.info("应用启动流程成功完成。")
        yield
        
    except Exception as e:
        logger.error(f"应用启动过程中出现错误: {e}", exc_info=True)
        logger.warning("部分服务可能不可用，但应用将继续运行")
        # 确保基础状态仍然设置
        if not hasattr(app.state, 'settings'):
            app.state.settings = settings
        if not hasattr(app.state, 'start_time'):
            app.state.start_time = time.time()
        yield
        
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

# 添加静态文件服务用于输出图片访问
from fastapi.staticfiles import StaticFiles
import os

# 确保输出目录存在
outputs_dir = "outputs"
if not os.path.exists(outputs_dir):
    os.makedirs(outputs_dir)

# 确保上传目录存在（仅用于输入文件）
uploads_dir = "uploads"
if not os.path.exists(uploads_dir):
    os.makedirs(uploads_dir)

# 挂载输出目录为静态文件服务
app.mount("/outputs", StaticFiles(directory=outputs_dir), name="outputs")

# 文件访问功能已迁移到RPC方法中
# 使用 files.get_output_image, files.get_output_image_info, files.list_output_images 等RPC方法

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """请求日志中间件"""
    start_time = time.time()
    
    # 记录请求（过滤健康检查请求）
    if not (request.url.path == "/rpc" and request.method == "POST"):
        logger.info(f"请求开始: {request.method} {request.url}")
    
    response = await call_next(request)
    
    # 记录响应（过滤健康检查请求）
    process_time = time.time() - start_time
    if not (request.url.path == "/rpc" and request.method == "POST"):
        logger.info(f"请求完成: {request.method} {request.url} - {response.status_code} - {process_time:.3f}s")
    
    return response

@app.post("/rpc")
async def rpc_endpoint(request: Request):
    """RPC端点 - 处理所有RPC请求"""
    try:
        # 解析请求体
        body = await request.body()
        request_data = json.loads(body.decode('utf-8'))
        
        # 检查是否为批量请求
        if isinstance(request_data, list):
            # 批量请求
            responses = await rpc_handler.handle_batch_request(request, request_data)
            return JSONResponse(content=responses)
        else:
            # 单个请求
            response = await rpc_handler.handle_request(request, request_data)
            return JSONResponse(content=response)
            
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": 1001,
                    "message": "无效的JSON格式"
                },
                "id": None
            }
        )
    except Exception as e:
        logger.error(f"RPC端点异常: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": 1004,
                    "message": "内部服务器错误"
                },
                "id": None
            }
        )

@app.get("/")
async def root(request: Request):
    """根端点 - 提供API概览"""
    settings: AppConfig = request.app.state.settings
    
    return {
        "service": "ComfyUI Workflow Server", 
        "version": "2.0.0",
        "description": "RPC风格的ComfyUI工作流微服务",
        "environment": settings.environment,
        "comfyui_connected": hasattr(request.app.state, 'comfyui_service'),
        "api_docs": "/docs" if settings.debug else "禁用（生产模式）",
        "health_check": "/health",
        "rpc_endpoint": "/rpc",
        "websocket": "/ws/{client_id}",
        "available_methods": [
            "workflow.execute",
            "workflow.list",
            "workflow.get_schema",
            "workflow.get_status", 
            "workflow.get_result",
            "workflow.cancel",
            "workflow.search",
            "files.list_output_images",
            "files.get_output_image",
            "files.get_output_image_info",
            "system.health",
            "system.parse_filename",
            "system.get_stats"
            # 文件命名由客户端处理，任务管理通过工作流RPC方法提供
        ]
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
            # 使用正确的健康检查方法
            comfyui_healthy = await comfyui_service.health_check()
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

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket端点 - 为客户端提供实时工作流状态推送
    
    client_id 可以是:
    - request_id: 特定请求的连接
    - "workflow_test_system": 服务级连接
    """
    await push_manager.connect(websocket, client_id)
    try:
        while True:
            # 保持连接活跃，等待心跳或消息
            try:
                message = await websocket.receive_text()
                # 可以处理心跳消息
                if message == "ping":
                    await websocket.send_text("pong")
            except:
                break
    except WebSocketDisconnect:
        pass
    finally:
        push_manager.disconnect(client_id)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    logger.error(f"未处理的异常: {request.method} {request.url} - {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 1004,
                "message": "内部服务器错误", 
                "details": str(exc) if get_settings().debug else "请联系管理员"
            }
        }
    ) 