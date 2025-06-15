import asyncio
import base64
import logging
import uuid

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from witness.task_processor.task_processor import TaskProcessor
from witness.core.redis_client import RedisClient
from witness.config import config
from witness.task_processor.tasks import ImageProcessingTask, UserInfo as TaskUserInfo, TaskStatus
from witness.core.comfy_client import ComfyUIClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Witness API",
    description="API for submitting and managing image processing tasks with ComfyUI.",
    version="0.1.0"
)

# --- Pydantic Models ---
class UserInfoRequest(BaseModel):
    client_id: Optional[str] = Field(None, example="client_abc")
    ip_address: Optional[str] = Field(None, example="192.168.1.100")

class ImageTaskRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded image data.")
    workflow_json: Optional[str] = Field(None, description="Full JSON content of the ComfyUI workflow. If not provided, a default workflow might be used or selected based on workflow_name.", example='{"key": "value"}')
    workflow_name: Optional[str] = Field(None, description="Name of a predefined workflow to load if workflow_json is not provided (e.g., 'default_workflow.json'). The actual workflow loading logic based on name needs to be implemented in the worker.", example="default_workflow.json")
    params: Optional[Dict[str, Any]] = Field(None, description="Additional parameters to patch into the workflow.", example={"seed": 12345})
    user_info: Optional[UserInfoRequest] = Field(None, description="User information.")

class ImageTaskResponse(BaseModel):
    task_id: str = Field(..., description="Unique identifier for the submitted task.")
    status: str = Field(..., description="Current status of the task.")
    message: str = Field(default="Task submitted successfully.")

# For Pydantic models from other modules if needed directly
# from witness.task_processor.tasks import UserInfo as TaskUserInfo # Already imported and aliased

# --- Global Clients (Initialize once) ---
# It's generally better to manage client lifecycles with FastAPI's lifespan events
# For simplicity in this example, we initialize them globally.

# Configuration is now handled by witness.config

redis_client: Optional[RedisClient] = None
comfy_client: Optional[ComfyUIClient] = None
task_processor: Optional[TaskProcessor] = None

@app.on_event("startup")
async def startup_event():
    global redis_client, comfy_client, task_processor
    logger.info("FastAPI application startup...")
    try:
        logger.info(f"Attempting to connect to Redis at {config.REDIS_HOST}:{config.REDIS_PORT}")
        redis_client = RedisClient(host=config.REDIS_HOST, port=config.REDIS_PORT, db=config.REDIS_DB)
        if redis_client.is_connected():
            logger.info(f"Successfully connected to Redis at {config.REDIS_HOST}:{config.REDIS_PORT}.")
        else:
            logger.error(f"Failed to connect to Redis at {config.REDIS_HOST}:{config.REDIS_PORT}. Application might not function correctly.")
            # Depending on criticality, you might want to raise an exception here to stop startup

        logger.info(f"Initializing ComfyUI client for server at {config.COMFYUI_SERVER_ADDRESS}")
        comfy_client = ComfyUIClient(server_address=config.COMFYUI_SERVER_ADDRESS)
        # Perform a basic check for ComfyUI client initialization. 
        # A more robust check would involve an actual API call in ComfyUIClient's connect() or a dedicated check_connection() method.
        # For now, we assume ComfyUIClient's constructor or an internal connect method handles initial setup.
        # Example: await comfy_client.connect() # If connect is async and performs checks
        logger.info(f"ComfyUI client initialized for {config.COMFYUI_SERVER_ADDRESS}. Further checks depend on client implementation.")

        if redis_client and redis_client.is_connected() and comfy_client:
            task_processor = TaskProcessor(
                redis_client=redis_client, 
                comfy_client=comfy_client, 
                task_queue_name=config.REDIS_TASK_QUEUE_NAME,
                task_status_prefix=config.REDIS_TASK_STATUS_PREFIX
            )
            logger.info("TaskProcessor initialized.")
        else:
            logger.error("TaskProcessor could not be initialized due to missing or failed client connections (Redis or ComfyUI).")
            task_processor = None # Ensure task_processor is None if initialization fails


    except Exception as e:
        logger.error(f"Critical error during startup: {e}. Application might not function correctly.", exc_info=True)
        # Consider raising the exception to stop FastAPI from starting if critical components fail
        # raise HTTPException(status_code=503, detail=f"Startup failed: {e}") # This won't stop startup from here
        # To truly stop, you might need to handle this outside or ensure lifespan handles it.

