"""
监控工具模块

提供性能监控、统计收集和指标计算功能。
"""

import time
import asyncio
import logging
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    request_count: int = 0
    total_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    error_count: int = 0
    success_count: int = 0
    
    @property
    def avg_response_time(self) -> float:
        """平均响应时间"""
        if self.request_count == 0:
            return 0.0
        return self.total_response_time / self.request_count
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.request_count == 0:
            return 0.0
        return (self.success_count / self.request_count) * 100
    
    @property
    def error_rate(self) -> float:
        """错误率"""
        if self.request_count == 0:
            return 0.0
        return (self.error_count / self.request_count) * 100

@dataclass
class RequestRecord:
    """请求记录"""
    timestamp: float
    endpoint: str
    method: str
    status_code: int
    response_time: float
    user_id: Optional[str] = None
    error_message: Optional[str] = None

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, max_records: int = 10000):
        self.max_records = max_records
        self.records: deque = deque(maxlen=max_records)
        self.metrics_by_endpoint: Dict[str, PerformanceMetrics] = defaultdict(PerformanceMetrics)
        self.metrics_by_hour: Dict[str, PerformanceMetrics] = defaultdict(PerformanceMetrics)
        self.start_time = time.time()
        self._lock = threading.Lock()
        
        # 启动定期清理任务
        self._cleanup_task = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """启动定期清理任务"""
        try:
            loop = asyncio.get_running_loop()
            self._cleanup_task = loop.create_task(self._periodic_cleanup())
        except RuntimeError:
            # 没有运行中的事件循环，延迟启动
            pass
    
    async def _periodic_cleanup(self):
        """定期清理过期数据"""
        while True:
            try:
                await asyncio.sleep(3600)  # 每小时清理一次
                self.cleanup_old_data()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"清理任务失败: {e}")
    
    def record_request(self, endpoint: str, method: str, status_code: int, 
                      response_time: float, user_id: Optional[str] = None,
                      error_message: Optional[str] = None):
        """记录请求"""
        with self._lock:
            timestamp = time.time()
            
            # 创建请求记录
            record = RequestRecord(
                timestamp=timestamp,
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                response_time=response_time,
                user_id=user_id,
                error_message=error_message
            )
            
            self.records.append(record)
            
            # 更新端点指标
            self._update_metrics(self.metrics_by_endpoint[endpoint], record)
            
            # 更新小时指标
            hour_key = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d_%H')
            self._update_metrics(self.metrics_by_hour[hour_key], record)
    
    def _update_metrics(self, metrics: PerformanceMetrics, record: RequestRecord):
        """更新指标"""
        metrics.request_count += 1
        metrics.total_response_time += record.response_time
        metrics.min_response_time = min(metrics.min_response_time, record.response_time)
        metrics.max_response_time = max(metrics.max_response_time, record.response_time)
        
        if 200 <= record.status_code < 300:
            metrics.success_count += 1
        else:
            metrics.error_count += 1
    
    def get_metrics(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """获取指标"""
        with self._lock:
            if endpoint:
                metrics = self.metrics_by_endpoint.get(endpoint, PerformanceMetrics())
                return {
                    "endpoint": endpoint,
                    "request_count": metrics.request_count,
                    "avg_response_time": round(metrics.avg_response_time, 3),
                    "min_response_time": round(metrics.min_response_time, 3) if metrics.min_response_time != float('inf') else 0,
                    "max_response_time": round(metrics.max_response_time, 3),
                    "success_rate": round(metrics.success_rate, 2),
                    "error_rate": round(metrics.error_rate, 2)
                }
            else:
                # 全局指标
                total_metrics = PerformanceMetrics()
                for metrics in self.metrics_by_endpoint.values():
                    total_metrics.request_count += metrics.request_count
                    total_metrics.total_response_time += metrics.total_response_time
                    total_metrics.min_response_time = min(total_metrics.min_response_time, metrics.min_response_time)
                    total_metrics.max_response_time = max(total_metrics.max_response_time, metrics.max_response_time)
                    total_metrics.success_count += metrics.success_count
                    total_metrics.error_count += metrics.error_count
                
                uptime = time.time() - self.start_time
                
                return {
                    "uptime_seconds": round(uptime, 2),
                    "total_requests": total_metrics.request_count,
                    "avg_response_time": round(total_metrics.avg_response_time, 3),
                    "min_response_time": round(total_metrics.min_response_time, 3) if total_metrics.min_response_time != float('inf') else 0,
                    "max_response_time": round(total_metrics.max_response_time, 3),
                    "success_rate": round(total_metrics.success_rate, 2),
                    "error_rate": round(total_metrics.error_rate, 2),
                    "requests_per_second": round(total_metrics.request_count / uptime, 2) if uptime > 0 else 0
                }
    
    def get_endpoint_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有端点统计"""
        with self._lock:
            return {
                endpoint: self.get_metrics(endpoint)
                for endpoint in self.metrics_by_endpoint.keys()
            }
    
    def get_recent_errors(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取最近的错误记录"""
        with self._lock:
            errors = [
                {
                    "timestamp": datetime.fromtimestamp(record.timestamp).isoformat(),
                    "endpoint": record.endpoint,
                    "method": record.method,
                    "status_code": record.status_code,
                    "response_time": record.response_time,
                    "user_id": record.user_id,
                    "error_message": record.error_message
                }
                for record in reversed(self.records)
                if record.status_code >= 400
            ][:limit]
            
            return errors
    
    def get_hourly_stats(self, hours: int = 24) -> Dict[str, Dict[str, Any]]:
        """获取小时统计"""
        with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            cutoff_hour = cutoff_time.strftime('%Y-%m-%d_%H')
            
            relevant_hours = {
                hour: metrics for hour, metrics in self.metrics_by_hour.items()
                if hour >= cutoff_hour
            }
            
            return {
                hour: {
                    "hour": hour,
                    "request_count": metrics.request_count,
                    "avg_response_time": round(metrics.avg_response_time, 3),
                    "success_rate": round(metrics.success_rate, 2),
                    "error_rate": round(metrics.error_rate, 2)
                }
                for hour, metrics in sorted(relevant_hours.items())
            }
    
    def cleanup_old_data(self, max_age_hours: int = 24):
        """清理旧数据"""
        with self._lock:
            cutoff_time = time.time() - (max_age_hours * 3600)
            
            # 清理旧的小时统计
            cutoff_hour = datetime.fromtimestamp(cutoff_time).strftime('%Y-%m-%d_%H')
            old_hours = [hour for hour in self.metrics_by_hour.keys() if hour < cutoff_hour]
            
            for hour in old_hours:
                del self.metrics_by_hour[hour]
            
            logger.info(f"清理了 {len(old_hours)} 个过期的小时统计")
    
    def export_data(self) -> Dict[str, Any]:
        """导出所有监控数据"""
        with self._lock:
            return {
                "global_metrics": self.get_metrics(),
                "endpoint_stats": self.get_endpoint_stats(),
                "hourly_stats": self.get_hourly_stats(),
                "recent_errors": self.get_recent_errors(),
                "uptime_seconds": time.time() - self.start_time,
                "export_timestamp": datetime.now().isoformat()
            }
    
    def stop(self):
        """停止监控器"""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()

# 全局监控器实例
performance_monitor = PerformanceMonitor()

class PerformanceTimer:
    """性能计时器上下文管理器"""
    
    def __init__(self, endpoint: str, method: str, user_id: Optional[str] = None):
        self.endpoint = endpoint
        self.method = method
        self.user_id = user_id
        self.start_time = None
        self.status_code = 200
        self.error_message = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            response_time = time.time() - self.start_time
            
            if exc_type is not None:
                self.status_code = 500
                self.error_message = str(exc_val)
            
            performance_monitor.record_request(
                endpoint=self.endpoint,
                method=self.method,
                status_code=self.status_code,
                response_time=response_time,
                user_id=self.user_id,
                error_message=self.error_message
            )
    
    def set_status(self, status_code: int, error_message: Optional[str] = None):
        """设置状态码和错误信息"""
        self.status_code = status_code
        self.error_message = error_message

def log_performance_summary():
    """记录性能摘要到日志"""
    try:
        metrics = performance_monitor.get_metrics()
        endpoint_stats = performance_monitor.get_endpoint_stats()
        
        logger.info("=== 性能监控摘要 ===")
        logger.info(f"总请求数: {metrics['total_requests']}")
        logger.info(f"平均响应时间: {metrics['avg_response_time']}ms")
        logger.info(f"成功率: {metrics['success_rate']}%")
        logger.info(f"每秒请求数: {metrics['requests_per_second']}")
        
        if endpoint_stats:
            logger.info("端点统计:")
            for endpoint, stats in endpoint_stats.items():
                logger.info(f"  {endpoint}: {stats['request_count']} 请求, "
                          f"{stats['avg_response_time']}ms 平均响应时间, "
                          f"{stats['success_rate']}% 成功率")
        
    except Exception as e:
        logger.error(f"记录性能摘要失败: {e}")

# 在模块导入时启动清理任务
def _start_monitor():
    """启动监控器"""
    try:
        loop = asyncio.get_running_loop()
        if not performance_monitor._cleanup_task:
            performance_monitor._start_cleanup_task()
    except RuntimeError:
        # 没有运行中的事件循环
        pass

# 注册在应用启动时调用
_start_monitor() 