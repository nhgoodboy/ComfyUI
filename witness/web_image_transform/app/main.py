from fastapi import FastAPI, Request, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.sessions import SessionMiddleware
import uvicorn
import asyncio
from pathlib import Path
import time

from .config import settings
from app.api.transform_api import router as transform_router

# 创建FastAPI应用
app = FastAPI(
    title="Web Image Transform",
    description="一个安全代理客户端，用于与ComfyUI工作流服务器交互。",
    version="2.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加可信主机中间件
if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", settings.APP_HOST]
    )

# 添加会话中间件，用于区分不同浏览器用户
# 注意：SESSION_SECRET_KEY在生产环境中必须是一个长而随机的字符串
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET_KEY
)

# 设置静态文件和模板
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
app.mount("/outputs", StaticFiles(directory=settings.OUTPUT_DIR), name="outputs")

templates = Jinja2Templates(directory=BASE_DIR.parent / "templates")

# 包含API路由
app.include_router(transform_router)

# 主页路由
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """主页"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION
    })

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
        return JSONResponse(status_code=404, content={"error": "文件不存在"})
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"下载失败: {str(e)}"})

# 应用启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动事件。"""
    # 检查目录
    upload_dir = Path(settings.UPLOAD_DIR)
    output_dir = Path(settings.OUTPUT_DIR)
    
    if not upload_dir.exists():
        upload_dir.mkdir(parents=True, exist_ok=True)
    
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Web Image Transform 应用启动...")
    print(f"连接到主服务器: {settings.COMFYUI_WORKFLOW_SERVER_URL}")
    if settings.SESSION_SECRET_KEY == "your-web-app-session-secret-key":
        print("\n⚠️ 警告: 正在使用默认的 SESSION_SECRET_KEY。")
        print("为了安全，请在 .env 文件中设置一个随机的密钥。\n")

# 应用关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件。"""
    print("Web Image Transform 应用关闭。")

# 异常处理
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """404错误处理"""
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"error": "API端点不存在", "path": request.url.path})
    else:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "app_name": settings.APP_NAME,
            "app_version": settings.APP_VERSION
        })

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """500错误处理"""
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=500, content={"error": "内部服务器错误", "message": str(exc)})
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
        host=settings.APP_HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning"
    )

if __name__ == "__main__":
    run_dev_server() 