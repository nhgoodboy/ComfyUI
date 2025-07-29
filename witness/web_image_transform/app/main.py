import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.transform_api import api_router
from app.services.transform_service import transform_service

import asyncio
import logging

logger = logging.getLogger(__name__)

async def health_check_task():
    """定期健康检查任务"""
    while True:
        try:
            await asyncio.sleep(30)  # 每30秒检查一次
            await transform_service.check_and_reconnect_if_needed()
        except Exception as e:
            logger.error(f"健康检查任务异常: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理器"""
    # 启动时的操作
    print("🚀 启动 Web Image Transform 应用...")
    
    # 启动推送监听器
    await transform_service.start_push_listener()
    print("✅ 推送监听器已启动")
    
    # 启动健康检查任务
    health_task = asyncio.create_task(health_check_task())
    print("✅ 健康检查任务已启动")
    
    yield
    
    # 关闭时的操作
    print("🔄 关闭 Web Image Transform 应用...")
    
    # 停止健康检查任务
    health_task.cancel()
    try:
        await health_task
    except asyncio.CancelledError:
        pass
    print("✅ 健康检查任务已停止")
    
    await transform_service.stop_push_listener()
    print("✅ 推送监听器已停止")

def create_app() -> FastAPI:
    """创建FastAPI应用实例"""
    
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Web Image Transform - 使用ComfyUI工作流的图像风格转换服务",
        lifespan=lifespan
    )

    # 添加CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 添加Session中间件
    app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET_KEY)

    # 注册API路由
    app.include_router(api_router)

    # 设置静态文件
    if os.path.exists("app/static"):
        app.mount("/static", StaticFiles(directory="app/static"), name="static")
    
    # 设置上传和输出文件的静态访问
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
    app.mount("/outputs", StaticFiles(directory=settings.OUTPUT_DIR), name="outputs")

    # 设置模板
    if os.path.exists("templates"):
        templates = Jinja2Templates(directory="templates")

        @app.get("/", response_class=HTMLResponse)
        async def serve_index(request: Request):
            """提供主页面"""
            # 确保session中有user_id
            if "user_id" not in request.session:
                request.session["user_id"] = f"user-{int(time.time())}-{str(uuid.uuid4())[:8]}"
            
            return templates.TemplateResponse("index.html", {
                "request": request,
                "app_name": settings.APP_NAME,
                "user_id": request.session["user_id"]
            })

    return app

# 创建应用实例
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    ) 