# tests_server/performance/locustfile.py
import time
import hmac
import hashlib
import json
from locust import HttpUser, task, between

# --- 测试配置 ---
# 在实际运行locust时，这些值最好通过环境变量传入
# 为方便起见，我们在这里硬编码
API_KEY = "test-api-key" 
API_SECRET_KEY = "test_api_secret_key_for_predictable_signatures_1234567890"
BASE_URL = "http://127.0.0.1:8000" # 假设服务运行在本地8000端口
USER_ID_PREFIX = "locust-user"

class SecureWebServiceUser(HttpUser):
    """
    模拟一个安全Web服务的用户。
    这个用户会执行一个完整的操作流程：获取令牌 -> 创建任务。
    """
    wait_time = between(1, 5)  # 每个任务执行后等待1到5秒
    
    def on_start(self):
        """
        当一个虚拟用户开始测试时调用。
        主要任务是获取该用户的JWT令牌。
        """
        self.user_id = f"{USER_ID_PREFIX}-{self.environment.runner.user_count}"
        self.token = self._get_auth_token()
        if not self.token:
            print(f"用户 {self.user_id} 未能获取令牌，将停止。")
            self.environment.runner.quit()

    def _get_secure_headers(self, method: str, path: str, body: dict = None, token: str = None) -> dict:
        """一个辅助方法，用于生成签名和头部。"""
        timestamp = str(int(time.time()))
        body_str = json.dumps(body, separators=(',', ':'), ensure_ascii=False) if body else ""
        message = f"{method.upper()}\n{path}\n{timestamp}\n{body_str}"
        signature = hmac.new(API_SECRET_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()
        
        headers = {
            'x-api-key': API_KEY,
            'x-timestamp': timestamp,
            'x-signature': signature,
            'Content-Type': 'application/json',
        }
        if token:
            headers['Authorization'] = f"Bearer {token}"
        return headers

    def _get_auth_token(self) -> str | None:
        """获取JWT认证令牌。"""
        path = "/api/v1/auth/token"
        method = "POST"
        body = {"user_id": self.user_id}
        headers = self._get_secure_headers(method, path, body)
        
        with self.client.post(path, json=body, headers=headers, name="/auth/token", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
                return response.json().get("access_token")
            else:
                response.failure(f"获取令牌失败: {response.status_code} - {response.text}")
                return None

    @task
    def create_transform_task(self):
        """
        定义一个核心任务：创建一个图像转换任务。
        这是 locust 将会并发执行的主要操作。
        """
        if not self.token:
            # 如果没有令牌，则无法继续执行此任务
            return

        path = "/api/v1/tasks"
        method = "POST"
        body = {
            "input_file_id": "locust_test_file.png", # 使用一个固定的假文件ID
            "style_id": "clay",
            "params": {"strength": 0.8}
        }
        headers = self._get_secure_headers(method, path, body, self.token)
        
        with self.client.post(path, json=body, headers=headers, name="/tasks/create", catch_response=True) as response:
            if response.status_code == 202:
                response.success()
            else:
                response.failure(f"创建任务失败: {response.status_code} - {response.text}") 