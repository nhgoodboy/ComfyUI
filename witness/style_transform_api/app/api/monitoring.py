"""
监控API端点

提供系统性能监控、统计和健康检查功能。
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from ..utils.monitoring import performance_monitor, log_performance_summary
from ..schemas.response import ErrorResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/monitoring", tags=["系统监控"])

@router.get("/health")
async def health_check():
    """
    健康检查端点
    
    返回系统健康状态和基本信息
    """
    try:
        # 获取基本指标
        metrics = performance_monitor.get_metrics()
        
        # 简单的健康检查
        health_status = {
            "status": "healthy",
            "timestamp": performance_monitor.get_timestamp(),
            "uptime_seconds": metrics.get("uptime_seconds", 0),
            "total_requests": metrics.get("total_requests", 0),
            "success_rate": metrics.get("success_rate", 100)
        }
        
        # 根据成功率判断健康状态
        if metrics.get("success_rate", 100) < 95:
            health_status["status"] = "degraded"
        elif metrics.get("success_rate", 100) < 90:
            health_status["status"] = "unhealthy"
        
        return health_status
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )

@router.get("/metrics")
async def get_metrics():
    """
    获取系统性能指标
    
    返回详细的性能统计信息
    """
    try:
        metrics = performance_monitor.get_metrics()
        return {
            "success": True,
            "metrics": metrics
        }
    except Exception as e:
        logger.error(f"获取指标失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="METRICS_QUERY_FAILED",
                error_message=str(e)
            ).dict()
        )

@router.get("/metrics/{endpoint}")
async def get_endpoint_metrics(endpoint: str):
    """
    获取特定端点的性能指标
    
    - **endpoint**: 端点路径
    """
    try:
        # 去掉前缀斜杠
        endpoint = endpoint.lstrip('/')
        
        metrics = performance_monitor.get_metrics(endpoint)
        
        if metrics.get("request_count", 0) == 0:
            return {
                "success": False,
                "message": f"未找到端点 {endpoint} 的指标数据"
            }
        
        return {
            "success": True,
            "metrics": metrics
        }
    except Exception as e:
        logger.error(f"获取端点指标失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="ENDPOINT_METRICS_QUERY_FAILED",
                error_message=str(e)
            ).dict()
        )

@router.get("/stats")
async def get_system_stats():
    """
    获取系统统计信息
    
    返回所有端点的统计信息
    """
    try:
        endpoint_stats = performance_monitor.get_endpoint_stats()
        global_metrics = performance_monitor.get_metrics()
        
        return {
            "success": True,
            "stats": {
                "global": global_metrics,
                "endpoints": endpoint_stats,
                "endpoint_count": len(endpoint_stats)
            }
        }
    except Exception as e:
        logger.error(f"获取系统统计失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="SYSTEM_STATS_QUERY_FAILED",
                error_message=str(e)
            ).dict()
        )

@router.get("/errors")
async def get_recent_errors(limit: int = 50):
    """
    获取最近的错误记录
    
    - **limit**: 返回记录数量限制（默认50，最大200）
    """
    try:
        # 限制查询数量
        limit = min(limit, 200)
        
        errors = performance_monitor.get_recent_errors(limit)
        
        return {
            "success": True,
            "errors": errors,
            "count": len(errors)
        }
    except Exception as e:
        logger.error(f"获取错误记录失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="ERRORS_QUERY_FAILED",
                error_message=str(e)
            ).dict()
        )

@router.get("/hourly-stats")
async def get_hourly_stats(hours: int = 24):
    """
    获取按小时统计的性能数据
    
    - **hours**: 查询时间范围（小时，默认24小时）
    """
    try:
        # 限制查询范围
        hours = min(hours, 168)  # 最大一周
        
        hourly_stats = performance_monitor.get_hourly_stats(hours)
        
        return {
            "success": True,
            "hourly_stats": hourly_stats,
            "hours": hours,
            "count": len(hourly_stats)
        }
    except Exception as e:
        logger.error(f"获取小时统计失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="HOURLY_STATS_QUERY_FAILED",
                error_message=str(e)
            ).dict()
        )

@router.get("/summary")
async def get_performance_summary():
    """
    获取性能摘要报告
    
    返回格式化的性能摘要信息
    """
    try:
        # 记录性能摘要到日志
        log_performance_summary()
        
        # 获取各种数据
        global_metrics = performance_monitor.get_metrics()
        endpoint_stats = performance_monitor.get_endpoint_stats()
        recent_errors = performance_monitor.get_recent_errors(10)
        
        # 计算一些摘要统计
        top_endpoints = sorted(
            endpoint_stats.items(),
            key=lambda x: x[1]["request_count"],
            reverse=True
        )[:5]
        
        error_rate_by_endpoint = {
            endpoint: stats["error_rate"]
            for endpoint, stats in endpoint_stats.items()
            if stats["error_rate"] > 0
        }
        
        return {
            "success": True,
            "summary": {
                "global_metrics": global_metrics,
                "top_endpoints": dict(top_endpoints),
                "error_rate_by_endpoint": error_rate_by_endpoint,
                "recent_errors_count": len(recent_errors),
                "total_endpoints": len(endpoint_stats)
            }
        }
    except Exception as e:
        logger.error(f"获取性能摘要失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="PERFORMANCE_SUMMARY_FAILED",
                error_message=str(e)
            ).dict()
        )

@router.post("/export")
async def export_monitoring_data():
    """
    导出监控数据
    
    返回完整的监控数据用于备份或分析
    """
    try:
        export_data = performance_monitor.export_data()
        
        return {
            "success": True,
            "data": export_data
        }
    except Exception as e:
        logger.error(f"导出监控数据失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="EXPORT_DATA_FAILED",
                error_message=str(e)
            ).dict()
        )

@router.post("/cleanup")
async def cleanup_old_data(max_age_hours: int = 24):
    """
    清理旧的监控数据
    
    - **max_age_hours**: 保留数据的最大时间（小时）
    """
    try:
        # 限制清理范围
        max_age_hours = max(1, min(max_age_hours, 168))  # 最少1小时，最多一周
        
        performance_monitor.cleanup_old_data(max_age_hours)
        
        return {
            "success": True,
            "message": f"已清理 {max_age_hours} 小时前的数据"
        }
    except Exception as e:
        logger.error(f"清理监控数据失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="CLEANUP_DATA_FAILED",
                error_message=str(e)
            ).dict()
        ) 