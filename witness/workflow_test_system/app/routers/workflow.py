"""
Workflow API endpoints
"""

import uuid
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from ..models.requests import WorkflowExecuteRequest, WorkflowStatusRequest
from ..services.rpc_client import rpc_client
from ..services.session_manager import session_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workflow", tags=["workflow"])

def generate_request_id() -> str:
    """Generate unique request ID"""
    return f"test_{uuid.uuid4().hex[:12]}"

@router.post("/execute")
async def execute_workflow(request: WorkflowExecuteRequest):
    """Execute workflow"""
    try:
        # Generate request_id if not provided
        if not request.request_id:
            request.request_id = generate_request_id()
        
        logger.info(f"Executing workflow: {request.workflow_id}, request_id: {request.request_id}")
        
        async with rpc_client:
            result = await rpc_client.execute_workflow(
                request.request_id,
                request.workflow_id,
                request.params
            )
        
        return {
            "success": True,
            "data": result,
            "request_id": request.request_id
        }
        
    except Exception as e:
        logger.error(f"Failed to execute workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{request_id}")
async def get_workflow_status(request_id: str):
    """Get workflow status"""
    try:
        logger.debug(f"Getting workflow status: {request_id}")
        
        async with rpc_client:
            result = await rpc_client.get_workflow_status(request_id)
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Failed to get workflow status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/result/{request_id}")
async def get_workflow_result(request_id: str):
    """Get workflow result"""
    try:
        logger.info(f"Getting workflow result: {request_id}")
        
        async with rpc_client:
            result = await rpc_client.get_workflow_result(request_id)
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Failed to get workflow result: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cancel/{request_id}")
async def cancel_workflow(request_id: str):
    """Cancel workflow"""
    try:
        logger.info(f"Cancelling workflow: {request_id}")
        
        async with rpc_client:
            result = await rpc_client.cancel_workflow(request_id)
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Failed to cancel workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
async def list_workflows():
    """List available workflows"""
    try:
        logger.debug("Listing workflows")
        
        async with rpc_client:
            result = await rpc_client.list_workflows()
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Failed to list workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/schema/{workflow_id}")
async def get_workflow_schema(workflow_id: str):
    """Get workflow schema definition"""
    try:
        logger.debug(f"Getting workflow schema: {workflow_id}")
        
        async with rpc_client:
            result = await rpc_client.get_workflow_schema(workflow_id)
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Failed to get workflow schema: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search")
async def search_workflows(request: Dict[str, Any]):
    """Search workflows"""
    try:
        query = request.get("query", "")
        logger.debug(f"Searching workflows: {query}")
        
        async with rpc_client:
            result = await rpc_client.search_workflows(query)
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Failed to search workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))