from pydantic_settings import BaseSettings

class TestSettings(BaseSettings):
    """
    专门用于测试环境的配置。
    这些值将覆盖主应用配置中的默认值。
    """
    # 使用一个固定的、用于测试的密钥，以确保签名结果是可预测的
    API_SECRET_KEY: str = "test_api_secret_key_for_predictable_signatures_1234567890"
    JWT_SECRET_KEY: str = "test_jwt_secret_key_for_predictable_tokens_0987654321"
    
    # 允许所有IP进行测试
    ALLOWED_IPS: str = "127.0.0.1,::1,testclient"

    # 缩短签名和令牌的有效期，以便测试超时和过期逻辑
    SIGNATURE_TIMEOUT: int = 5  # 5秒
    TOKEN_EXPIRY_MINUTES: int = 1 # 1分钟
    
    # 放宽速率限制，防止测试因限流而意外失败
    RATE_LIMIT_PER_IP: int = 1000
    RATE_LIMIT_PER_USER: int = 500

    # 明确关闭调试模式
    DEBUG: bool = False

# 创建一个全局可用的测试配置实例
test_settings = TestSettings() 