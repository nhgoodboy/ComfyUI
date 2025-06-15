import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .config import settings
from .api.transform import router as transform_router
from .services.comfyui_service import comfyui_service
from .utils.task_manager import start_cleanup_task
from .schemas.response import ErrorResponse

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
    
    try:
        # 初始化ComfyUI服务
        await comfyui_service.initialize()
        logger.info("ComfyUI服务初始化完成")
        
        # 启动清理任务
        cleanup_task = asyncio.create_task(start_cleanup_task())
        logger.info("任务清理服务启动")
        
        yield
        
    except Exception as e:
        logger.error(f"服务启动失败: {e}")
        raise
    finally:
        # 关闭时执行
        logger.info("关闭服务...")
        
        # 取消清理任务
        if 'cleanup_task' in locals():
            cleanup_task.cancel()
            try:
                await cleanup_task
            except asyncio.CancelledError:
                pass
        
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

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(transform_router)

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
        stats = await comfyui_service.client.system.get_system_stats()
        
        return {
            "status": "healthy",
            "comfyui_connected": True,
            "comfyui_stats": stats
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "comfyui_connected": False,
                "error": str(e)
            }
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
            details={"path": str(request.url.path)}
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