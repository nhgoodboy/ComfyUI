import os
from dotenv import load_dotenv

# Load environment variables from .env file, if it exists
load_dotenv()

class AppConfig:
    """Application configuration class."""

    # Redis Configuration
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_TASK_QUEUE_NAME: str = os.getenv("REDIS_TASK_QUEUE_NAME", "image_processing_queue")
    REDIS_TASK_STATUS_PREFIX: str = os.getenv("REDIS_TASK_STATUS_PREFIX", "task_status:")

    # ComfyUI Configuration
    COMFYUI_SERVER_ADDRESS: str = os.getenv("COMFYUI_SERVER_ADDRESS", "127.0.0.1:8188")
    # Default workflow file path (relative to the project root or an absolute path)
    # This might need adjustment based on where workflows are stored.
    DEFAULT_COMFYUI_WORKFLOW: str = os.getenv("DEFAULT_COMFYUI_WORKFLOW", "workflows/default_workflow.json") 

    # Task Processor Configuration
    TASK_WORKER_LOG_LEVEL: str = os.getenv("TASK_WORKER_LOG_LEVEL", "INFO").upper()
    TASK_PROCESSING_TIMEOUT_SECONDS: int = int(os.getenv("TASK_PROCESSING_TIMEOUT_SECONDS", "300")) # 5 minutes

    # API Server Configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_LOG_LEVEL: str = os.getenv("API_LOG_LEVEL", "info").lower()

    # Logging Configuration
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    # Other settings
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50")) # Max image upload size

# Instantiate the config
config = AppConfig()

# Example of how to use it in other modules:
# from witness.config import config
# print(config.REDIS_HOST)