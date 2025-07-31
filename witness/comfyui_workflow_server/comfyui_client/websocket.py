import websocket
import json
from threading import Thread
from typing import Optional, Callable
from .utils.logger import get_logger

class ComfyUIWebSocketClient:
    """
    处理 WebSocket 连接和消息处理。

    如果未直接给出完整 `url`，可以传入 host/port/client_id 自动拼接。
    """
    def __init__(self, url: Optional[str] = None, *, host: Optional[str] = None, 
                 port: Optional[int] = None, client_id: Optional[str] = None, 
                 debug: bool = False):
        # 若提供了 host/port 则组装 URL
        if url is None and host and port:
            # 若提供 client_id 则追加查询参数以订阅专属事件
            if client_id:
                url = f"ws://{host}:{port}/ws?clientId={client_id}"
            else:
                url = f"ws://{host}:{port}/ws"
        elif url is None:
            raise ValueError("必须提供 url 或 host+port 组合")

        self.url = url
        self.debug = debug
        
        # 根据调试模式设置 websocket 追踪
        if debug:
            websocket.enableTrace(True)
        
        self.ws = websocket.WebSocketApp(
            url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )
        self.logger = get_logger("ComfyUIWebSocketClient")
        self.is_connected = False
        self.progress_callback: Optional[Callable] = None
        self.completion_callback: Optional[Callable] = None

    def on_message(self, ws, message):
        """
        处理传入消息。根据消息类型调用相应的回调。
        基于 ComfyUI 源码的真实消息格式。
        """
        try:
            data = json.loads(message)
            if isinstance(data, dict):
                event_type = data.get("type")
                event_data = data.get("data", {})
                
                # 调试日志：记录收到的WebSocket消息
                if self.debug:
                    self.logger.debug(f"收到WebSocket消息: type={event_type}, data={event_data}")
                
                # 处理真实的进度更新事件（ComfyUI 发送的采样器进度）
                if event_type == "progress" and self.progress_callback:
                    # ComfyUI 格式: {"value": value, "max": total, "prompt_id": prompt_id, "node": node_id}
                    prompt_id = event_data.get("prompt_id")
                    if prompt_id:
                        current_value = event_data.get("value", 0)
                        max_value = event_data.get("max", 100)
                        node_id = event_data.get("node")
                        
                        # 计算百分比进度
                        if max_value > 0:
                            progress_percent = min(100, (current_value / max_value) * 100)
                        else:
                            progress_percent = 0
                        
                        # 检查是否是主要采样进度 vs 快速预处理进度
                        # 采样器通常有多步骤 (max_value > 1)，而预处理节点通常只有1步
                        is_main_sampling = max_value > 1
                        
                        # 跟踪采样状态
                        if not hasattr(self, '_sampling_status'):
                            self._sampling_status = {}
                        
                        if prompt_id not in self._sampling_status:
                            self._sampling_status[prompt_id] = {
                                'in_main_sampling': False,
                                'last_progress': 0
                            }
                        
                        status = self._sampling_status[prompt_id]
                        
                        if is_main_sampling:
                            # 这是主要采样节点，开始主要采样阶段
                            if not status['in_main_sampling']:
                                status['in_main_sampling'] = True
                                status['last_progress'] = 0
                                self.logger.info(f"开始主要采样阶段: {prompt_id} - 节点: {node_id}")
                            
                            # 更新并发送主要采样进度
                            status['last_progress'] = progress_percent
                            
                            progress_data = {
                                "value": progress_percent,
                                "max": 100,
                                "current_step": current_value,
                                "total_steps": max_value,
                                "node": node_id,
                                "prompt_id": prompt_id
                            }
                            
                            # self.logger.info(f"采样器进度更新 {prompt_id}: {current_value}/{max_value} ({progress_percent:.1f}%) - 节点: {node_id}")
                            self.progress_callback(prompt_id, progress_data)
                            
                        else:
                            # 这是预处理节点（max_value <= 1），检查是否应该忽略
                            if status['in_main_sampling']:
                                # 已经在主要采样阶段，忽略预处理节点的进度
                                if self.debug:
                                    self.logger.debug(f"忽略预处理节点进度 {prompt_id}: 节点{node_id} ({progress_percent:.1f}%) - 已在主要采样阶段")
                            else:
                                # 还没开始主要采样，可以显示预处理进度，但限制在低值
                                # 预处理阶段进度不超过10%
                                limited_progress = min(10, progress_percent * 0.1)
                                
                                progress_data = {
                                    "value": limited_progress,
                                    "max": 100,
                                    "current_step": current_value,
                                    "total_steps": max_value,
                                    "node": node_id,
                                    "prompt_id": prompt_id,
                                    "phase": "preprocessing"
                                }
                                
                                if self.debug:
                                    self.logger.debug(f"预处理进度 {prompt_id}: {current_value}/{max_value} ({limited_progress:.1f}%) - 节点: {node_id}")
                                self.progress_callback(prompt_id, progress_data)
                
                # 处理执行开始事件
                elif event_type == "execution_start" and self.progress_callback:
                    prompt_id = event_data.get("prompt_id")
                    if prompt_id:
                        start_data = {
                            "value": 0,
                            "max": 100,
                            "status": "started",
                            "prompt_id": prompt_id
                        }
                        self.logger.info(f"工作流执行开始: {prompt_id}")
                        self.progress_callback(prompt_id, start_data)
                
                # 处理节点开始执行事件
                elif event_type == "executing" and self.progress_callback:
                    # ComfyUI 格式: {"node": unique_id, "display_node": display_node_id, "prompt_id": prompt_id}
                    prompt_id = event_data.get("prompt_id")
                    node_id = event_data.get("node")
                    display_node = event_data.get("display_node")
                    
                    if prompt_id:
                        if node_id is None:
                            # 这通常表示队列处理或准备阶段，不是执行完成
                            # 不发送进度更新，避免错误的100%跳跃
                            if self.debug:
                                self.logger.debug(f"队列处理或准备阶段: {prompt_id}")
                        else:
                            # 节点开始执行 - 如果这是第一个节点，发送开始事件
                            if not hasattr(self, '_started_prompts'):
                                self._started_prompts = set()
                            
                            if prompt_id not in self._started_prompts:
                                # 第一个节点开始执行，发送任务开始事件
                                start_data = {
                                    "value": 0,
                                    "max": 100,
                                    "status": "started",
                                    "prompt_id": prompt_id,
                                    "first_node": node_id
                                }
                                self.logger.info(f"任务开始执行 (第一个节点): {prompt_id} - 节点: {node_id}")
                                self.progress_callback(prompt_id, start_data)
                                self._started_prompts.add(prompt_id)
                                
                            # 发送节点状态通知（仅调试模式）
                            if self.debug:
                                status_data = {
                                    "status": "executing_node",
                                    "node": node_id,
                                    "display_node": display_node,
                                    "prompt_id": prompt_id
                                }
                                self.logger.info(f"节点开始执行: {node_id} (显示节点: {display_node}, 工作流: {prompt_id})")
                                self.progress_callback(prompt_id, status_data)
                
                # 处理节点执行完成事件（包含输出数据）
                elif event_type == "executed":
                    # ComfyUI 格式: {"node": unique_id, "display_node": display_node_id, "output": output_ui, "prompt_id": prompt_id}
                    prompt_id = event_data.get("prompt_id")
                    node_id = event_data.get("node")
                    display_node = event_data.get("display_node")
                    output_data = event_data.get("output", {})
                    
                    if prompt_id and self.debug:
                        self.logger.info(f"节点执行完成: {node_id} (显示节点: {display_node}, 工作流: {prompt_id})")
                        if output_data:
                            self.logger.debug(f"节点输出数据: {list(output_data.keys())}")
                
                # 处理缓存执行事件
                elif event_type == "execution_cached":
                    prompt_id = event_data.get("prompt_id")
                    cached_nodes = event_data.get("nodes", [])
                    if self.debug:
                        self.logger.debug(f"缓存执行节点 (工作流: {prompt_id}): {cached_nodes}")
                
                # 处理执行中断事件
                elif event_type == "execution_interrupted":
                    prompt_id = event_data.get("prompt_id")
                    node_id = event_data.get("node_id")
                    if prompt_id and self.completion_callback:
                        self.logger.warning(f"工作流执行被中断: {prompt_id} (节点: {node_id})")
                        # 清理已开始的提示记录和采样状态
                        if hasattr(self, '_started_prompts') and prompt_id in self._started_prompts:
                            self._started_prompts.remove(prompt_id)
                        if hasattr(self, '_sampling_status') and prompt_id in self._sampling_status:
                            del self._sampling_status[prompt_id]
                        self.completion_callback(prompt_id, {"status": "interrupted", "node_id": node_id})
                
                # 处理执行错误
                elif event_type == "execution_error" and self.completion_callback:
                    prompt_id = event_data.get("prompt_id")
                    node_id = event_data.get("node_id")
                    exception_message = event_data.get("exception_message", "")
                    exception_type = event_data.get("exception_type", "")
                    if prompt_id:
                        self.logger.error(f"工作流执行错误: {prompt_id} - 节点: {node_id}, 错误: {exception_message}")
                        # 清理已开始的提示记录和采样状态
                        if hasattr(self, '_started_prompts') and prompt_id in self._started_prompts:
                            self._started_prompts.remove(prompt_id)
                        if hasattr(self, '_sampling_status') and prompt_id in self._sampling_status:
                            del self._sampling_status[prompt_id]
                        self.completion_callback(prompt_id, {
                            "status": "failed", 
                            "error": event_data,
                            "node_id": node_id,
                            "exception_message": exception_message,
                            "exception_type": exception_type
                        })
                
                # 处理工作流完成事件
                elif event_type == "execution_success" and self.completion_callback:
                    prompt_id = event_data.get("prompt_id")
                    if prompt_id:
                        self.logger.info(f"工作流执行成功完成: {prompt_id}")
                        # 清理已开始的提示记录和采样状态
                        if hasattr(self, '_started_prompts') and prompt_id in self._started_prompts:
                            self._started_prompts.remove(prompt_id)
                        if hasattr(self, '_sampling_status') and prompt_id in self._sampling_status:
                            del self._sampling_status[prompt_id]
                        self.completion_callback(prompt_id, {"status": "completed", "result": event_data})

                # 处理状态更新事件（连接时发送的初始状态）
                elif event_type == "status":
                    sid = event_data.get("sid")
                    status = event_data.get("status", {})
                    if self.debug:
                        exec_info = status.get("exec_info", {})
                        queue_remaining = exec_info.get("queue_remaining", 0)
                        self.logger.debug(f"状态更新 (SID: {sid}): 队列剩余 {queue_remaining} 个任务")

                # 处理其他事件类型
                else:
                    if self.debug:
                        self.logger.debug(f"收到未处理的事件: {event_type}")
                        
            else:
                if self.debug:
                    self.logger.debug(f"收到非JSON字典消息: {message}")
                    
        except json.JSONDecodeError:
            self.logger.warning(f"无法解析JSON消息: {message}")
        except Exception as e:
            self.logger.error(f"处理消息时出错: {e}")
            if self.debug:
                import traceback
                self.logger.error(f"错误详情: {traceback.format_exc()}")

    def on_error(self, ws, error):
        """
        处理 WebSocket 错误。
        """
        self.logger.error(f"WebSocket 错误: {error}")
        self.is_connected = False

    def on_close(self, ws, close_status_code, close_msg):
        """
        处理 WebSocket 连接关闭。
        """
        self.logger.info("WebSocket 连接已关闭")
        self.is_connected = False

    def on_open(self, ws):
        """
        处理连接打开后要执行的操作。
        """
        self.logger.info("WebSocket 连接已打开")
        self.is_connected = True

    def run_forever(self):
        """
        启动 WebSocket 客户端并在一个单独的线程中永久运行它。
        """
        thread = Thread(target=self.ws.run_forever, daemon=True)
        thread.start()
        self.logger.info("WebSocket 客户端已在新线程中启动。")

    def set_progress_callback(self, callback):
        """设置进度回调函数"""
        self.progress_callback = callback

    def set_completion_callback(self, callback):
        """设置完成回调函数"""
        self.completion_callback = callback

    async def disconnect(self):
        """异步关闭WebSocket连接"""
        self.close()

    def close(self):
        """
        关闭 WebSocket 连接。
        """
        self.ws.close() 