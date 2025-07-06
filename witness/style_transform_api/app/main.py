import asyncio
import logging
from contextlib import asynccontextmanager
import sys
import os
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .config import settings
from .api.transform import router as transform_router
from .api.monitoring import router as monitoring_router
from .services.comfyui_service import comfyui_service
from .utils.task_manager import start_cleanup_task
from .utils.monitoring import performance_monitor, PerformanceTimer
from .schemas.response import ErrorResponse
from .middleware.validation import ValidationMiddleware
from .middleware.auth import APIKeyMiddleware
from .middleware.rate_limit import RateLimitMiddleware
from .exceptions import StyleTransformAPIException

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("启动图像风格变换API服务...")
    
    # 初始化ComfyUI服务, 不阻塞启动
    await comfyui_service.initialize()
    
    # 启动清理任务
    cleanup_task = asyncio.create_task(start_cleanup_task())
    logger.info("任务清理服务启动")
    
    try:
        yield
    finally:
        # 关闭时执行
        logger.info("关闭服务...")
        
        # 取消清理任务
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        
        # 停止性能监控器
        performance_monitor.stop()
        logger.info("性能监控器已停止")
        
        # 关闭ComfyUI服务
        await comfyui_service.close()
        logger.info("服务已关闭")

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="基于ComfyUI的图像风格变换API服务",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# 添加中间件（注意顺序很重要）
# 1. 限流中间件（最先执行）
app.add_middleware(RateLimitMiddleware)

# 2. 认证中间件
app.add_middleware(APIKeyMiddleware)

# 3. 输入验证中间件
app.add_middleware(ValidationMiddleware)

# 4. CORS中间件（最后执行）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 5. 性能监控中间件
@app.middleware("http")
async def performance_monitoring_middleware(request: Request, call_next):
    """性能监控中间件"""
    # 获取用户ID（如果有）
    user_id = getattr(request.state, 'user_id', None)
    
    # 记录请求开始
    with PerformanceTimer(
        endpoint=request.url.path,
        method=request.method,
        user_id=user_id
    ) as timer:
        try:
            response = await call_next(request)
            timer.set_status(response.status_code)
            return response
        except Exception as e:
            timer.set_status(500, str(e))
            raise

# 注册路由
app.include_router(transform_router)
app.include_router(monitoring_router)

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "图像风格变换API服务",
        "version": settings.APP_VERSION,
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        # 检查ComfyUI连接
        comfyui_connected = await comfyui_service.health_check()
        
        health_data = {
            "status": "healthy" if comfyui_connected else "degraded",
            "comfyui_connected": comfyui_connected,
            "api_version": settings.APP_VERSION,
            "timestamp": time.time()
        }
        
        if comfyui_connected:
            try:
                stats = await comfyui_service.client.system.get_system_stats()
                health_data["comfyui_stats"] = stats
            except Exception as e:
                logger.warning(f"获取ComfyUI统计信息失败: {e}")
        
        # 获取限流统计（如果中间件已加载）
        try:
            # 通过app的中间件栈获取限流中间件实例
            for middleware in app.user_middleware:
                if hasattr(middleware, 'cls') and middleware.cls.__name__ == 'RateLimitMiddleware':
                    # 获取中间件实例（需要通过内部方式，这里简化处理）
                    health_data["rate_limit_stats"] = {
                        "rate_limits_configured": True,
                        "ip_per_minute": 60,
                        "user_per_minute": 10
                    }
                    break
        except Exception as e:
            logger.warning(f"获取限流统计失败: {e}")
        
        return health_data
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "comfyui_connected": False,
                "error": str(e),
                "timestamp": time.time()
            }
        )

@app.exception_handler(StyleTransformAPIException)
async def api_exception_handler(request: Request, exc: StyleTransformAPIException):
    """API自定义异常处理"""
    logger.warning(f"API异常: {exc.error_code} - {exc.error_message}", exc_info=True)
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error_code=exc.error_code,
            error_message=exc.error_message,
            details={
                "path": str(request.url.path),
                "method": request.method,
                **exc.details
            }
        ).dict()
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error_code="INTERNAL_SERVER_ERROR",
            error_message="服务器内部错误",
            details={
                "path": str(request.url.path),
                "method": request.method,
                "exception_type": type(exc).__name__
            }
        ).dict()
    )

def run_server():
    """运行服务器"""
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        workers=settings.WORKERS,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )

if __name__ == "__main__":
    run_server() 