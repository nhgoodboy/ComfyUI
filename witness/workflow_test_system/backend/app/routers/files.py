"""
‡ö¡APIï1
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from ..models.requests import FileGetRequest, FileListRequest
from ..services.rpc_client import rpc_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/files", tags=["files"])

@router.get("/output/{filename}")
async def get_output_image(filename: str):
    """·Ö“úþG"""
    try:
        logger.debug(f"·Ö“úþG: {filename}")
        
        async with rpc_client:
            result = await rpc_client.get_output_image(filename)
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"·Ö“úþG1%: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/output/{filename}/info")
async def get_output_image_info(filename: str):
    """·Ö“úþGáo"""
    try:
        logger.debug(f"·Ö“úþGáo: {filename}")
        
        async with rpc_client:
            result = await rpc_client.get_output_image_info(filename)
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"·Ö“úþGáo1%: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/output")
async def list_output_images(
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    pattern: Optional[str] = "*"
):
    """ú“úþG"""
    try:
        logger.debug(f"ú“úþG: limit={limit}, offset={offset}, pattern={pattern}")
        
        async with rpc_client:
            result = await rpc_client.list_output_images(limit, offset, pattern)
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"ú“úþG1%: {e}")
        raise HTTPException(status_code=500, detail=str(e))