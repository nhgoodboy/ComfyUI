from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class StyleType(str, Enum):
    """风格类型枚举"""
    CLAY = "clay"
    ANIME = "anime"
    REALISTIC = "realistic"
    CARTOON = "cartoon"
    OIL_PAINTING = "oil_painting"

class TransformRequest(BaseModel):
    """图像风格变换请求模型"""
    user_id: str = Field(..., description="用户ID")
    image_url: str = Field(..., description="输入图像的URL")
    style_type: StyleType = Field(default=StyleType.CLAY, description="风格类型")
    custom_prompt: Optional[str] = Field(None, description="自定义风格提示词")
    strength: Optional[float] = Field(0.6, ge=0.1, le=1.0, description="变换强度")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "user_12345",
                "image_url": "https://example.com/input.jpg",
                "style_type": "clay",
                "custom_prompt": "Clay Style, lovely, 3d, cute",
                "strength": 0.6
            }
        }

class BatchTransformRequest(BaseModel):
    """批量图像变换请求模型"""
    user_id: str = Field(..., description="用户ID")
    image_urls: list[str] = Field(..., min_items=1, max_items=10, description="输入图像URL列表")
    style_type: StyleType = Field(default=StyleType.CLAY, description="风格类型")
    custom_prompt: Optional[str] = Field(None, description="自定义风格提示词")
    strength: Optional[float] = Field(0.6, ge=0.1, le=1.0, description="变换强度") 