@app.on_event("shutdown")
async def shutdown_event():
    global redis_client
    logger.info("FastAPI application shutdown...")
    if redis_client:
        # Assuming RedisClient has a close method, or connections are managed by the library
        # await redis_client.close() # Example
        logger.info("Redis client resources released (if applicable).")
    if comfy_client:
        # Perform any cleanup for comfy_client if necessary
        logger.info("ComfyUI client resources released (if applicable).")

# --- API Endpoints ---
@app.post("/process_image/", response_model=ImageTaskResponse, status_code=202)
async def process_image_endpoint(request: ImageTaskRequest, background_tasks: BackgroundTasks):
    """
    Submits an image processing task.

    - **image_base64**: Base64 encoded image data.
    - **workflow_json**: (Optional) Full JSON content of the ComfyUI workflow.
    - **workflow_name**: (Optional) Name of a predefined workflow if workflow_json is not provided.
    - **params**: (Optional) Additional parameters to patch into the workflow.
    - **user_info**: (Optional) User information.
    """
    if not task_processor or not redis_client or not redis_client.is_connected():
        logger.error("Task processor or Redis client not available/connected. Startup might have failed.")
        raise HTTPException(status_code=503, detail="Service temporarily unavailable. Essential services not ready.")

    try:
        # Validate base64 image data (basic check)
        try:
            _ = base64.b64decode(request.image_base64)
        except Exception:
            logger.warning(f"Invalid base64 image data received.", exc_info=True)
            raise HTTPException(status_code=400, detail="Invalid base64 image data.")

        task_id = str(uuid.uuid4())
        
        user_info_data = None
        if request.user_info:
            user_info_data = TaskUserInfo(client_id=request.user_info.client_id, ip_address=request.user_info.ip_address)

        # Create the task payload according to ImageProcessingTask model structure
        task_payload_model = ImageProcessingTask(
            task_id=task_id,
            image_base64=request.image_base64,
            workflow_json=request.workflow_json,
            # workflow_name is not directly part of ImageProcessingTask, 
            # it's used by the worker to load a workflow_json if workflow_json itself is not provided.
            # The worker needs to handle logic for workflow_name if workflow_json is None.
            # For now, we pass it via params if needed, or worker assumes a default if both are None.
            params=request.params or {},
            user_info=user_info_data,
            status=TaskStatus.PENDING
        )
        # If workflow_name is provided and workflow_json is not, add it to params for worker to pick up.
        if request.workflow_name and not request.workflow_json:
            if task_payload_model.params is None: task_payload_model.params = {}
            task_payload_model.params['workflow_name'] = request.workflow_name

        # Enqueue the task using TaskProcessor.enqueue_task, which expects a dictionary.
        enqueued_task_id = task_processor.enqueue_task(task_payload_model.model_dump())

        if not enqueued_task_id or enqueued_task_id != task_id:
            logger.error(f"Failed to enqueue task {task_id}. Enqueue method returned: {enqueued_task_id}")
            raise HTTPException(status_code=500, detail="Failed to enqueue task properly.")

        logger.info(f"Image processing task {task_id} enqueued for user {request.user_info.client_id if request.user_info else 'unknown'} with workflow_name: {request.workflow_name or 'not specified'}, workflow_json provided: {bool(request.workflow_json)}")
        return ImageTaskResponse(task_id=task_id, status=TaskStatus.PENDING.value, message="Task accepted and queued for processing.")


    except HTTPException: # Re-raise HTTPExceptions directly
        raise
    except Exception as e:
        logger.error(f"Error processing image task for user {request.user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    # Add checks for Redis and ComfyUI connectivity if desired
    # For example:
    # redis_ok = await redis_client.ping() if redis_client else False
    # comfy_ok = await comfy_client.check_status() if comfy_client else False
    return {"status": "ok"}

# To run this application (example):
# uvicorn witness.main:app --reload

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Uvicorn server for Witness API...")
    # Note: Lifespan events (startup/shutdown) work best when Uvicorn is run programmatically like this
    # or via the command line `uvicorn witness.main:app`.
    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT, log_level=config.API_LOG_LEVEL.lower())