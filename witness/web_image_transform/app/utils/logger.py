import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Optional
import json
from ..config import settings

class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    # 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[32m',     # 绿色
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',    # 红色
        'CRITICAL': '\033[35m', # 紫色
        'RESET': '\033[0m'      # 重置
    }
    
    def format(self, record):
        # 添加颜色
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
        
        # 格式化消息
        formatted = super().format(record)
        return formatted

class JSONFormatter(logging.Formatter):
    """JSON格式化器，用于结构化日志"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # 添加异常信息
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # 添加额外字段
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'task_id'):
            log_entry['task_id'] = record.task_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
            
        return json.dumps(log_entry, ensure_ascii=False)

class WebTransformLogger:
    """网页图像变换日志管理器"""
    
    def __init__(self):
        self.loggers = {}
        self._setup_root_logger()
    
    def _setup_root_logger(self):
        """设置根日志器"""
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
        
        # 清除现有处理器
        root_logger.handlers.clear()
        
        # 控制台处理器（彩色输出）
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
        console_formatter = ColoredFormatter(settings.LOG_FORMAT)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # 文件处理器（轮转日志）
        file_handler = logging.handlers.RotatingFileHandler(
            settings.LOG_FILE,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(settings.LOG_FORMAT)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # JSON日志处理器（用于日志分析）
        json_log_file = settings.LOG_FILE.replace('.log', '.json')
        json_handler = logging.handlers.RotatingFileHandler(
            json_log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        json_handler.setLevel(logging.INFO)
        json_formatter = JSONFormatter()
        json_handler.setFormatter(json_formatter)
        root_logger.addHandler(json_handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """获取指定名称的日志器"""
        if name not in self.loggers:
            logger = logging.getLogger(name)
            self.loggers[name] = logger
        return self.loggers[name]
    
    def log_request(self, request_id: str, method: str, path: str, 
                   user_id: Optional[str] = None):
        """记录请求日志"""
        logger = self.get_logger("web.request")
        extra = {'request_id': request_id}
        if user_id:
            extra['user_id'] = user_id
        
        logger.info(f"请求开始: {method} {path}", extra=extra)
    
    def log_response(self, request_id: str, status_code: int, 
                    duration: float, user_id: Optional[str] = None):
        """记录响应日志"""
        logger = self.get_logger("web.response")
        extra = {'request_id': request_id}
        if user_id:
            extra['user_id'] = user_id
        
        logger.info(f"请求完成: {status_code} ({duration:.3f}s)", extra=extra)
    
    def log_file_upload(self, filename: str, file_size: int, 
                       user_id: Optional[str] = None):
        """记录文件上传日志"""
        logger = self.get_logger("web.upload")
        extra = {}
        if user_id:
            extra['user_id'] = user_id
        
        logger.info(f"文件上传: {filename} ({file_size} bytes)", extra=extra)
    
    def log_transform_start(self, task_id: str, style_type: str, 
                          user_id: Optional[str] = None):
        """记录变换开始日志"""
        logger = self.get_logger("web.transform")
        extra = {'task_id': task_id}
        if user_id:
            extra['user_id'] = user_id
        
        logger.info(f"图像变换开始: {style_type}", extra=extra)
    
    def log_transform_progress(self, task_id: str, progress: float,
                             user_id: Optional[str] = None):
        """记录变换进度日志"""
        logger = self.get_logger("web.transform")
        extra = {'task_id': task_id}
        if user_id:
            extra['user_id'] = user_id
        
        logger.debug(f"变换进度: {progress:.1f}%", extra=extra)
    
    def log_transform_complete(self, task_id: str, duration: float,
                             output_path: str, user_id: Optional[str] = None):
        """记录变换完成日志"""
        logger = self.get_logger("web.transform")
        extra = {'task_id': task_id}
        if user_id:
            extra['user_id'] = user_id
        
        logger.info(f"图像变换完成: {output_path} ({duration:.3f}s)", extra=extra)
    
    def log_transform_error(self, task_id: str, error: str,
                          user_id: Optional[str] = None):
        """记录变换错误日志"""
        logger = self.get_logger("web.transform")
        extra = {'task_id': task_id}
        if user_id:
            extra['user_id'] = user_id
        
        logger.error(f"图像变换失败: {error}", extra=extra)
    
    def log_websocket_connect(self, client_id: str):
        """记录WebSocket连接日志"""
        logger = self.get_logger("web.websocket")
        logger.info(f"WebSocket连接: {client_id}")
    
    def log_websocket_disconnect(self, client_id: str):
        """记录WebSocket断开日志"""
        logger = self.get_logger("web.websocket")
        logger.info(f"WebSocket断开: {client_id}")
    
    def log_system_stats(self, stats: dict):
        """记录系统统计日志"""
        logger = self.get_logger("web.system")
        logger.info(f"系统统计: {json.dumps(stats, ensure_ascii=False)}")

# 创建全局日志管理器实例
web_logger = WebTransformLogger()

# 便捷函数
def get_logger(name: str = "web") -> logging.Logger:
    """获取日志器"""
    return web_logger.get_logger(name)

def log_request(request_id: str, method: str, path: str, user_id: Optional[str] = None):
    """记录请求日志"""
    web_logger.log_request(request_id, method, path, user_id)

def log_response(request_id: str, status_code: int, duration: float, user_id: Optional[str] = None):
    """记录响应日志"""
    web_logger.log_response(request_id, status_code, duration, user_id)

def log_file_upload(filename: str, file_size: int, user_id: Optional[str] = None):
    """记录文件上传日志"""
    web_logger.log_file_upload(filename, file_size, user_id)

def log_transform_start(task_id: str, style_type: str, user_id: Optional[str] = None):
    """记录变换开始日志"""
    web_logger.log_transform_start(task_id, style_type, user_id)

def log_transform_progress(task_id: str, progress: float, user_id: Optional[str] = None):
    """记录变换进度日志"""
    web_logger.log_transform_progress(task_id, progress, user_id)

def log_transform_complete(task_id: str, duration: float, output_path: str, user_id: Optional[str] = None):
    """记录变换完成日志"""
    web_logger.log_transform_complete(task_id, duration, output_path, user_id)

def log_transform_error(task_id: str, error: str, user_id: Optional[str] = None):
    """记录变换错误日志"""
    web_logger.log_transform_error(task_id, error, user_id)

def log_websocket_connect(client_id: str):
    """记录WebSocket连接日志"""
    web_logger.log_websocket_connect(client_id)

def log_websocket_disconnect(client_id: str):
    """记录WebSocket断开日志"""
    web_logger.log_websocket_disconnect(client_id)

def log_system_stats(stats: dict):
    """记录系统统计日志"""
    web_logger.log_system_stats(stats) 