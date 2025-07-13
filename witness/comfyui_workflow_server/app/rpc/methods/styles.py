"""
风格管理RPC方法

提供风格查询、搜索等功能
"""

import logging
from typing import Dict, Any, List
from fastapi import Request

from ..router import rpc_method
from ..validator import RPCValidator
from ..formatter import RPCFormatter
from ..exceptions import RPCError
from ..error_codes import ErrorCodes
from ...services.style_service import StyleService

logger = logging.getLogger(__name__)


@rpc_method("styles.list")
async def list_styles(params: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """获取所有可用风格"""
    try:
        # 获取风格服务
        style_service: StyleService = request.app.state.style_service
        
        # 获取所有风格
        styles = await style_service.get_all_styles()
        
        # 格式化风格信息
        formatted_styles = [
            RPCFormatter.format_style_info(style) for style in styles
        ]
        
        return {
            "styles": formatted_styles,
            "total": len(formatted_styles)
        }
        
    except Exception as e:
        logger.error(f"获取风格列表失败: {e}", exc_info=True)
        raise RPCError(
            code=ErrorCodes.INTERNAL_ERROR,
            message="获取风格列表失败",
            data={"error": str(e)}
        )


@rpc_method("styles.search")
async def search_styles(params: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """搜索风格"""
    try:
        # 验证参数
        RPCValidator.validate_required_fields(params, ["q"])
        
        query = params["q"]
        if not isinstance(query, str) or not query.strip():
            raise RPCError(
                code=ErrorCodes.INVALID_PARAMS,
                message="搜索关键词不能为空",
                data={"field": "q", "value": query}
            )
        
        # 获取风格服务
        style_service: StyleService = request.app.state.style_service
        
        # 搜索风格
        styles = await style_service.search_styles(query.strip())
        
        # 格式化风格信息
        formatted_styles = [
            RPCFormatter.format_style_info(style) for style in styles
        ]
        
        return {
            "styles": formatted_styles,
            "total": len(formatted_styles),
            "query": query.strip()
        }
        
    except RPCError:
        raise
    except Exception as e:
        logger.error(f"搜索风格失败: {e}", exc_info=True)
        raise RPCError(
            code=ErrorCodes.INTERNAL_ERROR,
            message="搜索风格失败",
            data={"error": str(e)}
        )


@rpc_method("styles.get")
async def get_style(params: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """获取特定风格详情"""
    try:
        # 验证参数
        RPCValidator.validate_required_fields(params, ["style_id"])
        
        style_id = params["style_id"]
        RPCValidator.validate_style_id(style_id)
        
        # 获取风格服务
        style_service: StyleService = request.app.state.style_service
        
        # 获取风格详情
        style = await style_service.get_style(style_id)
        
        if not style:
            raise RPCError(
                code=ErrorCodes.STYLE_NOT_FOUND,
                message=f"风格不存在: {style_id}",
                data={"style_id": style_id}
            )
        
        # 格式化风格信息
        return RPCFormatter.format_style_info(style)
        
    except RPCError:
        raise
    except Exception as e:
        logger.error(f"获取风格详情失败: {e}", exc_info=True)
        raise RPCError(
            code=ErrorCodes.INTERNAL_ERROR,
            message="获取风格详情失败",
            data={"error": str(e)}
        )