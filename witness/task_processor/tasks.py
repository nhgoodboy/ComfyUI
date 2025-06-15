from enum import Enum
import uuid
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field

class UserInfo(BaseModel):
    user_id: str
    user_group: Optional[str] = None

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class ImageProcessingTask(BaseModel):
    """Represents a task's state and metadata as stored in Redis and viewed by API."""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus = TaskStatus.PENDING
    workflow_name: str  # e.g., "style_change"
    user_info: Optional[UserInfo] = None
    
    # Details for API/client, may not all be directly used by worker payload
    original_input_filename: Optional[str] = None # Original filename from upload
    # output_path: Optional[str] = None # Path where final result might be stored by a subsequent step
    
    # Worker-related results
    prompt_id: Optional[str] = None # ComfyUI prompt ID
    worker_output_preview: Optional[Any] = None # Preview of worker output (e.g., path to image)
    result_data: Optional[Dict[str, Any]] = None # Full result data from worker if needed
    error_message: Optional[str] = None
    created_at: str = Field(default_factory=lambda: str(time.time()))
    updated_at: str = Field(default_factory=lambda: str(time.time()))

class WorkerTaskPayload(BaseModel):
    """Data payload sent to the image processing worker via the queue."""
    task_id: str
    image_data_b64: str  # Base64 encoded image string
    workflow_name: str   # e.g., "style_change"
    user_info: UserInfo  # User information for processing

# Example usage (for testing or reference)
if __name__ == "__main__":
    import time
    user = UserInfo(user_id="test_user", user_group="alpha")
    task_meta = ImageProcessingTask(
        workflow_name="style_transfer_v1", 
        user_info=user,
        original_input_filename="my_image.png"
    )
    print(f"Task Metadata: {task_meta.model_dump_json(indent=2)}")

    worker_payload = WorkerTaskPayload(
        task_id=task_meta.task_id,
        image_data_b64="(pretend_base64_string)",
        workflow_name=task_meta.workflow_name,
        user_info=user
    )
    print(f"Worker Payload: {worker_payload.model_dump_json(indent=2)}")