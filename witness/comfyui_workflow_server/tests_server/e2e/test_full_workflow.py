# tests_server/e2e/test_full_workflow.py
import pytest
import asyncio
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

# 将所有测试标记为异步
pytestmark = pytest.mark.asyncio

# --- 夹具：获取认证令牌 ---
@pytest.fixture(scope="module")
async def auth_token(async_client: AsyncClient, get_secure_headers_for_test, test_user_id):
    """模块级夹具：为E2E测试获取一个有效的JWT令牌。"""
    path = "/api/v1/auth/token"
    method = "POST"
    body = {"user_id": test_user_id}
    headers = get_secure_headers_for_test(method, path, body)
    response = await async_client.post(path, json=body, headers=headers)
    response.raise_for_status()
    return response.json()["access_token"]

# --- 端到端测试主函数 ---

@patch("app.services.comfyui_service.ComfyUIService.queue_prompt", new_callable=AsyncMock)
@patch("app.services.comfyui_service.ComfyUIService.get_history", new_callable=AsyncMock)
@patch("app.services.file_service.FileService.save_file", new_callable=AsyncMock)
async def test_happy_path_e2e(
    mock_save_file: AsyncMock,
    mock_get_history: AsyncMock,
    mock_queue_prompt: AsyncMock,
    async_client: AsyncClient,
    get_secure_headers_for_test,
    auth_token
):
    """
    测试一个完整的、成功的用户工作流（"Happy Path"）。
    1.  上传图片 -> 2. 创建转换任务 -> 3. 轮询任务状态 -> 4. 获取最终结果
    """
    # --- 步骤 0: 模拟外部依赖的返回值 ---
    
    # 模拟文件服务：当调用 save_file 时，返回一个虚拟的文件ID
    mock_save_file.return_value = "mock_file_id_12345.png"

    # 模拟ComfyUI服务：
    # 1. 当调用 queue_prompt 时，返回一个虚拟的prompt_id
    mock_prompt_id = "mock_prompt_id_abcde"
    mock_queue_prompt.return_value = {"prompt_id": mock_prompt_id}
    
    # 2. 当调用 get_history 时，模拟任务状态的演变
    #    - 第一次调用：任务正在运行
    #    - 第二次调用：任务完成，并返回输出文件信息
    mock_final_output = {
        "outputs": {
            "final_image": {
                "filename": "final_output_image.png",
                "type": "output"
            }
        }
    }
    mock_get_history.side_effect = [
        {}, # 第一次轮询，历史记录为空，表示正在运行
        {mock_prompt_id: mock_final_output} # 第二次轮询，返回结果
    ]

    # --- 步骤 1: 上传文件 ---
    upload_path = "/api/v1/files/upload"
    upload_method = "POST"
    # 对于文件上传，我们不需要JSON body，所以body=None
    # 但我们需要一个真实的multipart/form-data payload
    files = {'file': ('test_image.png', b'fake image data', 'image/png')}
    upload_headers = get_secure_headers_for_test(upload_method, upload_path, token=auth_token)
    # httpx 对 multipart 的处理方式不同，不需要手动设置 Content-Type
    del upload_headers['Content-Type']

    upload_response = await async_client.post(upload_path, files=files, headers=upload_headers)
    
    assert upload_response.status_code == 200
    upload_data = upload_response.json()
    assert "file_id" in upload_data
    input_file_id = upload_data["file_id"]
    assert input_file_id == "mock_file_id_12345.png"
    mock_save_file.assert_called_once() # 验证模拟函数被调用

    # --- 步骤 2: 创建转换任务 ---
    task_path = "/api/v1/tasks"
    task_method = "POST"
    task_body = {
        "input_file_id": input_file_id,
        "style_id": "clay", # 使用一个内置style
        "params": {}
    }
    task_headers = get_secure_headers_for_test(task_method, task_path, task_body, token=auth_token)
    
    task_response = await async_client.post(task_path, json=task_body, headers=task_headers)

    assert task_response.status_code == 202 # Accepted
    task_data = task_response.json()
    assert "request_id" in task_data
    request_id = task_data["request_id"]
    assert request_id == mock_prompt_id
    mock_queue_prompt.assert_called_once() # 验证模拟函数被调用
    
    # --- 步骤 3 & 4: 轮询任务状态并获取结果 ---
    status_path = f"/api/v1/tasks/{request_id}"
    status_method = "GET"
    status_headers = get_secure_headers_for_test(status_method, status_path, token=auth_token)
    
    final_response = None
    for i in range(3): # 设置最大轮询次数以防无限循环
        await asyncio.sleep(0.1) # 短暂等待
        response = await async_client.get(status_path, headers=status_headers)
        if response.status_code == 200:
            final_response = response
            break
        assert response.status_code == 202 # Accepted，表示仍在进行中
    
    assert final_response is not None, "任务在指定时间内未完成"
    assert final_response.status_code == 200
    result_data = final_response.json()
    
    assert result_data["status"] == "completed"
    assert "outputs" in result_data
    assert result_data["outputs"]["final_image"]["filename"] == "final_output_image.png"
    assert mock_get_history.call_count == 2 # 验证轮询了两次 