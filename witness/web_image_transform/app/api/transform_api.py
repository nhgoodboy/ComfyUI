"""
基于RPC的转换API接口

提供图像转换的REST API接口，内部调用RPC服务
"""

import time
import logging
from typing import List, Dict, Any, Optional
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
    request_id: str
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
        # 维护user_id到request_id的映射，支持一个用户有多个任务
        self.user_tasks: Dict[str, set] = {}  # user_id -> {request_id1, request_id2, ...}
        # 维护request_id到user_id的反向映射
        self.task_owners: Dict[str, str] = {}  # request_id -> user_id

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        if user_id not in self.user_tasks:
            self.user_tasks[user_id] = set()
        logger.info(f"WebSocket user connected: {user_id}")

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            # 清理任务映射
            if user_id in self.user_tasks:
                # 清理反向映射
                for request_id in self.user_tasks[user_id]:
                    if request_id in self.task_owners:
                        del self.task_owners[request_id]
                del self.user_tasks[user_id]
            logger.info(f"WebSocket user disconnected: {user_id}")

    def register_task(self, user_id: str, request_id: str):
        """注册任务归属关系"""
        if user_id not in self.user_tasks:
            self.user_tasks[user_id] = set()
        self.user_tasks[user_id].add(request_id)
        self.task_owners[request_id] = user_id
        logger.info(f"Task {request_id} registered to user {user_id}")

    def get_task_owner(self, request_id: str) -> Optional[str]:
        """获取任务的所有者user_id"""
        return self.task_owners.get(request_id)

    async def send_json(self, user_id: str, data: dict):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(data)
                return True
            except Exception as e:
                logger.warning(f"Failed to send message to user {user_id}: {e}")
                self.disconnect(user_id)
                return False
        else:
            logger.warning(f"Attempted to send message to disconnected user: {user_id}")
            return False

    async def send_to_task_owner(self, request_id: str, data: dict) -> bool:
        """发送消息给特定任务的所有者"""
        owner_user_id = self.get_task_owner(request_id)
        if owner_user_id:
            logger.info(f"发送任务更新到所有者 {owner_user_id}: {request_id}")
            return await self.send_json(owner_user_id, data)
        else:
            logger.warning(f"任务 {request_id} 没有找到所有者，当前任务映射: {dict(self.task_owners)}")
            return False

    def is_connected(self, user_id: str) -> bool:
        """检查用户是否仍然连接"""
        return user_id in self.active_connections


# 全局连接管理器
manager = ConnectionManager()


@api_router.get("/styles", response_model=List[StyleInfo])
async def get_styles(request: Request, user_id: str = None):
    """获取所有可用风格"""
    try:
        # 如果没有提供user_id，使用默认的
        if not user_id:
            user_id = "default_user"
        
        styles = await transform_service.get_styles(user_id)
        return styles
    except Exception as e:
        logger.error(f"获取风格列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取风格列表失败: {str(e)}")


@api_router.get("/styles/search")
async def search_styles(request: Request, q: str, user_id: str = None):
    """搜索风格"""
    try:
        # 如果没有提供user_id，使用默认的
        if not user_id:
            user_id = "default_user"
        
        styles = await transform_service.search_styles(user_id, q)
        return {"styles": styles, "query": q}
    except Exception as e:
        logger.error(f"搜索风格失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索风格失败: {str(e)}")


