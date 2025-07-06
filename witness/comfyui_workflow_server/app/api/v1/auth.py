from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from typing import Dict

from ...models.api_models import Token
from ...models.user_models import APIUser
from ...services.jwt_service import JWTService
from ...services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

async def get_current_user(
    request: Request, 
    token: str = Depends(oauth2_scheme)
) -> APIUser:
    """
    解码JWT令牌并返回当前用户。
    这是一个依赖项，可用于保护需要认证的端点。
    """
    jwt_service: JWTService = request.app.state.jwt_service
    user_service: UserService = request.app.state.user_service
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt_service.decode_token(token)
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except Exception: # Broad exception for any JWT error
        raise credentials_exception
    
    user = user_service.get_user_by_name(username)
    if user is None:
        raise credentials_exception
    return user

async def get_admin_user(current_user: APIUser = Depends(get_current_user)) -> APIUser:
    """
    一个依赖项，确保当前用户是管理员。
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="需要管理员权限"
        )
    return current_user

@router.post("/token", response_model=Token, summary="获取访问令牌")
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    使用用户名和API密钥（作为密码）进行认证，并返回一个JWT访问令牌。
    """
    user_service: UserService = request.app.state.user_service
    jwt_service: JWTService = request.app.state.jwt_service
    
    user = user_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="不正确的用户名或API密钥",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = jwt_service.generate_token({"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"} 