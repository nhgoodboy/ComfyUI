"""
÷BŒÍ”!‹
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel

class RPCRequest(BaseModel):
    """RPC÷B!‹"""
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[str] = None

class RPCResponse(BaseModel):
    """RPCÍ”!‹"""
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None

class WorkflowExecuteRequest(BaseModel):
    """å\AgL÷B"""
    workflow_id: str
    params: Dict[str, Any]
    request_id: Optional[str] = None

class WorkflowStatusRequest(BaseModel):
    """å\A¶åâ÷B"""
    request_id: str

class FileGetRequest(BaseModel):
    """‡ö·Ö÷B"""
    filename: str

class FileListRequest(BaseModel):
    """‡öh÷B"""  
    limit: Optional[int] = 100
    offset: Optional[int] = 0
    pattern: Optional[str] = "*"

class SessionCreateResponse(BaseModel):
    """ÝúÍ”"""
    session_id: str
    created_at: str

class TaskStatusResponse(BaseModel):
    """û¡¶Í”"""
    request_id: str
    status: str
    progress: float
    message: str
    timestamp: str