"""
˚ﬂ—ßAPIÔ1
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
    """˚ﬂe∑¿Â"""
    try:
        logger.debug("gL˚ﬂe∑¿Â")
        
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
        logger.error(f"e∑¿Â1%: {e}")
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
    """∑÷˚ﬂﬂ°·o"""
    try:
        logger.debug("∑÷˚ﬂﬂ°·o")
        
        # ∑÷›ﬂ°
        session_stats = session_manager.get_session_stats()
        
        # ∑÷ComfyUI°hﬂ°
        try:
            async with rpc_client:
                comfyui_stats = await rpc_client.get_system_stats()
        except Exception as e:
            logger.warning(f"∑÷ComfyUIﬂ°1%: {e}")
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
        logger.error(f"∑÷˚ﬂﬂ°1%: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions")
async def get_sessions():
    """∑÷;√›h"""
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
        logger.error(f"∑÷›h1%: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/parse-filename")
async def parse_filename(filename: str):
    """„êáˆ"""
    try:
        logger.debug(f"„êáˆ: {filename}")
        
        async with rpc_client:
            result = await rpc_client.parse_filename(filename)
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"„êáˆ1%: {e}")
        raise HTTPException(status_code=500, detail=str(e))