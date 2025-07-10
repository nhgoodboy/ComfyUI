import uuid
from fastapi import APIRouter, File, UploadFile, HTTPException, Form, Request
from fastapi.responses import JSONResponse
from starlette.websockets import WebSocket, WebSocketDisconnect
import logging
import asyncio

from app.services.transform_service import transform_service, manager

logger = logging.getLogger(__name__)

# 创建API路由器
api_router = APIRouter(prefix="/api/v1", tags=["transform"])

@api_router.get("/styles")
async def get_styles(request: Request):
    """
    获取可用的图像风格列表
    """
    try:
        # 从session获取session_id，如果没有则生成默认的
        session_id = request.session.get("session_id", "default_session")
        
        styles = await transform_service.get_styles(session_id)
        return {"styles": styles}
    except Exception as e:
        logger.error(f"获取风格失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取风格失败: {str(e)}")

@api_router.post("/transform")
async def transform_image(
    request: Request,
    style_id: str = Form(...),
    file: UploadFile = File(...)
):
    """
    转换图像风格
    """
    try:
        # 验证文件类型
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="只支持图像文件")
        
        # 读取文件内容
        file_content = await file.read()
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="文件内容为空")
        
        # 从session获取session_id和client_id
        session_id = request.session.get("session_id", "default_session")
        client_id = request.session.get("client_id", f"client_{session_id}")
        
        # 处理转换
        result = await transform_service.process_transform(
            session_id=session_id,
            client_id=client_id,
            style_id=style_id,
            file_content=file_content,
            filename=file.filename or "uploaded_image"
        )
        
        return JSONResponse(content={
            "success": True,
            "message": "转换任务已启动",
            "task_id": result["task_id"]
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"图像转换失败: {e}")
        raise HTTPException(status_code=500, detail=f"转换失败: {str(e)}")

@api_router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket连接端点，用于实时推送转换进度
    """
    try:
        await manager.connect(websocket, client_id)
        logger.info(f"WebSocket连接建立: {client_id}")
        
        # 保持连接活跃
        while True:
            try:
                # 等待客户端消息（心跳或其他）
                message = await websocket.receive_text()
                logger.debug(f"收到客户端消息: {client_id} -> {message}")
                
                # 简单的心跳响应
                if message == "ping":
                    await websocket.send_text("pong")
                    
            except WebSocketDisconnect:
                logger.info(f"WebSocket连接断开: {client_id}")
                break
            except Exception as e:
                logger.error(f"WebSocket处理消息时出错: {e}")
                break
    
    except Exception as e:
        logger.error(f"WebSocket连接出错: {e}")
    finally:
        manager.disconnect(client_id)

@api_router.get("/health")
async def health_check():
    """
    健康检查端点
    """
    return {"status": "ok", "message": "Web Image Transform API is running"} 