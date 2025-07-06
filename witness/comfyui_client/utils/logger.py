import logging
import sys

def get_logger(name="ComfyUIClient"):
    """
    获取一个指定名称的日志记录器。
    应用程序应该负责配置处理程序。
    """
    logger = logging.getLogger(name)
    return logger 