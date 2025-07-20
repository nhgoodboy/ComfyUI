"""
银行级安全客户端示例

演示如何正确使用ComfyUI工作流服务器的五层安全防护：
1. IP白名单验证
2. API密钥认证
3. 请求签名验证
4. 速率限制保护
5. JWT令牌验证

这个客户端展示了完整的安全交互流程。
"""

import asyncio
import aiohttp
import hashlib
import hmac
import time
import json
from typing import Optional, Dict, Any, List
from pathlib import Path
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecureComfyUIClient:
    """银行级安全的ComfyUI客户端"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_secret_key: str = "",
        user_token: str = ""
    ):
        """
        初始化安全客户端
        
        Args:
            base_url: 服务器地址
            api_secret_key: API密钥（用于签名）
            user_token: 用户JWT令牌
        """
        self.base_url = base_url.rstrip('/')
        self.api_secret_key = api_secret_key.encode()
        self.user_token = user_token
        self.session = None
        
        # 请求计数器（用于监控速率限制）
        self.request_count = 0
        self.last_request_time = 0
        
        logger.info(f"安全客户端初始化完成: {base_url}")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=300),
            connector=aiohttp.TCPConnector(
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30
            )
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        if self.session:
            await self.session.close()
    
    def _generate_signature(
        self, 
        method: str, 
        path: str, 
        body: bytes = b"", 
        query: str = "",
        timestamp: Optional[str] = None
    ) -> Dict[str, str]:
        """生成请求签名"""
        if timestamp is None:
            timestamp = str(int(time.time()))
        
        # 计算body哈希
        body_hash = hashlib.sha256(body).hexdigest()
        
        # 签名内容：timestamp + method + path + query + body_hash
        sign_content = f"{timestamp}{method}{path}{query}{body_hash}"
        
        # 生成HMAC-SHA256签名
        signature = hmac.new(
            self.api_secret_key,
            sign_content.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return {
            "x-timestamp": timestamp,
            "x-signature": signature
        }
    
    def _get_secure_headers(
        self, 
        method: str, 
        path: str, 
        body: bytes = b"", 
        query: str = ""
    ) -> Dict[str, str]:
        """获取安全请求头"""
        headers = {
            "x-api-key": self.api_secret_key.decode(),
            "content-type": "application/json"
        }
        
        # 添加签名头
        signature_headers = self._generate_signature(method, path, body, query)
        headers.update(signature_headers)
        
        # 添加JWT令牌
        if self.user_token:
            headers["authorization"] = f"Bearer {self.user_token}"
        
        return headers
    
    def _rate_limit_check(self):
        """速率限制检查"""
        current_time = time.time()
        if current_time - self.last_request_time < 2:  # 最少2秒间隔
            wait_time = 2 - (current_time - self.last_request_time)
            logger.warning(f"速率限制保护，等待 {wait_time:.2f} 秒")
            time.sleep(wait_time)
        
        self.request_count += 1
        self.last_request_time = time.time()
    
    async def _make_request(
        self, 
        method: str, 
        path: str, 
        data: Optional[Dict] = None,
        query_params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """发送安全请求"""
        if not self.session:
            raise RuntimeError("客户端未初始化，请使用 async with")
        
        # 速率限制检查
        self._rate_limit_check()
        
        # 构建完整URL
        url = f"{self.base_url}{path}"
        
        # 准备请求体
        body = b""
        if data:
            body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        
        # 构建查询字符串
        query = ""
        if query_params:
            query = "&".join([f"{k}={v}" for k, v in query_params.items()])
            if query:
                url += f"?{query}"
        
        # 获取安全头部
        headers = self._get_secure_headers(method, path, body, query)
        
        logger.info(f"发送安全请求: {method} {url}")
        
        try:
            async with self.session.request(
                method=method,
                url=url,
                headers=headers,
                data=body if body else None,
                params=query_params
            ) as response:
                result = await response.json()
                
                if response.status == 200:
                    logger.info(f"请求成功: {response.status}")
                    return result
                else:
                    logger.error(f"请求失败: {response.status} - {result}")
                    raise Exception(f"请求失败: {response.status} - {result}")
                    
        except Exception as e:
            logger.error(f"请求异常: {e}")
            raise
    
    async def get_styles(self) -> List[Dict[str, Any]]:
        """获取可用风格列表"""
        return await self._make_request("GET", "/api/v1/styles")
    
    async def create_style_task(
        self, 
        style_name: str, 
        image_file: str,
        **kwargs
    ) -> Dict[str, Any]:
        """创建风格转换任务"""
        data = {
            "style_name": style_name,
            "image_file": image_file,
            **kwargs
        }
        return await self._make_request("POST", "/api/v1/styles/transform", data)
    
    async def get_task_status(self, request_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        return await self._make_request("GET", f"/api/v1/tasks/{request_id}")
    
    async def get_task_result(self, request_id: str) -> Dict[str, Any]:
        """获取任务结果"""
        return await self._make_request("GET", f"/api/v1/tasks/{request_id}/result")
    
    async def upload_file(self, file_path: str) -> Dict[str, Any]:
        """上传文件"""
        # 注意：文件上传需要特殊处理，这里简化示例
        logger.info(f"上传文件: {file_path}")
        # 实际实现需要处理multipart/form-data
        return {"file_id": "mock_file_id"}
    
    async def get_user_tasks(self) -> List[Dict[str, Any]]:
        """获取用户任务列表"""
        return await self._make_request("GET", "/api/v1/tasks")
    
    async def delete_task(self, request_id: str) -> Dict[str, Any]:
        """删除任务"""
        return await self._make_request("DELETE", f"/api/v1/tasks/{request_id}")
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return await self._make_request("GET", "/health")


class SecureWorkflowManager:
    """安全工作流管理器"""
    
    def __init__(self, client: SecureComfyUIClient):
        self.client = client
    
    async def execute_style_transformation(
        self, 
        style_name: str, 
        image_path: str,
        wait_for_completion: bool = True,
        max_wait_time: int = 300
    ) -> Dict[str, Any]:
        """执行完整的风格转换流程"""
        logger.info(f"开始风格转换: {style_name}")
        
        try:
            # 步骤1：上传图片
            logger.info("步骤1: 上传图片")
            upload_result = await self.client.upload_file(image_path)
            file_id = upload_result["file_id"]
            
            # 步骤2：创建转换任务
            logger.info("步骤2: 创建转换任务")
            task_result = await self.client.create_style_task(
                style_name=style_name,
                image_file=file_id
            )
            request_id = task_result["request_id"]
            
            # 步骤3：等待任务完成（如果需要）
            if wait_for_completion:
                logger.info("步骤3: 等待任务完成")
                result = await self._wait_for_task_completion(request_id, max_wait_time)
                return result
            else:
                return {"request_id": request_id, "status": "submitted"}
                
        except Exception as e:
            logger.error(f"风格转换失败: {e}")
            raise
    
    async def _wait_for_task_completion(
        self, 
        request_id: str, 
        max_wait_time: int
    ) -> Dict[str, Any]:
        """等待任务完成"""
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            status = await self.client.get_task_status(request_id)
            
            if status["status"] == "completed":
                logger.info("任务完成，获取结果")
                return await self.client.get_task_result(request_id)
            elif status["status"] == "failed":
                raise Exception(f"任务失败: {status.get('error', 'Unknown error')}")
            
            logger.info(f"任务状态: {status['status']}, 等待中...")
            await asyncio.sleep(5)
        
        raise TimeoutError(f"任务超时: {max_wait_time} 秒")


async def main():
    """主函数 - 演示安全客户端使用"""
    # 配置（实际使用时应从环境变量获取）
    config = {
        "base_url": "http://localhost:8000",
        "api_secret_key": "your-api-secret-key-here",
        "user_token": "your-jwt-token-here"
    }
    
    logger.info("=== 银行级安全客户端示例 ===")
    
    try:
        # 创建安全客户端
        async with SecureComfyUIClient(**config) as client:
            # 健康检查
            logger.info("执行健康检查...")
            health = await client.health_check()
            logger.info(f"服务状态: {health}")
            
            # 获取可用风格
            logger.info("获取可用风格...")
            styles = await client.get_styles()
            logger.info(f"可用风格: {[s['name'] for s in styles['styles']]}")
            
            # 创建工作流管理器
            workflow_manager = SecureWorkflowManager(client)
            
            # 执行风格转换（示例）
            if styles['styles']:
                style_name = styles['styles'][0]['name']
                image_path = "example.jpg"  # 示例图片路径
                
                logger.info(f"执行风格转换: {style_name}")
                result = await workflow_manager.execute_style_transformation(
                    style_name=style_name,
                    image_path=image_path,
                    wait_for_completion=True
                )
                logger.info(f"转换结果: {result}")
            
            # 获取用户任务
            logger.info("获取用户任务列表...")
            tasks = await client.get_user_tasks()
            logger.info(f"任务数量: {len(tasks.get('tasks', []))}")
            
    except Exception as e:
        logger.error(f"示例执行失败: {e}")


def create_test_token(user_id: str, secret_key: str) -> str:
    """创建测试JWT令牌"""
    import jwt
    from datetime import datetime, timedelta
    
    payload = {
        "user_id": user_id,
        "permissions": ["read_styles", "create_task", "read_task", "upload_file"],
        "roles": ["user"],
        "iat": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp())
    }
    
    return jwt.encode(payload, secret_key, algorithm="HS256")


def generate_security_config():
    """生成安全配置示例"""
    import secrets
    
    api_secret_key = secrets.token_hex(32)
    jwt_secret_key = secrets.token_hex(32)
    
    print("=== 安全配置示例 ===")
    print(f"API_SECRET_KEY={api_secret_key}")
    print(f"JWT_SECRET_KEY={jwt_secret_key}")
    print(f"ALLOWED_IPS=127.0.0.1,::1,192.168.0.0/24")
    print(f"RATE_LIMIT_PER_IP=60")
    print(f"RATE_LIMIT_PER_USER=30")
    print(f"SIGNATURE_TIMEOUT=300")
    print(f"TOKEN_EXPIRY_MINUTES=60")
    
    # 生成测试令牌
    test_token = create_test_token("test_user", jwt_secret_key)
    print(f"\n测试JWT令牌:")
    print(f"USER_TOKEN={test_token}")
    
    print("\n=== 环境变量设置 ===")
    print("export API_SECRET_KEY='your-api-secret-key'")
    print("export JWT_SECRET_KEY='your-jwt-secret-key'")
    print("export ALLOWED_IPS='127.0.0.1,::1,192.168.0.0/24'")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "generate-config":
        generate_security_config()
    else:
        # 运行示例
        asyncio.run(main())
        
        print("\n=== 使用说明 ===")
        print("1. 生成安全配置: python secure_client_example.py generate-config")
        print("2. 设置环境变量: export API_SECRET_KEY='your-key'")
        print("3. 启动服务器: python -m app.main")
        print("4. 运行客户端: python secure_client_example.py")
        print("\n这个示例展示了银行级安全防护的完整使用流程。") 