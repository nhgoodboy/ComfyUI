from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from typing import Dict

from ...models.api_models import Token

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/token", response_model=Token)
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """OAuth2兼容的token端点"""
    user_service = request.app.state.user_service
    jwt_service = request.app.state.jwt_service
    
    # 这里需要实现用户验证逻辑
    # 暂时简化处理
    user = user_service.get_user_by_api_key(form_data.client_id)
    if not user:
        raise HTTPException(status_code=400, detail="错误的API Key")

    access_token = jwt_service.generate_token(user_id=user.username)
    return {"access_token": access_token, "token_type": "bearer"} 