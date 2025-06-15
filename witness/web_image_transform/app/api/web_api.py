from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uuid
import time
import asyncio
from pathlib import Path

from ..services.file_service import file_service
from ..services.transform_service import transform_service, transform_image_async
from ..utils.logger import get_logger, log_request, log_response
from ..config import settings

logger = get_logger("web_api")
router = APIRouter(prefix="/api", tags=["web"])

# 请求模型
class TransformRequest(BaseModel):
    """图像变换请求模型"""
    filename: str
    style_type: str
    custom_prompt: Optional[str] = None
    strength: float = 0.6

class TaskStatusResponse(BaseModel):
    """任务状态响应模型"""
    success: bool
    task_id: str
    status: str
    progress: float
    message: str
    output_url: Optional[str] = None
    duration: Optional[float] = None
    error_message: Optional[str] = None

# 全局任务存储（生产环境应使用Redis等）
active_tasks: Dict[str, Dict[str, Any]] = {}

@router.get("/health")
async def health_check():
    """健康检查端点"""
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        log_request(request_id, "GET", "/api/health")
        
        # 检查风格变换API状态
        api_health = await transform_service.get_api_health()
        
        response_data = {
            "success": True,
            "message": "Web服务正常运行",
            "timestamp": time.time(),
            "api_status": api_health.get("status", "unknown"),
            "version": settings.APP_VERSION
        }
        
        duration = time.time() - start_time
        log_response(request_id, 200, duration)
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        duration = time.time() - start_time
        log_response(request_id, 500, duration)
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"服务异常: {str(e)}"
            }
        )

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """文件上传端点"""
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        log_request(request_id, "POST", "/api/upload")
        
        # 读取文件内容
        file_content = await file.read()
        
        # 保存文件
        result = await file_service.save_uploaded_file(file_content, file.filename)
        
        duration = time.time() - start_time
        log_response(request_id, 200, duration)
        
        return JSONResponse(content=result)
        
    except ValueError as e:
        logger.warning(f"文件上传验证失败: {e}")
        duration = time.time() - start_time
        log_response(request_id, 400, duration)
        
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": str(e)
            }
        )
        
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        duration = time.time() - start_time
        log_response(request_id, 500, duration)
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"上传失败: {str(e)}"
            }
        )

@router.post("/transform")
async def start_transform(request: TransformRequest):
    """开始图像变换"""
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        log_request(request_id, "POST", "/api/transform")
        
        # 验证文件是否存在
        file_info = await file_service.get_file_info(request.filename)
        if not file_info:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 创建任务记录
        active_tasks[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "progress": 0.0,
            "message": "任务已创建",
            "start_time": time.time(),
            "file_path": file_info["file_path"],
            "style_type": request.style_type,
            "custom_prompt": request.custom_prompt,
            "strength": request.strength
        }
        
        # 异步启动变换任务
        asyncio.create_task(process_transform_task(task_id))
        
        duration = time.time() - start_time
        log_response(request_id, 200, duration)
        
        return JSONResponse(content={
            "success": True,
            "task_id": task_id,
            "message": "任务已提交"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提交变换任务失败: {e}")
        duration = time.time() - start_time
        log_response(request_id, 500, duration)
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"提交任务失败: {str(e)}"
            }
        )

async def process_transform_task(task_id: str):
    """处理图像变换任务"""
    try:
        task = active_tasks.get(task_id)
        if not task:
            logger.error(f"任务不存在: {task_id}")
            return
        
        # 更新任务状态
        task["status"] = "processing"
        task["progress"] = 10.0
        task["message"] = "开始处理..."
        
        # 定义进度回调函数
        async def progress_callback(web_task_id, progress, status):
            if web_task_id in active_tasks:
                active_tasks[web_task_id]["progress"] = progress
                active_tasks[web_task_id]["message"] = f"处理中... {progress:.1f}%"
        
        # 执行图像变换
        result = await transform_image_async(
            image_path=task["file_path"],
            style_type=task["style_type"],
            custom_prompt=task["custom_prompt"],
            strength=task["strength"],
            web_task_id=task_id,
            progress_callback=progress_callback
        )
        
        # 更新任务完成状态
        task["status"] = "completed"
        task["progress"] = 100.0
        task["message"] = "处理完成"
        task["output_url"] = f"/outputs/{Path(result['local_output_path']).name}"
        task["duration"] = time.time() - task["start_time"]
        task["end_time"] = time.time()
        
        logger.info(f"任务完成: {task_id}")
        
    except Exception as e:
        logger.error(f"处理任务失败 {task_id}: {e}")
        
        # 更新任务错误状态
        if task_id in active_tasks:
            active_tasks[task_id]["status"] = "failed"
            active_tasks[task_id]["progress"] = 0.0
            active_tasks[task_id]["message"] = f"处理失败: {str(e)}"
            active_tasks[task_id]["error_message"] = str(e)
            active_tasks[task_id]["end_time"] = time.time()

@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """查询任务状态"""
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        log_request(request_id, "GET", f"/api/task/{task_id}")
        
        task = active_tasks.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        response_data = TaskStatusResponse(
            success=True,
            task_id=task_id,
            status=task["status"],
            progress=task["progress"],
            message=task["message"],
            output_url=task.get("output_url"),
            duration=task.get("duration"),
            error_message=task.get("error_message")
        )
        
        duration = time.time() - start_time
        log_response(request_id, 200, duration)
        
        return JSONResponse(content=response_data.dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询任务状态失败: {e}")
        duration = time.time() - start_time
        log_response(request_id, 500, duration)
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"查询失败: {str(e)}"
            }
        )

