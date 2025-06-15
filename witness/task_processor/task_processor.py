import json
import logging
import time
from typing import Optional, List

from witness.utils.redis_client import RedisClient
from .tasks import ImageProcessingTask, TaskStatus, WorkerTaskPayload, UserInfo

logger = logging.getLogger(__name__)

class TaskProcessor:
    def __init__(self, redis_host: str = 'localhost', redis_port: int = 6379, redis_db: int = 0):
        self.redis_client = RedisClient(host=redis_host, port=redis_port, db=redis_db)
        self.task_queue_key = "image_processing_queue"
        self.task_key_prefix = "task:"

    async def connect(self):
        """Establishes connection to Redis."""
        try:
            await self.redis_client.connect()
            logger.info(f"TaskProcessor connected to Redis at {self.redis_client.host}:{self.redis_client.port}")
        except Exception as e:
            logger.error(f"TaskProcessor failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        """Closes connection to Redis."""
        await self.redis_client.disconnect()
        logger.info("TaskProcessor disconnected from Redis.")

    async def enqueue_task(
        self, 
        image_data_b64: str, 
        workflow_name: str, 
        user_info: UserInfo,
        original_input_filename: Optional[str] = None
    ) -> ImageProcessingTask:
        """Creates task metadata, stores it in Redis, and enqueues the task for a worker."""
        task_meta = ImageProcessingTask(
            workflow_name=workflow_name,
            user_info=user_info,
            original_input_filename=original_input_filename,
            created_at=str(time.time()), # Ensure created_at is set
            updated_at=str(time.time())  # Ensure updated_at is set
        )

        worker_payload = WorkerTaskPayload(
            task_id=task_meta.task_id,
            image_data_b64=image_data_b64,
            workflow_name=workflow_name,
            user_info=user_info
        )

        try:
            # Store task metadata in Redis
            await self.redis_client.set_value(
                f"{self.task_key_prefix}{task_meta.task_id}", 
                task_meta.model_dump_json()
            )
            
            # Push worker payload to the queue (Redis list)
            await self.redis_client.rpush_value(self.task_queue_key, worker_payload.model_dump_json())
            
            logger.info(f"Task {task_meta.task_id} enqueued for workflow '{workflow_name}'.")
            return task_meta
        except Exception as e:
            logger.error(f"Failed to enqueue task {task_meta.task_id}: {e}")
            # Potentially try to clean up metadata if queue push fails, or mark as failed immediately
            task_meta.status = TaskStatus.FAILED
            task_meta.error_message = f"Failed to enqueue: {str(e)}"
            await self.update_task_status(task_meta.task_id, TaskStatus.FAILED, error_message=task_meta.error_message)
            raise

    async def get_task(self, task_id: str) -> Optional[ImageProcessingTask]:
        """Retrieves task metadata from Redis."""
        task_json = await self.redis_client.get_value(f"{self.task_key_prefix}{task_id}")
        if task_json:
            return ImageProcessingTask(**json.loads(task_json))
        return None

    async def update_task_status(
        self, 
        task_id: str, 
        status: TaskStatus, 
        prompt_id: Optional[str] = None,
        worker_output_preview: Optional[str] = None, 
        result_data: Optional[dict] = None,
        error_message: Optional[str] = None
    ) -> Optional[ImageProcessingTask]:
        """Updates the status and other details of a task in Redis."""
        task = await self.get_task(task_id)
        if not task:
            logger.warning(f"Attempted to update non-existent task: {task_id}")
            return None

        task.status = status
        task.updated_at = str(time.time())
        if prompt_id is not None:
            task.prompt_id = prompt_id
        if worker_output_preview is not None:
            task.worker_output_preview = worker_output_preview
        if result_data is not None:
            task.result_data = result_data
        if error_message is not None:
            task.error_message = error_message
        
        try:
            await self.redis_client.set_value(f"{self.task_key_prefix}{task.task_id}", task.model_dump_json())
            logger.info(f"Task {task.task_id} status updated to {status}.")
            return task
        except Exception as e:
            logger.error(f"Failed to update task {task.task_id} status: {e}")
            # Consider how to handle update failures - retry?
            return task # Return the task with intended changes, even if save failed

    async def get_queued_task_payload(self, timeout: int = 0) -> Optional[WorkerTaskPayload]:
        """Retrieves a task payload from the queue (blocking pop with timeout)."""
        # blpop returns a tuple (key_name, value) or None if timeout
        item = await self.redis_client.blpop_value(self.task_queue_key, timeout=timeout)
        if item:
            # item[0] is the key name, item[1] is the value
            payload_json = item[1]
            try:
                return WorkerTaskPayload(**json.loads(payload_json))
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode task payload from queue: {e}. Payload: {payload_json}")
                return None # Or handle error differently
            except Exception as e:
                logger.error(f"Error processing task payload: {e}. Payload: {payload_json}")
                return None
        return None

# Example usage (for testing or reference)
async def example_usage():
    logging.basicConfig(level=logging.INFO)
    processor = TaskProcessor(redis_host=os.getenv("REDIS_HOST", "localhost"), redis_port=int(os.getenv("REDIS_PORT", "6379")))
    await processor.connect()

    try:
        test_user = UserInfo(user_id="proc_test_user", user_group="testers")
        # Minimal valid PNG: 1x1 black pixel, base64 encoded
        minimal_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        
        print("Enqueuing a new task...")
        enqueued_task_meta = await processor.enqueue_task(
            image_data_b64=minimal_png_b64,
            workflow_name="style_change_example",
            user_info=test_user,
            original_input_filename="pixel.png"
        )
        print(f"Enqueued task metadata: {enqueued_task_meta.model_dump_json(indent=2)}")

        print(f"\nRetrieving task {enqueued_task_meta.task_id}...")
        retrieved_task = await processor.get_task(enqueued_task_meta.task_id)
        if retrieved_task:
            print(f"Retrieved task: {retrieved_task.model_dump_json(indent=2)}")
        else:
            print(f"Task {enqueued_task_meta.task_id} not found after enqueue.")

        print(f"\nAttempting to get a task from queue (timeout 5s)...")
        worker_payload = await processor.get_queued_task_payload(timeout=5)
        if worker_payload:
            print(f"Got worker payload: {worker_payload.model_dump_json(indent=2)}")
            # Simulate worker processing and updating status
            print(f"\nSimulating worker processing for task {worker_payload.task_id}...")
            await asyncio.sleep(2) # Simulate work
            await processor.update_task_status(
                task_id=worker_payload.task_id, 
                status=TaskStatus.PROCESSING,
                prompt_id="sim_prompt_123"
            )
            retrieved_task_processing = await processor.get_task(worker_payload.task_id)
            print(f"Task status after processing update: {retrieved_task_processing.model_dump_json(indent=2)}")
            
            await asyncio.sleep(3) # Simulate more work
            await processor.update_task_status(
                task_id=worker_payload.task_id, 
                status=TaskStatus.COMPLETED,
                worker_output_preview="/path/to/simulated_output.png",
                result_data={"detail": "simulation complete"}
            )
            retrieved_task_completed = await processor.get_task(worker_payload.task_id)
            print(f"Task status after completion update: {retrieved_task_completed.model_dump_json(indent=2)}")

        else:
            print("No task received from queue within timeout.")

    except Exception as e:
        print(f"An error occurred during example usage: {e}")
    finally:
        await processor.disconnect()

if __name__ == "__main__":
    import asyncio
    import os
    # To run this example, ensure Redis is running.
    # You might need to set REDIS_HOST and REDIS_PORT environment variables if not default.
    asyncio.run(example_usage())