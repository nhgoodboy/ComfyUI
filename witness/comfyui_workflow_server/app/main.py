"""
ComfyUI风格转换API主应用

极简化的图像风格转换服务
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import uvicorn

from .config import settings
from .api.v1 import styles, tasks, files
from .core.style_registry import style_registry
from .models.api_models import HealthResponse

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
    logger.info("启动ComfyUI风格转换服务器...")
    
    # 初始化风格注册系统
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
    
    logger.info("服务器启动完成")
    
    try:
        yield
    finally:
        # 关闭时执行
        logger.info("关闭服务...")
        logger.info("服务已关闭")

# 创建FastAPI应用
app = FastAPI(
    title="ComfyUI风格转换API",
    version="2.0.0",
    description="极简化的图像风格转换服务，基于配置驱动的架构",
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

# 添加静态文件服务
if Path("uploads").exists():
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

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
    
    # 记录请求开始
    logger.info(f"请求开始: {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        
        # 记录请求完成
        duration = time.time() - start_time
        logger.info(f"请求完成: {request.method} {request.url.path} - {response.status_code} - {duration:.3f}s")
        
        return response
    except Exception as e:
        # 记录请求错误
        duration = time.time() - start_time
        logger.error(f"请求失败: {request.method} {request.url.path} - {str(e)} - {duration:.3f}s")
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
        "message": "ComfyUI风格转换API",
        "version": "2.0.0",
        "status": "running",
        "architecture": "极简化配置驱动架构",
        "available_styles": available_styles,
        "api_endpoints": {
            "styles": "/api/v1/styles",
            "tasks": "/api/v1/tasks",
            "files": "/api/v1/files",
            "health": "/health",
            "docs": "/docs"
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
            "version": "2.0.0"
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
                "version": "2.0.0"
            }
        )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    logger.error(f"全局异常: {request.method} {request.url.path} - {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "服务器内部错误",
            "message": str(exc) if settings.DEBUG else "请联系管理员",
            "timestamp": time.time()
        }
    )

def run_server():
    """运行服务器"""
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        workers=settings.WORKERS,
        log_level=settings.LOG_LEVEL.lower(),
        reload=settings.DEBUG
    )

if __name__ == "__main__":
    run_server() 