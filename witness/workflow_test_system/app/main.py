"""
ComfyUI workflow test system - FastAPI main application
"""

import asyncio
import logging
import json
from typing import Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from .config import config
from .routers import workflow, files, system
from .services.rpc_client import rpc_client
from .services.websocket_manager import WebSocketManager
from .services.session_manager import session_manager

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="ComfyUI Workflow Test System",
    description="Test system for ComfyUI workflow server RPC calls",
    version="1.0.0"
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
ws_manager: WebSocketManager = None

# Include routers
app.include_router(workflow.router, prefix="/api")
app.include_router(files.router, prefix="/api") 
app.include_router(system.router, prefix="/api")

# Static files
import os
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Upload files directory
uploads_dir = "uploads"
if not os.path.exists(uploads_dir):
    os.makedirs(uploads_dir)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

async def handle_comfyui_message(message: Dict[str, Any]):
    """Handle WebSocket messages from ComfyUI server"""
    try:
        message_type = message.get("type")
        request_id = message.get("request_id")
        
        logger.debug(f"Received ComfyUI message: {message_type}, request_id: {request_id}")
        
        if request_id:
            # Route message to specific frontend session based on request_id
            await session_manager.broadcast_to_request(request_id, message)
        else:
            # Broadcast to all sessions
            await session_manager.broadcast_to_all(message)
            
    except Exception as e:
        logger.error(f"Error handling ComfyUI message: {e}")

@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    global ws_manager
    
    logger.info("Starting ComfyUI workflow test system")
    
    try:
        # Start session cleanup task
        session_manager.start_cleanup_task()
        
        # Initialize WebSocket manager
        ws_manager = WebSocketManager(message_handler=handle_comfyui_message)
        
        # Start WebSocket connection (don't wait for it)
        asyncio.create_task(ws_manager.connect())
        
        logger.info("Test system started successfully")
        
    except Exception as e:
        logger.error(f"Startup error: {e}")
        logger.warning("Some services may be unavailable, but the application will continue running")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("Shutting down ComfyUI workflow test system")
    
    try:
        # Close WebSocket manager
        if ws_manager:
            await ws_manager.close()
    except Exception as e:
        logger.error(f"Error closing WebSocket manager: {e}")
    
    try:
        # Shutdown session manager
        await session_manager.shutdown()
    except Exception as e:
        logger.error(f"Error shutting down session manager: {e}")
    
    logger.info("Test system shutdown complete")

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for frontend connections"""
    try:
        await websocket.accept()
        logger.info(f"WebSocket connection established: {session_id}")
        
        # Add WebSocket connection to session manager
        await session_manager.create_session(websocket)
        
        try:
            while True:
                # Receive frontend messages
                data = await websocket.receive_text()
                
                # Handle heartbeat ping/pong
                if data == 'ping':
                    await websocket.send_text('pong')
                    continue
                
                try:
                    message = json.loads(data)
                    await session_manager.handle_websocket_message(session_id, message)
                except json.JSONDecodeError:
                    logger.warning(f"Received invalid JSON message: {data}")
                    
        except WebSocketDisconnect:
            logger.info(f"WebSocket connection closed: {session_id}")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            # Clean up session
            await session_manager.remove_session(session_id)
            
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main frontend page"""
    try:
        index_path = os.path.join(static_dir, "index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        return HTMLResponse("""
        <html>
            <head><title>ComfyUI工作流测试系统</title></head>
            <body>
                <h1>ComfyUI工作流测试系统</h1>
                <p>前端文件未找到，请检查static目录。</p>
            </body>
        </html>
        """)

@app.get("/api/session")
async def get_session_info():
    """Get new session information"""
    import uuid
    session_id = str(uuid.uuid4())
    return {
        "success": True,
        "data": {
            "session_id": session_id,
            "created_at": "2024-01-01T00:00:00Z"
        }
    }

@app.get("/health")
async def health():
    """Simple health check endpoint"""
    return {"status": "healthy", "service": "workflow_test_system"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=config.TEST_SYSTEM_HOST,
        port=config.TEST_SYSTEM_PORT,
        reload=True
    )