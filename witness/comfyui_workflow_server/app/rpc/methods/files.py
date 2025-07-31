"""
文件访问RPC方法

提供文件访问和信息获取的RPC接口
"""

import logging
import base64
from pathlib import Path
from typing import Dict, Any
from fastapi import Request

from ..router import rpc_method
from ..validator import RPCValidator
from ..exceptions import RPCError
from ..error_codes import ErrorCodes

logger = logging.getLogger(__name__)


@rpc_method("files.get_output_image")
async def get_output_image(params: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """获取输出图片（以base64编码返回）"""
    try:
        # 验证必需参数
        RPCValidator.validate_required_fields(params, ["filename"])
        
        filename = params["filename"]
        
        if not isinstance(filename, str) or not filename.strip():
            raise RPCError(
                code=ErrorCodes.INVALID_PARAMS,
                message="文件名不能为空",
                data={"field": "filename", "value": filename}
            )
        
        output_dir = Path("outputs")
        file_path = output_dir / filename.strip()
        
        if not file_path.exists():
            logger.warning(f"请求的文件不存在: {filename}")
            raise RPCError(
                code=ErrorCodes.NOT_FOUND,
                message="文件不存在",
                data={"filename": filename}
            )
        
        if not file_path.is_file():
            logger.warning(f"请求的路径不是文件: {filename}")
            raise RPCError(
                code=ErrorCodes.NOT_FOUND,
                message="不是有效文件",
                data={"filename": filename}
            )
        
        # 检查文件扩展名
        allowed_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp'}
        if file_path.suffix.lower() not in allowed_extensions:
            logger.warning(f"不支持的文件类型: {filename}")
            raise RPCError(
                code=ErrorCodes.INVALID_PARAMS,
                message="不支持的文件类型",
                data={"filename": filename, "extension": file_path.suffix.lower()}
            )
        
        # 确定MIME类型
        mime_type_map = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.webp': 'image/webp',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp'
        }
        
        media_type = mime_type_map.get(file_path.suffix.lower(), 'image/png')
        
        # 读取文件并转换为base64
        with open(file_path, 'rb') as f:
            file_data = f.read()
            file_base64 = base64.b64encode(file_data).decode('utf-8')
        
        logger.info(f"提供文件访问: {filename}")
        
        return {
            "filename": filename,
            "media_type": media_type,
            "size": len(file_data),
            "data": file_base64,
            "url": f"/api/files/output/{filename}",
            "static_url": f"/outputs/{filename}"
        }
        
    except RPCError:
        raise
    except Exception as e:
        logger.error(f"获取文件失败: {filename}, 错误: {e}", exc_info=True)
        raise RPCError(
            code=ErrorCodes.INTERNAL_ERROR,
            message="获取文件失败",
            data={"filename": params.get("filename", ""), "error": str(e)}
        )


@rpc_method("files.get_output_image_info")
async def get_output_image_info(params: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """获取输出图片信息"""
    try:
        # 验证必需参数
        RPCValidator.validate_required_fields(params, ["filename"])
        
        filename = params["filename"]
        
        if not isinstance(filename, str) or not filename.strip():
            raise RPCError(
                code=ErrorCodes.INVALID_PARAMS,
                message="文件名不能为空",
                data={"field": "filename", "value": filename}
            )
        
        output_dir = Path("outputs")
        file_path = output_dir / filename.strip()
        
        if not file_path.exists():
            raise RPCError(
                code=ErrorCodes.NOT_FOUND,
                message="文件不存在",
                data={"filename": filename}
            )
        
        if not file_path.is_file():
            raise RPCError(
                code=ErrorCodes.NOT_FOUND,
                message="不是有效文件",
                data={"filename": filename}
            )
        
        # 获取文件信息
        stat = file_path.stat()
        
        # 检查文件扩展名
        allowed_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp'}
        is_image = file_path.suffix.lower() in allowed_extensions
        
        # 确定MIME类型
        mime_type_map = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.webp': 'image/webp',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp'
        }
        
        media_type = mime_type_map.get(file_path.suffix.lower(), 'application/octet-stream')
        
        logger.info(f"获取文件信息: {filename}")
        
        return {
            "filename": filename,
            "size": stat.st_size,
            "created_time": stat.st_ctime,
            "modified_time": stat.st_mtime,
            "extension": file_path.suffix.lower(),
            "media_type": media_type,
            "is_image": is_image,
            "url": f"/api/files/output/{filename}",
            "static_url": f"/outputs/{filename}"
        }
        
    except RPCError:
        raise
    except Exception as e:
        logger.error(f"获取文件信息失败: {filename}, 错误: {e}", exc_info=True)
        raise RPCError(
            code=ErrorCodes.INTERNAL_ERROR,
            message="获取文件信息失败",
            data={"filename": params.get("filename", ""), "error": str(e)}
        )


@rpc_method("files.list_output_images")
async def list_output_images(params: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """列出所有输出图片"""
    try:
        # 可选参数
        limit = params.get("limit", 100)
        offset = params.get("offset", 0)
        pattern = params.get("pattern", "*")  # 文件名过滤模式
        
        # 验证参数
        if not isinstance(limit, int) or limit < 1 or limit > 1000:
            limit = 100
        if not isinstance(offset, int) or offset < 0:
            offset = 0
        if not isinstance(pattern, str):
            pattern = "*"
        
        output_dir = Path("outputs")
        
        if not output_dir.exists():
            return {
                "files": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
                "pattern": pattern
            }
        
        # 支持的图片扩展名
        allowed_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp'}
        
        # 获取所有匹配的图片文件
        all_files = []
        for file_path in output_dir.glob(pattern):
            if (file_path.is_file() and 
                file_path.suffix.lower() in allowed_extensions):
                
                stat = file_path.stat()
                all_files.append({
                    "filename": file_path.name,
                    "size": stat.st_size,
                    "created_time": stat.st_ctime,
                    "modified_time": stat.st_mtime,
                    "extension": file_path.suffix.lower(),
                    "url": f"/api/files/output/{file_path.name}",
                    "static_url": f"/outputs/{file_path.name}"
                })
        
        # 按修改时间排序（最新的在前）
        all_files.sort(key=lambda x: x["modified_time"], reverse=True)
        
        # 分页
        total = len(all_files)
        files = all_files[offset:offset + limit]
        
        logger.info(f"列出输出图片: 总数={total}, 返回={len(files)}, 偏移={offset}, 限制={limit}")
        
        return {
            "files": files,
            "total": total,
            "limit": limit,
            "offset": offset,
            "pattern": pattern,
            "has_more": offset + len(files) < total
        }
        
    except Exception as e:
        logger.error(f"列出输出图片失败: {e}", exc_info=True)
        raise RPCError(
            code=ErrorCodes.INTERNAL_ERROR,
            message="列出输出图片失败",
            data={"error": str(e)}
        )