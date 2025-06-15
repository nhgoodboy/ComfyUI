# witness/core/comfy_client.py

import time
import uuid
import logging # 新增导入
from urllib.parse import urlparse
from typing import Dict, Any, Optional, List

from witness.utils.http_client import HttpClient
from witness.api_clients.file_client import FileClient
from witness.api_clients.prompt_client import PromptClient
from witness.api_clients.system_client import SystemClient
from witness.api_clients.websocket_client import WebSocketClient

logger = logging.getLogger(__name__) # 新增 logger

class ComfyUIClient:
    """高级客户端，用于与 ComfyUI 服务器交互。"""

    def __init__(self, server_address: str, client_id: Optional[str] = None):
        """
        初始化 ComfyUIClient。

        参数:
        - server_address (str): ComfyUI 服务器的完整地址 (例如, "http://127.0.0.1:8188")。
        - client_id (str, optional): WebSocket 连接的客户端 ID。如果为 None，则会自动生成一个。
        """
        self.server_address = server_address
        self.client_id = client_id or str(uuid.uuid4())

        parsed_url = urlparse(server_address)
        self.scheme = parsed_url.scheme
        self.host = parsed_url.hostname
        self.port = parsed_url.port

        if not self.host or not self.port:
            raise ValueError("无效的服务器地址，无法解析主机或端口。")

        self.http_client = HttpClient(base_url=server_address)
        self.file_client = FileClient(self.http_client)
        self.prompt_client = PromptClient(self.http_client)
        self.system_client = SystemClient(self.http_client)
        # WebSocketClient 初始化需要 host 和 port，而不是完整的 base_url
        self.ws_client = WebSocketClient(host=self.host, port=self.port, client_id=self.client_id)
        self.is_ws_connected = False

        logger.info(f"ComfyUIClient 初始化完毕，目标服务器: {server_address}, 客户端ID: {self.client_id}")

    def connect(self) -> bool:
        """检查与 ComfyUI 服务器的基本连接性。"""
        try:
            # 尝试获取系统状态作为连接检查
            stats = self.system_client.get_system_stats() # This is a synchronous call
            if stats and 'system' in stats and 'devices' in stats['system']:
                logger.info("成功连接到 ComfyUI 并获取系统状态。")
                return True
            logger.warning("连接到 ComfyUI 但系统状态响应格式不正确。")
            # Consider raising an error or returning False based on strictness
            return False # Or True if a partial connection is acceptable for some uses
        except ConnectionError as ce:
            logger.error(f"连接到 ComfyUI 失败 (ConnectionError): {ce}")
            raise # Re-raise specific connection errors
        except Exception as e:
            logger.error(f"连接到 ComfyUI 时发生未知错误: {e}", exc_info=True)
            raise # Re-raise other critical errors

    def upload_image(
        self, 
        image_bytes: bytes, 
        filename: str, 
        subfolder: Optional[str] = None, 
        image_type: str = "input", 
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        上传图像到 ComfyUI 服务器。

        参数:
        - image_bytes (bytes): 图像的字节数据。
        - filename (str): 在服务器上保存的文件名。
        - subfolder (str, optional): ComfyUI input/output 目录下的子文件夹。
        - image_type (str): 图像类型，通常是 'input' 或 'temp'。
        - overwrite (bool): 是否覆盖同名文件。

        返回:
        - dict: ComfyUI API 的响应，通常包含 'name', 'subfolder', 'type'。
        """
        logger.info(f"准备上传图像 '{filename}' 到子文件夹 '{subfolder or ""}' (类型: {image_type})，覆盖: {overwrite}")
        response = self.file_client.upload_image(
            image_bytes=image_bytes,
            filename=filename,
            subfolder=subfolder,
            type=image_type,
            overwrite=overwrite
        )
        logger.debug(f"图像上传 API 响应: {response}")
        # 确保返回的是包含服务器端文件路径信息的字典
        # 例如: {'name': 'example.png', 'subfolder': 'my_uploads', 'type': 'input'}
        # 这对于工作流中的 LoadImage 节点至关重要
        if 'name' not in response:
            raise ValueError(f"图像上传失败或响应格式不正确: {response}")
        return response

    def queue_prompt(self, workflow_api_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        将工作流（prompt）提交到 ComfyUI 队列。

        参数:
        - workflow_api_json (dict): ComfyUI API 格式的工作流 JSON。

        返回:
        - dict: API 响应，包含 'prompt_id', 'number', 'node_errors'。
        """
        logger.info(f"准备将工作流提交到队列。客户端ID: {self.client_id}")
        # PromptClient 的 queue_prompt 可能需要 client_id 作为参数，或者它内部处理
        # 查阅 PromptClient 实现，它似乎不直接使用 client_id，而是将其嵌入 prompt 数据中
        prompt_data_with_client_id = {
            "prompt": workflow_api_json,
            "client_id": self.client_id
        }
        response = self.prompt_client.queue_prompt(prompt_data_with_client_id) # 调整以匹配实际参数
        logger.debug(f"工作流提交 API 响应: {response}")
        if 'prompt_id' not in response:
            raise ValueError(f"提交工作流失败或响应格式不正确: {response}")
        return response

    def get_prompt_history(self, prompt_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取指定 prompt_id 的历史记录，或所有历史记录。

        参数:
        - prompt_id (str, optional): 要获取历史记录的特定 prompt_id。

        返回:
        - dict: 包含历史数据的 API 响应。
        """
        if prompt_id:
            logger.info(f"获取 Prompt ID '{prompt_id}' 的历史记录。")
            return self.prompt_client.get_history(prompt_id)
        else:
            logger.info("获取所有 Prompt 历史记录。")
            return self.prompt_client.get_history()

    async def wait_for_output_ws(self, prompt_id: str, timeout: int = 120) -> List[Dict[str, Any]]:
        """
        通过 WebSocket 等待指定 prompt_id 的执行完成并收集输出。
        这是一个异步方法。

        参数:
        - prompt_id (str): 要等待的 prompt_id。
        - timeout (int): 等待的超时时间（秒）。

        返回:
        - list: 包含输出节点数据的列表 (例如，来自 SaveImage 节点的图像信息)。
        """
        logger.info(f"[WebSocket] 开始为 Prompt ID '{prompt_id}' 等待输出 (超时: {timeout}s)..." )
        outputs = []
        start_time = time.time()

        if not self.is_ws_connected:
            try:
                await self.ws_client.connect()
                self.is_ws_connected = True
                logger.info("[WebSocket] 已连接。")
            except Exception as e:
                logger.error(f"[WebSocket] 连接失败: {e}", exc_info=True)
                raise ConnectionError(f"WebSocket connection failed: {e}")

        try:
            while True:
                current_time = time.time()
                if current_time - start_time > timeout:
                    logger.warning(f"[WebSocket] 等待 Prompt ID '{prompt_id}' 超时。")
                    # Consider closing WS if it was opened by this method and timed out
                    # await self.close_websocket() # Or handle in finally
                    raise TimeoutError(f"Timeout waiting for prompt {prompt_id}")
                
                # Calculate remaining time for WebSocket receive, ensuring it's not negative
                ws_receive_timeout = max(0.1, timeout - (current_time - start_time))
                message = await self.ws_client.receive_message(timeout=min(1.0, ws_receive_timeout)) # Use shorter of 1s or remaining time
                
                if message is None: # WebSocket timed out on receive_message or no new message
                    # Check history API for completion status if WS is quiet
                    # This is a fallback and might introduce slight delays if WS messages are missed
                    if (current_time - start_time) > 5: # Start checking history after 5s
                        history = self.get_prompt_history(prompt_id)
                        if prompt_id in history:
                            status_info = history[prompt_id].get("status", {})
                            status_str = status_info.get("status_str")
                            if status_str == "success":
                                logger.info(f"[WebSocket] 通过历史记录确认 Prompt ID '{prompt_id}' 已成功完成。")
                                final_outputs_from_history = history[prompt_id].get("outputs", {})
                                processed_outputs = []
                                for node_id_hist, node_data_hist in final_outputs_from_history.items():
                                    processed_outputs.append({"node_id": node_id_hist, "outputs": node_data_hist})
                                return processed_outputs
                            elif status_str == "error":
                                logger.error(f"[WebSocket] 通过历史记录确认 Prompt ID '{prompt_id}' 执行失败: {status_info}")
                                raise RuntimeError(f"Prompt {prompt_id} execution failed: {status_info}")
                    continue # Continue waiting for WebSocket messages or timeout

                logger.debug(f"[WebSocket] 收到消息: {message}")
                if isinstance(message, dict) and message.get("type") == "executed":
                    data = message.get("data", {})
                    if data.get("prompt_id") == prompt_id:
                        logger.info(f"[WebSocket] Prompt ID '{prompt_id}' 节点 '{data.get('node')}' 已执行。")
                        node_outputs = data.get("output", {})
                        if node_outputs: 
                            outputs.append({"node_id": data.get('node'), "outputs": node_outputs})
                        
                        # Check if this is the final 'executed' message for the prompt
                        # A message with "node": null often indicates the end, but relying on history is safer.
                        # For now, we collect all outputs and rely on history check or timeout.

                # More robust completion check: if history shows completion, return immediately.
                # This check can be done less frequently if performance is a concern.
                history = self.get_prompt_history(prompt_id)
                if prompt_id in history:
                    status_info = history[prompt_id].get("status", {})
                    status_str = status_info.get("status_str")
                    if status_str == "success":
                        logger.info(f"[WebSocket] 通过历史记录确认 Prompt ID '{prompt_id}' 已成功完成 (during WS loop)。")
                        final_outputs_from_history = history[prompt_id].get("outputs", {})
                        processed_outputs = []
                        for node_id_hist, node_data_hist in final_outputs_from_history.items():
                            processed_outputs.append({"node_id": node_id_hist, "outputs": node_data_hist})
                        return processed_outputs # Return combined or history outputs
                    elif status_str == "error":
                        logger.error(f"[WebSocket] 通过历史记录确认 Prompt ID '{prompt_id}' 执行失败 (during WS loop): {status_info}")
                        raise RuntimeError(f"Prompt {prompt_id} execution failed: {status_info}")
        
        except TimeoutError: # Re-raise specific timeout error
            logger.warning(f"[WebSocket] TimeoutError for prompt {prompt_id}.")
            raise
        except ConnectionError as ce:
            logger.error(f"[WebSocket] ConnectionError during wait_for_output_ws for prompt {prompt_id}: {ce}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"[WebSocket] 等待 Prompt ID '{prompt_id}' 时发生错误: {e}", exc_info=True)
            # Ensure WebSocket is closed on unexpected error if it was opened here
            # await self.close_websocket() # Or handle in finally
            raise RuntimeError(f"Error waiting for prompt {prompt_id}: {e}")
        finally:
            # Consider if WebSocket should always be closed here or managed by the caller
            # If this method opened it and it's not needed by caller afterwards, close it.
            # For now, we assume the caller might want to reuse the connection if it's persistent.
            pass 

        # If loop finishes without returning (e.g. due to timeout but not TimeoutError exception),
        # it means no definitive success/error from history was found within timeout.
        # Return whatever outputs were collected, or an empty list if none.
        logger.warning(f"[WebSocket] Prompt ID '{prompt_id}' 未通过历史记录确认完成，返回收集到的输出 (可能不完整)。")
        return outputs

    async def close_websocket(self):
        """显式关闭 WebSocket 连接。"""
        if self.is_ws_connected:
            try:
                await self.ws_client.close()
                self.is_ws_connected = False
                logger.info("[WebSocket] 连接已关闭。")
            except Exception as e:
                logger.error(f"[WebSocket] 关闭连接时发生错误: {e}", exc_info=True)
        else:
            logger.info("[WebSocket] 连接已关闭或从未打开。")

        except Exception as e:
            print(f"[WebSocket] 等待输出时发生错误: {e}")
            # self.is_ws_connected = False # 发生错误时可能需要重置连接状态
            # await self.ws_client.close() # 确保关闭
        finally:
            # 根据策略决定是否在此处关闭 WebSocket
            # 如果客户端是长连接的，则不关闭
            pass 
        
        if not outputs:
            print(f"[WebSocket] 未能为 Prompt ID '{prompt_id}' 收集到任何输出。")
        return outputs

    async def close_websocket(self):
        if self.is_ws_connected:
            await self.ws_client.close()
            self.is_ws_connected = False
            print("[WebSocket] 连接已关闭。")

# 示例用法 (通常在异步上下文中运行 wait_for_output_ws)
# async def main_example():
#     client = ComfyUIClient(server_address="http://127.0.0.1:8188")
#     if client.connect():
#         print("连接成功")
#         # ... 执行上传、排队等操作 ...
#         # prompt_id_to_wait = "some_prompt_id_from_queue_prompt_response"
#         # outputs = await client.wait_for_output_ws(prompt_id_to_wait)
#         # print("Outputs:", outputs)
#         # await client.close_websocket()
# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(main_example())