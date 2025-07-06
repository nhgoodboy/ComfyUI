import uuid
from fastapi import APIRouter, Request, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.services.transform_service import transform_service, manager

# 创建API路由
router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """渲染主页面。"""
    # 确保每个浏览器会话都有一个唯一的ID
    if "session_id" not in request.session:
        request.session["session_id"] = str(uuid.uuid4())
    return templates.TemplateResponse("index.html", {"request": request})

@router.get("/api/styles")
async def get_styles(request: Request):
    """获取可用风格列表。"""
    try:
        session_id = request.session["session_id"]
        styles = await transform_service.get_styles(session_id)
        return JSONResponse(content=styles)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.post("/api/transform")
async def create_transform(
    request: Request,
    style_id: str = Form(...),
    client_id: str = Form(...),
    image: UploadFile = File(...)
):
    """接收转换请求，启动处理流程。"""
    try:
        session_id = request.session["session_id"]
        contents = await image.read()
        
        # 非阻塞地启动后台任务
        task = await transform_service.process_transform(
            session_id=session_id,
            client_id=client_id,
            style_id=style_id,
            file_content=contents,
            filename=image.filename
        )
        return JSONResponse(content={"message": "任务已开始处理", "task_id": task['task_id']})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """处理WebSocket连接。"""
    await manager.connect(websocket, client_id)
    try:
        while True:
            # 保持连接打开以接收服务器推送
            # 客户端不需要发送消息，只需监听
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(client_id) 