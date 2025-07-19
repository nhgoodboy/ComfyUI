"""
基于RPC的转换API接口

提供图像转换的REST API接口，内部调用RPC服务
"""

import time
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from starlette.websockets import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.services.transform_service import transform_service

logger = logging.getLogger(__name__)

# 创建API路由器
api_router = APIRouter(prefix="/api", tags=["转换API"])


# 响应模型
class StyleInfo(BaseModel):
    id: str
    name: str
    description: str
    estimated_time: int
    tags: List[str]


class TaskInfo(BaseModel):
    task_id: str
    user_id: str
    style_id: str
    status: str
    progress: float
    stage: str
    message: str
    created_at: float
    estimated_time: int = None
    file_info: Dict[str, Any] = None
    request_id: str = None


# WebSocket连接管理器
class ConnectionManager:
    """管理WebSocket连接"""
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket client connected: {client_id}")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket client disconnected: {client_id}")

    async def send_json(self, client_id: str, data: dict):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(data)
                return True
            except Exception as e:
                logger.warning(f"Failed to send message to client {client_id}: {e}")
                self.disconnect(client_id)
                return False
        else:
            logger.warning(f"Attempted to send message to disconnected client: {client_id}")
            return False

    def is_connected(self, client_id: str) -> bool:
        """检查客户端是否仍然连接"""
        return client_id in self.active_connections


# 全局连接管理器
manager = ConnectionManager()


@api_router.get("/styles", response_model=List[StyleInfo])
async def get_styles(request: Request):
    """获取所有可用风格"""
    try:
        # 确保session_id存在
        if "session_id" not in request.session:
            request.session["session_id"] = transform_service.get_session_id()
        
        await transform_service.initialize()
        styles = await transform_service.get_styles()
        return styles
    except Exception as e:
        logger.error(f"获取风格列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取风格列表失败: {str(e)}")


@api_router.get("/styles/search")
async def search_styles(request: Request, q: str):
    """搜索风格"""
    try:
        await transform_service.initialize()
        styles = await transform_service.search_styles(q)
        return {"styles": styles, "query": q}
    except Exception as e:
        logger.error(f"搜索风格失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索风格失败: {str(e)}")


@api_router.post("/transform", response_model=TaskInfo)
async def create_transform_task(
    request: Request,
    style_id: str = Form(...),
    file: UploadFile = File(...),
    request_id: str = Form(None)
):
    """
    创建图像转换任务
    
    Args:
        style_id: 风格ID
        file: 上传的图片文件
        request_id: 请求ID (可选)
    
    Returns:
        TaskInfo: 任务信息
    """
    try:
        # 确保session_id存在
        if "session_id" not in request.session:
            request.session["session_id"] = transform_service.get_session_id()
        
        # 验证文件类型
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="文件必须是图片格式")
        
        # 验证文件大小
        file_content = await file.read()
        if len(file_content) > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(status_code=400, detail="文件大小不能超过10MB")
        
        # 初始化服务
        await transform_service.initialize()
        
        # 设置连接管理器
        transform_service.set_connection_manager(manager)
        
        # 执行转换
        task_info = await transform_service.transform_image(
            file_content=file_content,
            filename=file.filename or "image.jpg",
            style_id=style_id,
            request_id=request_id
        )
        
        logger.info(f"转换任务创建成功: {task_info.get('task_id')}")
        return task_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建转换任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建转换任务失败: {str(e)}")


@api_router.get("/tasks/{task_id}", response_model=TaskInfo)
async def get_task_status(task_id: str):
    """获取任务状态"""
    try:
        await transform_service.initialize()
        task_info = await transform_service.get_task_status(task_id)
        return task_info
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")


@api_router.get("/tasks/{task_id}/result")
async def get_task_result(task_id: str):
    """获取任务结果"""
    try:
        await transform_service.initialize()
        result = await transform_service.get_task_result(task_id)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"获取任务结果失败: {e}")
        # 如果是任务未完成的错误，返回特定状态码
        if "尚不可用" in str(e) or "未完成" in str(e):
            raise HTTPException(status_code=202, detail="任务结果尚不可用")
        raise HTTPException(status_code=500, detail=f"获取任务结果失败: {str(e)}")


@api_router.get("/tasks")
async def list_tasks(limit: int = 50):
    """获取任务列表"""
    try:
        await transform_service.initialize()
        tasks = await transform_service.list_user_tasks(limit=limit)
        return {"success": True, "data": {"tasks": tasks, "total": len(tasks)}}
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")


@api_router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """取消任务"""
    try:
        await transform_service.initialize()
        success = await transform_service.cancel_task(task_id)
        
        if success:
            return {"success": True, "message": "任务已取消"}
        else:
            raise HTTPException(status_code=400, detail="任务无法取消")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")


@api_router.get("/health")
async def get_health():
    """获取系统健康状态"""
    try:
        await transform_service.initialize()
        health = await transform_service.get_system_health()
        return health
    except Exception as e:
        logger.error(f"获取健康状态失败: {e}")
        return {
            "status": "unhealthy", 
            "error": str(e),
            "timestamp": time.time()
        }


@api_router.get("/session")
async def get_session_info(request: Request):
    """获取会话信息"""
    # 确保session_id存在
    if "session_id" not in request.session:
        request.session["session_id"] = transform_service.get_session_id()
    
    return {
        "session_id": request.session["session_id"],
        "user_id": request.session["session_id"],
        "message": "会话信息"
    }


@api_router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket端点，用于实时通信"""
    await manager.connect(websocket, client_id)
    try:
        while True:
            # 等待来自客户端的消息
            try:
                data = await websocket.receive_text()
                # 可以处理心跳消息
                if data == "ping":
                    await websocket.send_text("pong")
            except:
                break
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(client_id)