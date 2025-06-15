# Witness Project - ComfyUI Integration

This project provides a FastAPI-based application server and a task processing worker to interact with a ComfyUI instance for image processing tasks.

## Project Structure

```
witness/
├── core/                   # Core components like ComfyUI client
│   ├── __init__.py
│   └── comfy_client.py     # Client for interacting with ComfyUI
├── task_processor/         # Background task processing
│   ├── __init__.py
│   ├── task_processor.py   # Main task processor logic
│   ├── tasks.py            # Task definitions
│   └── workers/
│       ├── __init__.py
│       └── image_worker.py   # Image processing worker
├── utils/
│   ├── __init__.py
│   ├── redis_client.py     # Redis client utility
│   └── workflow_utils.py   # ComfyUI workflow loading and modification utilities
├── workflows/
│   └── style_change.json   # Example ComfyUI workflow
├── __init__.py
├── main.py                 # FastAPI application entry point
├── README.md               # This file
└── requirements.txt        # Python dependencies
```

## Prerequisites

1.  **Python 3.8+**
2.  A running **ComfyUI instance**. Ensure it's accessible from where this application will run.
    *   By default, the application expects ComfyUI at `http://127.0.0.1:8188`.
    *   You can configure this via the `COMFYUI_SERVER_ADDRESS` environment variable for the worker.
3.  **ComfyUI Workflows**: You need to have your ComfyUI workflow JSON files in the `witness/workflows/` directory. An example placeholder `style_change.json` is mentioned, but you'll need to create/provide your actual workflows.
    *   The `image_worker.py` currently expects node titles like "Load Image" and "Save Image" in the workflow for dynamic updates. Adjust `workflow_utils.py` if your node titles differ.

## Setup

1.  **Clone the repository (if applicable) or ensure you are in the `witness` project root.**

2.  **Create a Python virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Running the Application

### 1. Start the FastAPI Application Server

Navigate to the `witness` project root directory and run Uvicorn:

```bash
# Ensure you are in the witness/ directory
uvicorn main:app --reload --port 8000
```

*   `--reload`: Enables auto-reload on code changes (for development).
*   `--port 8000`: Runs the server on port 8000.

The API will be accessible at `http://127.0.0.1:8000`.
API documentation (Swagger UI) will be at `http://127.0.0.1:8000/docs`.

### 2. Start the Task Processor Worker

In a **new terminal window/tab**, navigate to the `witness` project root directory. The `image_worker.py` is designed to be run as a script that connects to Redis and processes tasks.

First, ensure Redis is running (as specified in `main.py` and `task_processor.py`, it defaults to `localhost:6379`).

Then, from the `witness` root directory, run the image worker:

```bash
# Ensure you are in the witness/ directory

# If ComfyUI is not at http://127.0.0.1:8188, or Redis is not at localhost:6379,
# you might need to set environment variables (if the worker is adapted to use them)
# or modify the hardcoded values in image_worker.py and comfy_client.py.
# Example for ComfyUI (worker needs to be adapted to read this):
# export COMFYUI_SERVER_ADDRESS="http://your_comfy_ui_ip:port"

python task_processor/workers/image_worker.py
```

This worker will listen for tasks on the Redis queue (default: `image_processing_tasks`) and process them using ComfyUI.

This worker will pick up tasks enqueued by the FastAPI server (currently via a mock queue) and process them using ComfyUI.

## Testing the End-to-End Flow

Follow these steps to test the complete image processing pipeline:

1.  **Prerequisites:**
    *   Ensure **ComfyUI** is running and accessible (default: `http://127.0.0.1:8188`).
    *   Ensure **Redis** server is running (default: `localhost:6379`).
    *   You have a workflow file, e.g., `style_change.json`, in the `witness/workflows/` directory. This workflow must contain:
        *   A node titled "Load Image" (or update `workflow_utils.py` and `image_worker.py` if your title is different) that will receive the input image.
        *   A node titled "Save Image" (or update `workflow_utils.py` and `image_worker.py`) that will save the output. The filename prefix will be automatically set by the worker.

