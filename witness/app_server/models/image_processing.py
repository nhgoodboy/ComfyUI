from pydantic import BaseModel
from typing import Optional

class UserInfo(BaseModel):
    """用户基本信息模型"""
    user_id: str
    user_group: Optional[str] = None

class ImageUploadRequest(BaseModel):
    """图片上传请求模型"""
    image_data: str  # Base64 编码的图片数据
    workflow_name: str  # 要使用的工作流名称，例如 'style_change'
    user_info: UserInfo

class ImageProcessResponse(BaseModel):
    """图片处理任务响应模型"""
    task_id: str
    status: str
    message: str