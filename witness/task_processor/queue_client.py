import json
import logging
from typing import Any, Dict

from witness.core.redis_client import RedisClient
from witness.task_processor.tasks import ImageProcessingTask
from witness.config import Config

logger = logging.getLogger(__name__)

class QueueClient:
    """客户端，用于与任务队列（通过 Redis 实现）交互。"""

    def __init__(self, redis_client: RedisClient, config: Config):
        """
        初始化 QueueClient。

        参数:
        - redis_client (RedisClient): Redis 客户端实例。
        - config (Config): 应用配置实例。
        """
        if not isinstance(redis_client, RedisClient):
            raise TypeError("redis_client 必须是 RedisClient 的一个实例")
        if not isinstance(config, Config):
            raise TypeError("config 必须是 Config 的一个实例")
            
        self.redis_client = redis_client
        self.task_queue_name = config.TASK_QUEUE_NAME
        logger.info(f"QueueClient 初始化完成，使用任务队列: {self.task_queue_name}")

    def enqueue_task(self, task: ImageProcessingTask) -> bool:
        """
        将图像处理任务加入队列。

        参数:
        - task (ImageProcessingTask): 要加入队列的任务对象。

        返回:
        - bool: 如果任务成功加入队列则返回 True，否则返回 False。
        """
        if not isinstance(task, ImageProcessingTask):
            logger.error(f"无效的任务类型传递给 enqueue_task: {type(task)}")
            return False
        
        try:
            # ImageProcessingTask 已经是 Pydantic 模型，可以直接序列化
            # RedisClient 的 enqueue_task 方法期望一个字典或 Pydantic 模型
            success = self.redis_client.enqueue_task(self.task_queue_name, task)
            if success:
                logger.info(f"任务 {task.task_id} 已成功加入队列 {self.task_queue_name}。")
            else:
                logger.error(f"无法将任务 {task.task_id} 加入队列 {self.task_queue_name}。")
            return success
        except Exception as e:
            logger.exception(f"将任务 {task.task_id} 加入队列 {self.task_queue_name} 时发生错误: {e}")
            return False

    def get_queue_length(self) -> int:
        """获取当前任务队列的长度。"""
        try:
            length = self.redis_client.get_list_length(self.task_queue_name)
            logger.debug(f"队列 {self.task_queue_name} 的当前长度: {length}")
            return length
        except Exception as e:
            logger.exception(f"获取队列 {self.task_queue_name} 长度时出错: {e}")
            return -1 # 表示错误

# 注意：此文件不再包含 get_mock_queue_status 或直接的 enqueue_image_task 函数。
# TaskProcessor 将使用此类。