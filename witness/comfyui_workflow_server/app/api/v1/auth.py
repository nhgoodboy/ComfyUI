from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from comfyui_workflow_server.app.services.jwt_service import get_jwt_service, JWTService
from comfyui_workflow_server.app.services.user_service import user_service, APIUser

router = APIRouter()

class TokenRequest(BaseModel):
    api_key: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/auth/token", response_model=TokenResponse)
async def login_for_access_token(
    form_data: TokenRequest,
    jwt_service: JWTService = Depends(get_jwt_service)
):
    """
    使用API Key获取JWT访问令牌
    """
    user = user_service.get_user_by_api_key(form_data.api_key)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的API密钥",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = jwt_service.generate_token(user_id=user.api_key)
    return {"access_token": access_token, "token_type": "bearer"} 