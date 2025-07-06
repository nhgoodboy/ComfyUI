import asyncio
import logging
from ..core.workflow_manager import get_workflow_manager

logger = logging.getLogger(__name__)

async def start_cleanup_task():
    """启动定期清理任务"""
    while True:
        try:
            # 获取工作流管理器并执行清理
            try:
                workflow_manager = get_workflow_manager()
                cleaned_count = workflow_manager.cleanup_old_tasks()
                if cleaned_count > 0:
                    logger.info(f"清理了 {cleaned_count} 个旧任务")
            except Exception as e:
                logger.error(f"获取工作流管理器失败: {e}")
            
            await asyncio.sleep(3600)  # 每小时清理一次
        except Exception as e:
            logger.error(f"清理任务失败: {e}")
            await asyncio.sleep(300)  # 出错后5分钟重试 