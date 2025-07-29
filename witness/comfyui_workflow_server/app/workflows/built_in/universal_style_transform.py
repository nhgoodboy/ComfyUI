"""
通用风格转换工作流

基于配置驱动的通用风格转换系统，支持多种风格的工作流处理。
每种风格只需要提供JSON工作流文件和配置元数据，无需重复编写代码。
"""

import copy
import json
import os
import yaml
from typing import Dict, Any, List
import logging

from ..base import BaseWorkflow, WorkflowMetadata, WorkflowParameter, WorkflowType
from ..base.parameter_types import ParameterValidator
from ...services.comfyui_service import ComfyUIService

logger = logging.getLogger(__name__)

class UniversalStyleTransformWorkflow(BaseWorkflow):
    """通用风格转换工作流
    
    基于配置驱动的工作流处理器，支持任意风格的图像转换。
    """
    
    def __init__(self, style_id: str, style_config: Dict[str, Any], comfyui_service: ComfyUIService):
        """初始化工作流
        
        Args:
            style_id: 风格ID
            style_config: 风格配置字典
            comfyui_service: ComfyUI服务实例
        """
        self.style_id = style_id
        self.style_config = style_config
        self.comfyui_service = comfyui_service
        super().__init__()
        
        # 缓存工作流JSON
        self._workflow_json_cache = None
        
        self.logger.info(f"初始化通用风格转换工作流: {style_id} - {style_config.get('name', 'Unknown')}")
    
    def get_metadata(self) -> WorkflowMetadata:
        """获取工作流元数据"""
        return WorkflowMetadata(
            id=self.style_id,
            name=self.style_config.get('name', 'Unknown Style'),
            description=self.style_config.get('description', ''),
            version="1.0.0",
            workflow_type=WorkflowType.IMAGE_TO_IMAGE,
            author="ComfyUI工作流服务器",
            tags=self.style_config.get('tags', []),
            parameters=[
                WorkflowParameter(
                    name="image_url",
                    type="string",
                    required=True,
                    description="输入图像的URL地址"
                )
            ],
            input_types=["image"],
            output_types=["image"],
            model_requirements=[],  # 不再从配置读取，由JSON工作流隐含定义
            node_requirements=[],   # 不再从配置读取，由JSON工作流隐含定义
            estimated_time=self.style_config.get('estimated_time', 45),
            gpu_required=True  # 简化假设，因为使用Flux模型
        )
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """验证和处理参数"""
        validated_params = {}
        
        # 支持两种输入方式：image_url（原有方式）或 input_image_path（新方式）
        image_url = parameters.get("image_url")
        input_image_path = parameters.get("input_image_path")
        
        if image_url:
            # 原有的URL方式
            if not isinstance(image_url, str) or not image_url.strip():
                raise ValueError("参数 'image_url' 必须是有效的URL字符串")
            
            # 检查URL格式
            if not (image_url.startswith('http://') or image_url.startswith('https://')):
                raise ValueError("参数 'image_url' 必须以 http:// 或 https:// 开头")
            
            validated_params["image_url"] = image_url.strip()
            
        elif input_image_path:
            # 新的本地文件路径方式
            if not isinstance(input_image_path, str) or not input_image_path.strip():
                raise ValueError("参数 'input_image_path' 必须是有效的文件路径")
            
            validated_params["input_image_path"] = input_image_path.strip()
            
        else:
            raise ValueError("必须提供 'image_url' 或 'input_image_path' 参数")
        
        # 添加输出文件名支持
        output_filename = parameters.get("output_filename")
        if output_filename:
            validated_params["output_filename"] = output_filename
        
        self.logger.info(f"{self.style_config.get('name', 'Unknown')} 参数验证完成")
        return validated_params
    
    async def pre_process(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """预处理步骤：处理图片并上传到ComfyUI"""
        try:
            processed_params = parameters.copy()
            
            if "image_url" in parameters:
                # URL方式：下载图片并上传到ComfyUI
                image_url = parameters["image_url"]
                self.logger.info(f"开始下载图片: {image_url}")
                
                # 使用注入的ComfyUI服务实例
                image_data = await self.comfyui_service.download_image(image_url)
                self.logger.info(f"图片下载完成，大小: {len(image_data)} bytes")
                
                # 根据风格ID生成文件名
                style_name = self.style_id.replace('_transform', '').replace('_style', '')
                filename = await self.comfyui_service.upload_image(image_data, f"{style_name}_input.jpg")
                self.logger.info(f"图片上传完成，文件名: {filename}")
                
                processed_params["image_filename"] = filename
                
            elif "input_image_path" in parameters:
                # 本地文件路径方式：读取本地文件并上传到ComfyUI
                input_image_path = parameters["input_image_path"]
                self.logger.info(f"开始处理本地文件: {input_image_path}")
                
                # 读取本地文件
                with open(input_image_path, 'rb') as f:
                    image_data = f.read()
                self.logger.info(f"本地文件读取完成，大小: {len(image_data)} bytes")
                
                # 根据风格ID生成文件名
                style_name = self.style_id.replace('_transform', '').replace('_style', '')
                filename = await self.comfyui_service.upload_image(image_data, f"{style_name}_input.jpg")
                self.logger.info(f"图片上传完成，文件名: {filename}")
                
                processed_params["image_filename"] = filename
            
            return processed_params
            
        except Exception as e:
            self.logger.error(f"图片预处理失败: {e}")
            raise ValueError(f"图片处理失败: {str(e)}")
    
    async def build_workflow(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """构建ComfyUI工作流JSON"""
        try:
            # 获取工作流JSON模板
            workflow_json = self._get_workflow_json()
            
            # 复制工作流
            workflow = copy.deepcopy(workflow_json)
            
            # 更新LoadImage节点的image参数
            image_filename = parameters.get("image_filename", "input.jpg")
            updated_workflow = self._update_load_image_node(workflow, image_filename)
            
            self.logger.info(f"{self.style_config.get('name', 'Unknown')} 工作流构建完成，包含 {len(updated_workflow)} 个节点")
            return updated_workflow
            
        except Exception as e:
            self.logger.error(f"工作流构建失败: {e}")
            raise RuntimeError(f"工作流构建失败: {str(e)}")
    
    def _get_workflow_json(self) -> Dict[str, Any]:
        """获取工作流JSON（带缓存）"""
        if self._workflow_json_cache is None:
            self._workflow_json_cache = self._load_workflow_json()
        return self._workflow_json_cache
    
    def _load_workflow_json(self) -> Dict[str, Any]:
        """从JSON文件加载工作流模板"""
        try:
            # 获取JSON模板文件路径
            workflow_file = self.style_config.get('workflow_file')
            if not workflow_file:
                raise ValueError(f"风格配置中未指定workflow_file: {self.style_id}")
            
            # 构建完整路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            template_path = os.path.join(
                current_dir, 
                "../../../workflows",
                workflow_file
            )
            
            # 规范化路径
            template_path = os.path.normpath(template_path)
            
            self.logger.info(f"加载工作流模板: {template_path}")
            
            # 读取JSON文件
            with open(template_path, 'r', encoding='utf-8') as f:
                template = json.load(f)
            
            self.logger.info(f"成功加载工作流模板 {workflow_file}，包含 {len(template)} 个节点")
            return template
            
        except FileNotFoundError:
            self.logger.error(f"工作流模板文件未找到: {template_path}")
            raise FileNotFoundError(f"工作流模板文件不存在: {template_path}")
        except json.JSONDecodeError as e:
            self.logger.error(f"工作流模板JSON解析失败: {e}")
            raise ValueError(f"工作流模板JSON格式错误: {e}")
        except Exception as e:
            self.logger.error(f"加载工作流模板时发生错误: {e}")
            raise RuntimeError(f"加载工作流模板失败: {e}")
    
    def _update_load_image_node(self, workflow: Dict[str, Any], image_filename: str) -> Dict[str, Any]:
        """智能查找并更新LoadImage节点的image参数"""
        updated_workflow = copy.deepcopy(workflow)
        
        # 遍历所有节点，查找LoadImage类型的节点
        load_image_nodes_found = 0
        for node_id, node_data in updated_workflow.items():
            if node_data.get('class_type') == 'LoadImage':
                # 更新image参数
                if 'inputs' in node_data and 'image' in node_data['inputs']:
                    old_image = node_data['inputs']['image']
                    node_data['inputs']['image'] = image_filename
                    load_image_nodes_found += 1
                    self.logger.debug(f"更新LoadImage节点 {node_id}: {old_image} -> {image_filename}")
        
        if load_image_nodes_found == 0:
            self.logger.warning(f"未找到LoadImage节点，无法设置输入图像: {image_filename}")
        elif load_image_nodes_found > 1:
            self.logger.warning(f"找到多个LoadImage节点 ({load_image_nodes_found}个)，已全部更新")
        else:
            self.logger.info(f"成功更新LoadImage节点的image参数为: {image_filename}")
        
        return updated_workflow
    
    async def post_process(self, workflow_result: Dict[str, Any]) -> Dict[str, Any]:
        """后处理步骤：下载ComfyUI图片并保存到本地"""
        try:
            # 从风格ID中提取风格名称
            style_name = self.style_id.replace('_transform', '').replace('_style', '')
            
            processed_result = {
                "output_images": [],
                "metadata": {
                    "style": style_name,
                    "workflow_type": self.style_id,
                    "style_config": {
                        "name": self.style_config.get('name', 'Unknown'),
                        "description": self.style_config.get('description', ''),
                        "version": self.style_config.get('version', '1.0.0')
                    }
                }
            }
            
            # 处理输出图片 - 从历史记录中提取
            history = workflow_result.get("history", {})
            if "outputs" in history:
                for node_id, node_output in history["outputs"].items():
                    if "images" in node_output:
                        for image_info in node_output["images"]:
                            comfyui_filename = image_info.get("filename", "")
                            if comfyui_filename:
                                # 获取期望的标准文件名
                                expected_filename = getattr(self, 'expected_output_filename', None)
                                if not expected_filename:
                                    # 如果没有预设的输出文件名，生成一个
                                    import time
                                    expected_filename = f"output_{int(time.time())}.png"
                                
                                # 下载并保存图片
                                success, local_path = await self._download_and_save_image(
                                    comfyui_filename, expected_filename
                                )
                                
                                if success:
                                    # 生成本地访问URL
                                    local_url = f"{self._get_server_base_url()}/outputs/{expected_filename}"
                                    processed_result["output_images"].append({
                                        "filename": expected_filename,
                                        "url": local_url,
                                        "local_path": local_path,
                                        "original_comfyui_filename": comfyui_filename,
                                        "type": f"{style_name}_style_image"
                                    })
                                    self.logger.info(f"图片保存成功: {expected_filename}")
                                else:
                                    # 保存失败，使用原始ComfyUI URL作为备用
                                    fallback_url = f"{self.comfyui_service.client.base_url}/view?filename={comfyui_filename}&type=output"
                                    processed_result["output_images"].append({
                                        "filename": comfyui_filename,
                                        "url": fallback_url,
                                        "error": "Failed to download from ComfyUI",
                                        "type": f"{style_name}_style_image"
                                    })
                                    self.logger.warning(f"图片保存失败，使用备用URL: {comfyui_filename}")
            
            self.logger.info(f"{self.style_config.get('name', 'Unknown')} 后处理完成，保存了 {len(processed_result['output_images'])} 张图片")
            return processed_result
            
        except Exception as e:
            self.logger.error(f"后处理失败: {e}")
            # 返回原始结果，避免完全失败
            return workflow_result
    
    def get_estimated_time(self, parameters: Dict[str, Any]) -> int:
        """根据参数估算执行时间"""
        # 从配置中获取基础时间
        base_time = self.style_config.get('estimated_time', 45)
        
        # 考虑图片下载时间（5-10秒）
        download_time = 8
        
        # 总执行时间
        estimated_time = base_time + download_time
        return max(estimated_time, 30)  # 最少30秒
    
    def get_resource_requirements(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """获取资源需求"""
        # 返回基于Flux模型的合理默认值
        return {
            "gpu_required": True,
            "estimated_memory_mb": 8192,   # 8GB内存
            "estimated_vram_mb": 12288,    # 12GB显存  
            "cpu_cores": 4,
            "disk_space_mb": 500,
            "network_required": True  # 需要网络下载图片
        }
    
    async def _download_and_save_image(self, comfyui_filename: str, target_filename: str) -> tuple[bool, str]:
        """从ComfyUI下载图片并保存到本地输出目录"""
        try:
            import aiohttp
            import aiofiles
            from pathlib import Path
            
            # 构建ComfyUI图片URL
            comfyui_url = f"{self.comfyui_service.client.base_url}/view?filename={comfyui_filename}&type=output"
            
            # 确保输出目录存在
            output_dir = Path("outputs")
            output_dir.mkdir(exist_ok=True)
            
            target_path = output_dir / target_filename
            
            self.logger.info(f"开始下载图片: {comfyui_url}")
            
            # 下载图片
            async with aiohttp.ClientSession() as session:
                async with session.get(comfyui_url) as response:
                    if response.status == 200:
                        # 保存到本地文件
                        async with aiofiles.open(target_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)
                        
                        file_size = target_path.stat().st_size
                        self.logger.info(f"图片下载成功: {target_filename}, 大小: {file_size} bytes")
                        return True, str(target_path)
                    else:
                        self.logger.error(f"下载图片失败: HTTP {response.status}")
                        return False, ""
                        
        except Exception as e:
            self.logger.error(f"下载保存图片异常: {e}")
            return False, ""

    def _get_server_base_url(self) -> str:
        """获取当前服务器的基础URL"""
        try:
            # 从配置中获取
            from ...config import get_settings
            settings = get_settings()
            return f"http://{settings.server.host}:{settings.server.port}"
        except Exception as e:
            self.logger.warning(f"获取服务器配置失败，使用默认值: {e}")
            return "http://127.0.0.1:8000"

    def validate_requirements(self) -> List[str]:
        """验证工作流运行要求"""
        missing_requirements = []
        
        # 验证工作流文件是否存在并可正确加载
        try:
            self._get_workflow_json()
        except Exception as e:
            missing_requirements.append(f"工作流文件验证失败: {str(e)}")
        
        return missing_requirements 