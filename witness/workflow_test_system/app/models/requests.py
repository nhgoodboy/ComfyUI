"""
Request and response models for the workflow test system
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel

class RPCRequest(BaseModel):
    """RPC request model"""
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[str] = None

class RPCResponse(BaseModel):
    """RPC response model"""
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None

class WorkflowExecuteRequest(BaseModel):
    """Workflow execution request"""
    workflow_id: str
    params: Dict[str, Any]
    request_id: Optional[str] = None

class WorkflowStatusRequest(BaseModel):
    """Workflow status query request"""
    request_id: str

class FileGetRequest(BaseModel):
    """File retrieval request"""
    filename: str

class FileListRequest(BaseModel):
    """File list request"""  
    limit: Optional[int] = 100
    offset: Optional[int] = 0
    pattern: Optional[str] = "*"

class SessionCreateResponse(BaseModel):
    """Session creation response"""
    session_id: str
    created_at: str

class TaskStatusResponse(BaseModel):
    """Task status response"""
    request_id: str
    status: str
    progress: float
    message: str
    timestamp: str