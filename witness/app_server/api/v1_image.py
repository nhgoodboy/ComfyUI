from fastapi import APIRouter, HTTPException, File, UploadFile
from witness.app_server.models.image_processing import ImageUploadRequest, ImageProcessResponse, UserInfo
from witness.task_processor.queue_client import enqueue_image_task # 新增导入
import uuid

router = APIRouter()

@router.post("/process", response_model=ImageProcessResponse)
async def process_image(request: ImageUploadRequest):
    """
    接收图片数据和用户信息，将其提交到任务队列进行异步处理。

    - **image_data**: Base64 编码的图片字符串。
    - **workflow_name**: 要使用的工作流名称。
    - **user_info**: 包含 `user_id` 和可选 `user_group` 的用户信息。
    """
    task_id = str(uuid.uuid4())
    print(f"接收到来自用户 {request.user_info.user_id} 的图片处理请求，任务ID: {task_id}，工作流: {request.workflow_name}")

    # 使用 queue_client 将任务加入队列
    success = enqueue_image_task(
        task_id=task_id,
        image_data=request.image_data,
        workflow_name=request.workflow_name,
        user_info=request.user_info
    )

    if not success:
        raise HTTPException(status_code=500, detail="无法将任务加入处理队列。")

    return ImageProcessResponse(
        task_id=task_id,
        status="queued",
        message="图片处理任务已成功加入队列。"
    )

# 可以在这里添加一个简单的GET端点用于测试API是否在线
@router.get("/health")
async def health_check():
    return {"status": "API is healthy"}