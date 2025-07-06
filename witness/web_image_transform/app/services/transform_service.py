import aiohttp
import asyncio
import time
import uuid
from typing import Dict, Any, Optional
from pathlib import Path
import aiofiles

from ..config import settings
from ..utils.logger import get_logger, log_transform_start, log_transform_complete, log_transform_error

logger = get_logger("transform_service")

# 风格类型到提示词的映射
STYLE_PROMPTS = {
    "clay": "Clay Style, lovely, 3d, cute",
    "anime": "anime style, vibrant colors, detailed",
    "watercolor": "watercolor painting style, soft colors, artistic",
    "oil_painting": "oil painting style, classical art, textured",
    "sketch": "pencil sketch style, black and white, artistic drawing",
    "cartoon": "cartoon style, colorful, animated",
    "realistic": "photorealistic, high quality, detailed",
    "fantasy": "fantasy art style, magical, ethereal"
}

class TransformService:
    """图像变换服务"""
    
    def __init__(self):
        self.api_base_url = settings.STYLE_API_BASE_URL
        self.session = None
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    async def upload_image(self, file_path: str) -> str:
        """上传图像文件到本地服务器并返回URL"""
        try:
            # 生成唯一文件名
            file_extension = Path(file_path).suffix
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            upload_path = Path(settings.UPLOAD_DIR) / unique_filename
            
            # 复制文件到上传目录
            async with aiofiles.open(file_path, 'rb') as src:
                async with aiofiles.open(upload_path, 'wb') as dst:
                    content = await src.read()
                    await dst.write(content)
            
            # 返回可访问的URL
            return f"http://{settings.HOST}:{settings.PORT}/uploads/{unique_filename}"
            
        except Exception as e:
            logger.error(f"上传图像失败: {e}")
            raise
    
    async def transform_image(self, image_url: str, style_type: str, 
                            custom_prompt: Optional[str] = None,
                            strength: float = 0.6) -> Dict[str, Any]:
        """提交图像变换任务"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # 确定风格提示词
            if custom_prompt:
                style_prompt = custom_prompt
            else:
                style_prompt = STYLE_PROMPTS.get(style_type, STYLE_PROMPTS["clay"])
            
            # 构建新的工作流API请求
            payload = {
                "workflow_id": "style_transform",
                "parameters": {
                    "image": image_url,
                    "style_prompt": style_prompt,
                    "strength": strength,
                    "steps": 20,
                    "cfg_scale": 7.0,
                    "negative_prompt": "bad quality, blurry, low resolution",
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "checkpoint": "sd_xl_base_1.0.safetensors"
                }
            }
            
            async with self.session.post(
                f"{self.api_base_url}/api/v1/workflows/style_transform/execute",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    task_id = result.get("data")  # 新API返回task_id在data字段中
                    if task_id:
                        log_transform_start(task_id, style_type, settings.DEFAULT_USER_ID)
                        return {"task_id": task_id}
                    else:
                        raise Exception("API响应中缺少任务ID")
                else:
                    error_text = await response.text()
                    raise Exception(f"API请求失败: {response.status} - {error_text}")
                    
        except Exception as e:
            logger.error(f"提交变换任务失败: {e}")
            raise
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """查询任务状态"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.get(
                f"{self.api_base_url}/api/v1/workflows/tasks/{task_id}",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    response_data = await response.json()
                    # 新API的响应格式
                    if response_data.get("success"):
                        task_data = response_data.get("data", {})
                        return {
                            "status": task_data.get("status"),
                            "progress": task_data.get("progress", 0),
                            "error_message": task_data.get("error_message"),
                            "task_id": task_id
                        }
                    else:
                        raise Exception(f"API返回错误: {response_data.get('error_message', '未知错误')}")
                else:
                    error_text = await response.text()
                    raise Exception(f"查询任务状态失败: {response.status} - {error_text}")
                    
        except Exception as e:
            logger.error(f"查询任务状态失败: {e}")
            raise
    
    async def get_task_result(self, task_id: str) -> Dict[str, Any]:
        """获取任务结果"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.get(
                f"{self.api_base_url}/api/v1/workflows/tasks/{task_id}/result",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    response_data = await response.json()
                    if response_data.get("success"):
                        return response_data.get("data", {})
                    else:
                        raise Exception(f"API返回错误: {response_data.get('error_message', '未知错误')}")
                else:
                    error_text = await response.text()
                    raise Exception(f"获取任务结果失败: {response.status} - {error_text}")
                    
        except Exception as e:
            logger.error(f"获取任务结果失败: {e}")
            raise
    
    async def wait_for_completion(self, api_task_id: str, 
                                web_task_id: str,
                                timeout: int = 300,
                                progress_callback=None) -> Dict[str, Any]:
        """等待任务完成"""
        start_time = time.time()
        
        try:
            while time.time() - start_time < timeout:
                try:
                    result = await self.get_task_status(api_task_id)
                except Exception as poll_err:
                    logger.warning(f"轮询任务 {api_task_id} 状态出错, 重试: {poll_err}")
                    await asyncio.sleep(2)
                    continue
                
                status = result.get("status")
                progress = result.get("progress", 0)
                
                # 调用进度回调
                if progress_callback:
                    await progress_callback(web_task_id, progress, status)
                
                if status == "completed":
                    duration = time.time() - start_time
                    
                    # 获取任务结果
                    try:
                        task_result = await self.get_task_result(api_task_id)
                        output_images = task_result.get("result", {}).get("output_images", [])
                        output_url = output_images[0] if output_images else None
                    except Exception as e:
                        logger.error(f"获取任务结果失败: {e}")
                        output_url = None
                    
                    log_transform_complete(api_task_id, duration, output_url or "unknown", settings.DEFAULT_USER_ID)
                    
                    return {
                        "status": "completed",
                        "output_image_url": output_url,
                        "task_id": api_task_id,
                        "progress": 1.0
                    }
                    
                elif status == "failed":
                    error_msg = result.get("error_message", "未知错误")
                    log_transform_error(api_task_id, error_msg, settings.DEFAULT_USER_ID)
                    return {
                        "status": "failed",
                        "error_message": error_msg,
                        "task_id": api_task_id,
                        "progress": 0
                    }
                
                await asyncio.sleep(2)  # 2秒轮询一次
            
            # 超时
            log_transform_error(api_task_id, "任务超时", settings.DEFAULT_USER_ID)
            return {
                "status": "failed",
                "error_message": "任务超时",
                "task_id": api_task_id,
                "progress": 0
            }
            
        except Exception as e:
            # 记录错误并返回失败结果，避免向 FastAPI 上传递裸 dict
            log_transform_error(api_task_id, str(e), settings.DEFAULT_USER_ID)
            return {
                "status": "failed",
                "error_message": str(e),
                "task_id": api_task_id,
                "progress": 0
            }
    
    async def download_result_image(self, image_url: str, task_id: str) -> str:
        """下载结果图像到本地"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # 生成本地文件路径
            file_extension = ".jpg"  # 默认扩展名
            if "." in image_url:
                file_extension = "." + image_url.split(".")[-1].split("?")[0]
            
            output_filename = f"result_{task_id}_{int(time.time())}{file_extension}"
            output_path = Path(settings.OUTPUT_DIR) / output_filename
            
            # 下载图像
            async with self.session.get(image_url) as response:
                if response.status == 200:
                    async with aiofiles.open(output_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                    
                    logger.info(f"结果图像已保存: {output_path}")
                    return str(output_path)
                else:
                    raise Exception(f"下载图像失败: {response.status}")
                    
        except Exception as e:
            logger.error(f"下载结果图像失败: {e}")
            raise
    
    async def get_api_health(self) -> Dict[str, Any]:
        """检查API服务健康状态"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.get(
                f"{self.api_base_url}/health",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {
                        "status": "unhealthy",
                        "error": f"HTTP {response.status}"
                    }
                    
        except Exception as e:
            logger.error(f"检查API健康状态失败: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def get_available_workflows(self) -> Dict[str, Any]:
        """获取可用的工作流列表"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.get(
                f"{self.api_base_url}/api/v1/workflows/",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    response_data = await response.json()
                    if response_data.get("success"):
                        return response_data.get("data", [])
                    else:
                        raise Exception(f"API返回错误: {response_data.get('error_message', '未知错误')}")
                else:
                    error_text = await response.text()
                    raise Exception(f"获取工作流列表失败: {response.status} - {error_text}")
                    
        except Exception as e:
            logger.error(f"获取工作流列表失败: {e}")
            return []
    
    async def get_api_stats(self) -> Dict[str, Any]:
        """获取API统计信息"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.get(
                f"{self.api_base_url}/api/v1/workflows/statistics",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    response_data = await response.json()
                    if response_data.get("success"):
                        return response_data.get("data", {})
                    else:
                        return {"error": response_data.get("error_message", "未知错误")}
                else:
                    return {"error": f"HTTP {response.status}"}
                    
        except Exception as e:
            logger.error(f"获取API统计信息失败: {e}")
            return {"error": str(e)}


# 异步函数保持向后兼容
async def transform_image_async(image_path: str, style_type: str,
                              web_task_id: str,
                              custom_prompt: Optional[str] = None,
                              strength: float = 0.6,
                              progress_callback=None) -> Dict[str, Any]:
    """
    异步图像变换函数
    
    Args:
        image_path: 本地图像文件路径
        style_type: 风格类型
        web_task_id: Web任务ID（用于追踪）
        custom_prompt: 自定义提示词
        strength: 变换强度
        progress_callback: 进度回调函数
        
    Returns:
        变换结果字典
    """
    async with TransformService() as service:
        try:
            # 1. 上传图像
            image_url = await service.upload_image(image_path)
            
            # 2. 提交变换任务
            submit_result = await service.transform_image(
                image_url=image_url,
                style_type=style_type,
                custom_prompt=custom_prompt,
                strength=strength
            )
            
            api_task_id = submit_result["task_id"]
            
            # 3. 等待完成
            result = await service.wait_for_completion(
                api_task_id=api_task_id,
                web_task_id=web_task_id,
                progress_callback=progress_callback
            )
            
            return result
            
        except Exception as e:
            logger.error(f"图像变换异步处理失败: {e}")
            return {
                "status": "failed",
                "error_message": str(e),
                "task_id": web_task_id,
                "progress": 0
            }

# 全局服务实例
transform_service = TransformService()

# 便捷函数
async def transform_image_async(image_path: str, style_type: str,
                              web_task_id: str,
                              custom_prompt: Optional[str] = None,
                              strength: float = 0.6,
                              progress_callback=None) -> Dict[str, Any]:
    """异步图像变换完整流程"""
    async with TransformService() as service:
        try:
            # 1. 上传图像
            image_url = await service.upload_image(image_path)
            logger.info(f"图像已上传: {image_url}")
            
            # 2. 提交变换任务
            result = await service.transform_image(
                image_url, style_type, custom_prompt, strength
            )
            api_task_id = result.get("task_id")
            
            if not api_task_id:
                raise Exception("未获取到任务ID")
            
            # 3. 等待完成
            final_result = await service.wait_for_completion(
                api_task_id, web_task_id=web_task_id, progress_callback=progress_callback
            )
            
            # 4. 下载结果图像
            output_url = final_result.get("output_image_url")
            if output_url:
                local_path = await service.download_result_image(output_url, api_task_id)
                final_result["local_output_path"] = local_path
            
            return final_result
            
        except Exception as e:
            logger.error(f"图像变换流程失败: {e}")
            raise 