@api_router.post("/transform", response_model=TaskInfo)
async def create_transform_task(
    request: Request,
    style_id: str = Form(...),
    file: UploadFile = File(...),
    request_id: str = Form(None),
    user_id: str = Form(...)  # 改为user_id参数
):
    """
    创建图像转换任务
    
    Args:
        style_id: 风格ID
        file: 上传的图片文件
        request_id: 请求ID (可选)
        user_id: 用户ID (必需)
    
    Returns:
        TaskInfo: 任务信息
    """
    try:
        # 验证文件类型
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="文件必须是图片格式")
        
        # 验证文件大小
        file_content = await file.read()
        if len(file_content) > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(status_code=400, detail="文件大小不能超过10MB")
        
        # 初始化服务（如果尚未初始化）
        if not transform_service.rpc_client:
            await transform_service.initialize()
        
        # 设置连接管理器
        transform_service.set_connection_manager(manager)
        
        # 注册用户到前端客户端的映射
        transform_service.register_user(user_id, user_id)
        
        # 添加调试日志
        logger.info(f"API接收到的user_id: {user_id}")
        
        # 执行转换
        task_info = await transform_service.transform_image(
            user_id=user_id,
            file_content=file_content,
            filename=file.filename or "image.jpg",
            style_id=style_id,
            request_id=request_id
        )
        
        logger.info(f"用户 {user_id} 的转换任务创建成功: {task_info.get('request_id')}")
        return task_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建转换任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建转换任务失败: {str(e)}")


@api_router.get("/tasks/{request_id}", response_model=TaskInfo)
async def get_task_status(request_id: str, user_id: str = None):
    """获取任务状态"""
    try:
        # 如果没有提供user_id，使用默认的
        if not user_id:
            user_id = "default_user"
        
        task_info = await transform_service.get_task_status(user_id, request_id)
        return task_info
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")


@api_router.get("/tasks/{request_id}/result")
async def get_task_result(request_id: str, user_id: str = None):
    """获取任务结果"""
    try:
        # 如果没有提供user_id，使用默认的
        if not user_id:
            user_id = "default_user"
        
        result = await transform_service.get_task_result(user_id, request_id)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"获取任务结果失败: {e}")
        # 如果是任务未完成的错误，返回特定状态码
        if "尚不可用" in str(e) or "未完成" in str(e):
            raise HTTPException(status_code=202, detail="任务结果尚不可用")
        raise HTTPException(status_code=500, detail=f"获取任务结果失败: {str(e)}")


@api_router.get("/tasks")
async def list_tasks(limit: int = 50, user_id: str = None):
    """获取任务列表"""
    try:
        # 如果没有提供user_id，使用默认的
        if not user_id:
            user_id = "default_user"
        
        tasks = await transform_service.list_user_tasks(user_id, limit=limit)
        return {"success": True, "data": {"tasks": tasks, "total": len(tasks)}}
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")


@api_router.delete("/tasks/{request_id}")
async def cancel_task(request_id: str, user_id: str = None):
    """取消任务"""
    try:
        # 如果没有提供user_id，使用默认的
        if not user_id:
            user_id = "default_user"
        
        success = await transform_service.cancel_task(user_id, request_id)
        
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
    import uuid
    
    # 确保user_id存在（与main.py保持一致）
    if "user_id" not in request.session:
        request.session["user_id"] = f"user-{int(time.time())}-{str(uuid.uuid4()).replace('-', '')[:8]}"
    
    return {
        "session_id": request.session["user_id"],  # 为了向后兼容
        "user_id": request.session["user_id"],
        "message": "会话信息"
    }


@api_router.get("/session/reset")
async def reset_session(request: Request):
    """重置会话信息 - 强制生成新的用户ID"""
    import uuid
    
    # 强制重新生成用户ID
    request.session["user_id"] = f"user-{int(time.time())}-{str(uuid.uuid4()).replace('-', '')[:8]}"
    
    return {
        "message": "会话已重置",
        "new_user_id": request.session["user_id"]
    }


@api_router.get("/debug/connections")
async def get_debug_connections():
    """调试端点：查看当前连接和任务映射状态"""
    return {
        "active_connections": list(manager.active_connections.keys()),
        "user_tasks": {k: list(v) for k, v in manager.user_tasks.items()},
        "task_owners": dict(manager.task_owners),
        "total_connections": len(manager.active_connections),
        "total_tasks": len(manager.task_owners)
    }


@api_router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket端点，用于实时通信"""
    await manager.connect(websocket, user_id)
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
        manager.disconnect(user_id)