2.  **Start the Services:**
    *   **FastAPI Server**: In a terminal, navigate to the `witness/` directory and run:
        ```bash
        uvicorn main:app --reload --port 8000
        ```
    *   **Task Worker**: In a *new* terminal, navigate to the `witness/` directory and run:
        ```bash
        python task_processor/workers/image_worker.py
        ```

3.  **Prepare your Test Image:**
    *   Get an image file (e.g., `my_test_image.png`).
    *   Base64 encode this image. You can use an online tool or a command-line utility:
        ```bash
        # On macOS
        base64 -i my_test_image.png -o my_test_image.b64
        # On Linux
        base64 my_test_image.png > my_test_image.b64
        ```
        Then copy the content of `my_test_image.b64`.

4.  **Send the Processing Request:**
    *   Use `curl` or a tool like Postman to send a POST request to the `/process_image/` endpoint.
    *   The API documentation is available at `http://127.0.0.1:8000/docs`.

    **Example using `curl`:**

    Create a JSON file named `payload.json`:
    ```json
    {
      "user_id": "test_user_001",
      "image_data_b64": "PASTE_YOUR_BASE64_ENCODED_IMAGE_DATA_HERE",
      "workflow_name": "style_change.json"
    }
    ```
    Replace `"PASTE_YOUR_BASE64_ENCODED_IMAGE_DATA_HERE"` with the actual base64 string from step 3.

    Then, execute the `curl` command:
    ```bash
    curl -X POST "http://127.0.0.1:8000/process_image/" \
    -H "Content-Type: application/json" \
    -d @payload.json
    ```
    You should receive a JSON response with a `task_id` and a message.

5.  **Monitor Logs:**
    *   **FastAPI Server Log**: Check the terminal where `uvicorn` is running. You should see logs indicating the request was received and a task was submitted (e.g., `Image processing task ... submitted`).
    *   **Task Worker Log**: Check the terminal where `image_worker.py` is running. You should see logs indicating:
        *   The worker picked up a task from Redis.
        *   Image uploaded to ComfyUI.
        *   Workflow queued in ComfyUI.
        *   WebSocket messages from ComfyUI about the processing status.
        *   Task completion or error messages.

6.  **Verify Output in ComfyUI:**
    *   Once the worker log indicates the task is complete and the image is saved, check your ComfyUI's `output` directory.
    *   You should find the processed image. The filename will typically be prefixed by something like `ComfyUI_` (from the default "Save Image" node) or `test_user_001_ComfyUI_` if the worker successfully modified the filename prefix in the workflow.

This process verifies that all components (API server, Redis, Task Worker, ComfyUI Client, and ComfyUI itself) are working together correctly.

## Important Notes & TODOs

*   **Mock Queue**: The current implementation uses a simple Python list (`_mock_task_queue`) as a task queue. For a production system, replace this with a robust message queue like RabbitMQ, Redis Streams, or Kafka.
*   **Error Handling**: Basic error handling is in place, but can be further improved.
*   **Configuration**: Server addresses, workflow paths, etc., should ideally be managed via a configuration file or environment variables more systematically.
*   **ComfyUI Workflow Structure**: The `update_workflow_image_and_user` function in `utils/workflow_utils.py` assumes specific node titles ("Load Image", "Save Image") for modification. This might need to be generalized or made configurable based on node IDs or types if your workflows vary significantly.
*   **Security**: No authentication/authorization is implemented on the API endpoints. Add appropriate security measures for production.
*   **Image Handling**: The worker currently saves a temporary local copy of the uploaded image before passing its path to ComfyUI. The `ComfyUIClient`'s `upload_image` method is used, which should handle placing the image in ComfyUI's input directory.
*   **Output Handling**: The worker currently prints a mock path for the output. Real implementation should fetch/link to the actual output from ComfyUI.