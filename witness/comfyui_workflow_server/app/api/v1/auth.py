from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from typing import Dict

from ...services.jwt_service import JWTService
from ...models.api_models import Token

router = APIRouter()

@router.post("/auth/token", response_model=Token)
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """通过API密钥和密钥获取JWT令牌"""
    user_service = request.app.state.user_service
    jwt_service: JWTService = request.app.state.jwt_service

    user = user_service.get_user_by_api_key(form_data.username)
    if not user or not user_service.verify_password(form_data.password, user.get("hashed_secret")):
        raise HTTPException(
            status_code=401,
            detail="无效的API密钥或密钥",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = jwt_service.create_access_token(data={"sub": user.get("username")})
    return {"access_token": access_token, "token_type": "bearer"} 