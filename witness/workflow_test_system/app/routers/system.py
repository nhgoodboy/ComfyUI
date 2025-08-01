"""
System API endpoints
"""

import logging
from fastapi import APIRouter, HTTPException
from ..services.rpc_client import rpc_client
from ..services.session_manager import session_manager
from ..services.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/system", tags=["system"])

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        logger.debug("Performing health check")
        
        async with rpc_client:
            comfyui_health = await rpc_client.health_check()
        
        return {
            "success": True,
            "data": {
                "test_system": "healthy",
                "comfyui_server": comfyui_health,
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "success": False,
            "data": {
                "test_system": "healthy",
                "comfyui_server": {"status": "unhealthy", "error": str(e)},
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }

@router.get("/stats")
async def get_system_stats():
    """Get system statistics"""
    try:
        logger.debug("Getting system statistics")
        
        # Get session statistics
        session_stats = session_manager.get_session_stats()
        
        # Get ComfyUI statistics
        try:
            async with rpc_client:
                comfyui_stats = await rpc_client.get_system_stats()
        except Exception as e:
            logger.warning(f"Failed to get ComfyUI statistics: {e}")
            comfyui_stats = {"error": str(e)}
        
        return {
            "success": True,
            "data": {
                "test_system": {
                    "sessions": session_stats,
                    "uptime": "unknown"
                },
                "comfyui_server": comfyui_stats
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get system statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions")
async def get_sessions():
    """Get active sessions information"""
    try:
        active_sessions = session_manager.get_active_sessions()
        session_stats = session_manager.get_session_stats()
        
        return {
            "success": True,
            "data": {
                "active_sessions": active_sessions,
                "stats": session_stats
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/parse-filename")
async def parse_filename(filename: str):
    """Parse filename"""
    try:
        logger.debug(f"Parsing filename: {filename}")
        
        async with rpc_client:
            result = await rpc_client.parse_filename(filename)
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Failed to parse filename: {e}")
        raise HTTPException(status_code=500, detail=str(e))