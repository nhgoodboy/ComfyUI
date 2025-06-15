from fastapi import FastAPI, Request, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn
import asyncio
from pathlib import Path
import time

from .config import settings
from .api.web_api import router as web_api_router
from .api.websocket import websocket_endpoint, start_task_monitor
from .utils.logger import get_logger, log_request, log_response

# 初始化日志
logger = get_logger("main")

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="网页版图像风格变换测试平台",
    debug=settings.DEBUG
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加可信主机中间件
if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", settings.HOST]
    )

# 设置静态文件和模板
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
app.mount("/outputs", StaticFiles(directory=settings.OUTPUT_DIR), name="outputs")

templates = Jinja2Templates(directory="templates")

# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录HTTP请求日志"""
    start_time = time.time()
    request_id = f"req_{int(start_time * 1000)}"
    
    # 记录请求开始
    log_request(request_id, request.method, str(request.url.path))
    
    # 处理请求
    response = await call_next(request)
    
    # 记录请求完成
    duration = time.time() - start_time
    log_response(request_id, response.status_code, duration)
    
    return response

# 包含API路由
app.include_router(web_api_router)

# 主页路由
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """主页"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION
    })

# WebSocket路由
@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    """WebSocket连接端点"""
    await websocket_endpoint(websocket)

# 健康检查路由
@app.get("/health")
async def health():
    """简单健康检查"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": time.time()
    }

# 文件下载路由
@app.get("/download/{filename}")
async def download_file(filename: str):
    """下载文件"""
    try:
        # 检查上传目录
        upload_file = Path(settings.UPLOAD_DIR) / filename
        if upload_file.exists():
            return FileResponse(
                path=upload_file,
                filename=filename,
                media_type='application/octet-stream'
            )
        
        # 检查输出目录
        output_file = Path(settings.OUTPUT_DIR) / filename
        if output_file.exists():
            return FileResponse(
                path=output_file,
                filename=filename,
                media_type='application/octet-stream'
            )
        
        # 文件不存在
        return {"error": "文件不存在"}
        
    except Exception as e:
        logger.error(f"下载文件失败: {e}")
        return {"error": f"下载失败: {str(e)}"}

# 应用启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    logger.info(f"启动 {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"调试模式: {settings.DEBUG}")
    logger.info(f"监听地址: {settings.HOST}:{settings.PORT}")
    
    # 启动任务监控
    start_task_monitor()
    logger.info("任务进度监控已启动")
    
    # 检查目录
    upload_dir = Path(settings.UPLOAD_DIR)
    output_dir = Path(settings.OUTPUT_DIR)
    
    if not upload_dir.exists():
        upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"创建上传目录: {upload_dir}")
    
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"创建输出目录: {output_dir}")
    
    logger.info("应用启动完成")

# 应用关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    logger.info("应用正在关闭...")
    
    # 这里可以添加清理逻辑
    # 例如：关闭数据库连接、清理临时文件等
    
    logger.info("应用已关闭")

# 异常处理
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """404错误处理"""
    if request.url.path.startswith("/api/"):
        return {"error": "API端点不存在", "path": request.url.path}
    else:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "app_name": settings.APP_NAME,
            "app_version": settings.APP_VERSION
        })

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """500错误处理"""
    logger.error(f"内部服务器错误: {exc}")
    
    if request.url.path.startswith("/api/"):
        return {"error": "内部服务器错误", "message": str(exc)}
    else:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "app_name": settings.APP_NAME,
            "app_version": settings.APP_VERSION,
            "error": "服务器内部错误，请稍后重试"
        })

# 开发服务器启动函数
def run_dev_server():
    """启动开发服务器"""
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning"
    )

if __name__ == "__main__":
    run_dev_server() 