@router.get("/files")
async def list_files(directory: str = "uploads", limit: int = 100):
    """列出文件"""
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        log_request(request_id, "GET", f"/api/files?directory={directory}")
        
        files = await file_service.list_files(directory, limit)
        
        duration = time.time() - start_time
        log_response(request_id, 200, duration)
        
        return JSONResponse(content={
            "success": True,
            "files": files,
            "count": len(files)
        })
        
    except Exception as e:
        logger.error(f"列出文件失败: {e}")
        duration = time.time() - start_time
        log_response(request_id, 500, duration)
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"列出文件失败: {str(e)}"
            }
        )

@router.delete("/files/{filename}")
async def delete_file(filename: str):
    """删除文件"""
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        log_request(request_id, "DELETE", f"/api/files/{filename}")
        
        success = await file_service.delete_file(filename)
        
        duration = time.time() - start_time
        log_response(request_id, 200 if success else 404, duration)
        
        if success:
            return JSONResponse(content={
                "success": True,
                "message": "文件已删除"
            })
        else:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "文件不存在"
                }
            )
        
    except Exception as e:
        logger.error(f"删除文件失败: {e}")
        duration = time.time() - start_time
        log_response(request_id, 500, duration)
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"删除失败: {str(e)}"
            }
        )

@router.get("/stats")
async def get_system_stats():
    """获取系统统计信息"""
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        log_request(request_id, "GET", "/api/stats")
        
        # 获取存储统计
        storage_stats = await file_service.get_storage_stats()
        
        # 获取任务统计
        total_tasks = len(active_tasks)
        completed_tasks = len([t for t in active_tasks.values() if t["status"] == "completed"])
        failed_tasks = len([t for t in active_tasks.values() if t["status"] == "failed"])
        
        success_rate = f"{(completed_tasks / total_tasks * 100):.1f}%" if total_tasks > 0 else "0%"
        
        # 计算平均处理时间
        completed_durations = [t.get("duration", 0) for t in active_tasks.values() 
                             if t["status"] == "completed" and t.get("duration")]
        avg_duration = f"{sum(completed_durations) / len(completed_durations):.1f}" if completed_durations else "0"
        
        # 获取API统计
        api_stats = await transform_service.get_api_stats()
        
        stats = {
            "upload_files": storage_stats.get("upload_dir", {}).get("file_count", 0),
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "success_rate": success_rate,
            "avg_duration": avg_duration,
            "storage_used": f"{storage_stats.get('total', {}).get('total_size_mb', 0)}MB",
            "api_status": api_stats.get("success", False),
            "api_latency": "0"  # 这里可以添加实际的API延迟测量
        }
        
        duration = time.time() - start_time
        log_response(request_id, 200, duration)
        
        return JSONResponse(content={
            "success": True,
            "stats": stats
        })
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        duration = time.time() - start_time
        log_response(request_id, 500, duration)
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"获取统计失败: {str(e)}"
            }
        )

@router.get("/logs")
async def get_recent_logs(limit: int = 100):
    """获取最近的日志"""
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        log_request(request_id, "GET", f"/api/logs?limit={limit}")
        
        # 这里简化处理，实际应该读取日志文件
        logs = [
            {
                "timestamp": "2024-01-01 12:00:00",
                "level": "INFO",
                "message": "系统启动完成"
            },
            {
                "timestamp": "2024-01-01 12:01:00",
                "level": "INFO",
                "message": "API服务正常运行"
            }
        ]
        
        duration = time.time() - start_time
        log_response(request_id, 200, duration)
        
        return JSONResponse(content={
            "success": True,
            "logs": logs
        })
        
    except Exception as e:
        logger.error(f"获取日志失败: {e}")
        duration = time.time() - start_time
        log_response(request_id, 500, duration)
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"获取日志失败: {str(e)}"
            }
        )

@router.post("/cleanup")
async def cleanup_old_files(max_age_hours: int = 24):
    """清理旧文件"""
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        log_request(request_id, "POST", f"/api/cleanup?max_age_hours={max_age_hours}")
        
        deleted_count = await file_service.cleanup_old_files(max_age_hours)
        
        # 清理旧任务记录
        current_time = time.time()
        old_tasks = [
            task_id for task_id, task in active_tasks.items()
            if task.get("end_time", current_time) < current_time - (max_age_hours * 3600)
        ]
        
        for task_id in old_tasks:
            del active_tasks[task_id]
        
        duration = time.time() - start_time
        log_response(request_id, 200, duration)
        
        return JSONResponse(content={
            "success": True,
            "deleted_files": deleted_count,
            "deleted_tasks": len(old_tasks),
            "message": f"清理完成，删除了 {deleted_count} 个文件和 {len(old_tasks)} 个任务记录"
        })
        
    except Exception as e:
        logger.error(f"清理失败: {e}")
        duration = time.time() - start_time
        log_response(request_id, 500, duration)
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"清理失败: {str(e)}"
            }
        ) 