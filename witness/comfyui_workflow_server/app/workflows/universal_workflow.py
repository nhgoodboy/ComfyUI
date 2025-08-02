"""
通用工作流执行器

基于配置驱动的通用工作流处理系统，支持任意类型的工作流处理
"""

import copy
import json
import os
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from .base import BaseWorkflow, WorkflowMetadata, WorkflowParameter, WorkflowType
from .base.parameter_types import ParameterValidator
from ..services.comfyui_service import ComfyUIService
from ..core.parameter_mapper import ParameterMapper
from ..core.workflow_registry import WorkflowConfig

logger = logging.getLogger(__name__)


class UniversalWorkflowExecutor(BaseWorkflow):
    """通用工作流执行器
    
    基于配置驱动的工作流处理器，支持任意类型的工作流。
    """
    
    def __init__(self, workflow_config: WorkflowConfig, comfyui_service: ComfyUIService):
        """初始化工作流执行器
        
        Args:
            workflow_config: 工作流配置对象
            comfyui_service: ComfyUI服务实例
        """
        self.workflow_config = workflow_config
        self.comfyui_service = comfyui_service
        super().__init__()
        
        # 缓存工作流JSON模板
        self._workflow_json_cache = None
        
        # 提取参数映射
        self.parameter_mappings = ParameterMapper.extract_parameter_mappings(workflow_config)
        
        self.logger.info(f"初始化通用工作流执行器: {workflow_config.id} - {workflow_config.name}")
    
    def get_metadata(self) -> WorkflowMetadata:
        """获取工作流元数据"""
        # 将配置参数转换为WorkflowParameter格式
        workflow_parameters = []
        for param_name, param_def in self.workflow_config.parameters.items():
            workflow_parameters.append(
                WorkflowParameter(
                    name=param_name,
                    type=param_def.type,
                    required=param_def.required,
                    description=param_def.description
                )
            )
        
        return WorkflowMetadata(
            id=self.workflow_config.id,
            name=self.workflow_config.name,
            description=self.workflow_config.description,
            version=self.workflow_config.version,
            workflow_type=WorkflowType.IMAGE_TO_IMAGE,  # 可以从配置中读取
            author="ComfyUI工作流服务器",
            tags=self.workflow_config.tags,
            parameters=workflow_parameters,
            input_types=self._extract_input_types(),
            output_types=["image"],  # 可以从配置中读取
            model_requirements=[],  # 从JSON工作流隐含定义
            node_requirements=[],   # 从JSON工作流隐含定义
            estimated_time=self.workflow_config.estimated_time,
            gpu_required=True  # 可以从配置中读取
        )
    
    def _extract_input_types(self) -> List[str]:
        """从参数定义中提取输入类型"""
        input_types = []
        for param_def in self.workflow_config.parameters.values():
            if param_def.type == "file":
                input_types.append("image")
        return input_types or ["image"]  # 默认至少支持图像
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """验证和处理参数"""
        try:
            # 使用工作流注册器的验证方法
            from app.core.workflow_registry import WorkflowRegistry
            
            # 创建一个临时的注册器实例来验证参数
            # 这里简化处理，直接验证必需参数和类型
            validated_params = {}
            errors = []
            
            # 检查必需参数
            for param_name, param_def in self.workflow_config.parameters.items():
                if param_def.required and param_name not in parameters:
                    errors.append(f"缺少必需参数: {param_name}")
                    continue
                
                # 获取参数值（用户提供的或默认值）
                param_value = parameters.get(param_name, param_def.default)
                
                if param_value is not None:
                    validated_params[param_name] = param_value
            
            if errors:
                raise ValueError(f"参数验证失败: {', '.join(errors)}")
            
            self.logger.info(f"{self.workflow_config.name} 参数验证完成")
            return validated_params
            
        except Exception as e:
            self.logger.error(f"参数验证失败: {e}")
            raise
    
    async def pre_process(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """预处理步骤：处理文件参数"""
        try:
            processed_params = parameters.copy()
            
            # 处理文件类型参数
            for param_name, param_def in self.workflow_config.parameters.items():
                if param_def.type == "file" and param_name in parameters:
                    file_value = parameters[param_name]
                    
                    if isinstance(file_value, str):
                        if file_value.startswith(('http://', 'https://')):
                            # URL方式：下载图片并上传到ComfyUI
                            self.logger.info(f"开始下载图片: {file_value}")
                            
                            image_data = await self.comfyui_service.download_image(file_value)
                            self.logger.info(f"图片下载完成，大小: {len(image_data)} bytes")
                            
                            # 生成文件名
                            filename = await self.comfyui_service.upload_image(
                                image_data, f"{self.workflow_config.id}_{param_name}.jpg"
                            )
                            self.logger.info(f"图片上传完成，文件名: {filename}")
                            
                            # 更新参数为ComfyUI中的文件名
                            processed_params[f"{param_name}_filename"] = filename
                            
                        else:
                            # 本地文件路径方式
                            self.logger.info(f"开始处理本地文件: {file_value}")
                            
                            with open(file_value, 'rb') as f:
                                image_data = f.read()
                            self.logger.info(f"本地文件读取完成，大小: {len(image_data)} bytes")
                            
                            filename = await self.comfyui_service.upload_image(
                                image_data, f"{self.workflow_config.id}_{param_name}.jpg"
                            )
                            self.logger.info(f"图片上传完成，文件名: {filename}")
                            
                            processed_params[f"{param_name}_filename"] = filename
            
            return processed_params
            
        except Exception as e:
            self.logger.error(f"预处理失败: {e}")
            raise ValueError(f"预处理失败: {str(e)}")
    
    async def build_workflow(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """构建ComfyUI工作流JSON"""
        try:
            # 获取工作流JSON模板
            workflow_json = self._get_workflow_json()
            
            # 准备映射参数
            mapping_params = {}
            for param_name, param_value in parameters.items():
                if param_name.endswith('_filename'):
                    # 文件参数映射到对应的节点
                    original_param = param_name.replace('_filename', '')
                    if original_param in self.parameter_mappings:
                        mapping_params[original_param] = param_value
                else:
                    # 其他参数直接映射
                    mapping_params[param_name] = param_value
            
            # 使用参数映射器应用参数
            updated_workflow = ParameterMapper.apply_parameters(
                workflow_json, mapping_params, self.parameter_mappings
            )
            
            self.logger.info(f"{self.workflow_config.name} 工作流构建完成，包含 {len(updated_workflow)} 个节点")
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
            # 使用配置的工作流目录路径
            from app.config import get_settings
            settings = get_settings()
            
            # 构建模板文件路径
            template_path = settings.storage.workflows_dir / self.workflow_config.template_file
            template_path = template_path.resolve()
            
            self.logger.info(f"加载工作流模板: {template_path}")
            
            # 使用参数映射器加载模板
            workflow_json = ParameterMapper.load_workflow_template(template_path)
            
            self.logger.info(f"成功加载工作流模板 {self.workflow_config.template_file}，包含 {len(workflow_json)} 个节点")
            return workflow_json
            
        except Exception as e:
            self.logger.error(f"加载工作流模板失败: {e}")
            raise
    
    async def post_process(self, workflow_result: Dict[str, Any]) -> Dict[str, Any]:
        """后处理步骤：下载ComfyUI图片并保存到本地"""
        try:
            processed_result = {
                "output_images": [],
                "metadata": {
                    "workflow_id": self.workflow_config.id,
                    "workflow_name": self.workflow_config.name,
                    "workflow_config": {
                        "name": self.workflow_config.name,
                        "description": self.workflow_config.description,
                        "version": self.workflow_config.version
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
                            image_type = image_info.get("type", "output")
                            
                            # 跳过临时预览图片，只处理最终输出图片
                            if image_type == "temp":
                                self.logger.info(f"跳过临时预览图片: {comfyui_filename}")
                                continue
                            
                            if comfyui_filename:
                                # 获取期望的标准文件名
                                expected_filename = getattr(self, 'expected_output_filename', None)
                                if not expected_filename:
                                    import time
                                    expected_filename = f"{self.workflow_config.id}_output_{int(time.time())}.png"
                                
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
                                        "filepath": local_path,
                                        "original_comfyui_filename": comfyui_filename,
                                        "type": f"{self.workflow_config.id}_output"
                                    })
                                    self.logger.info(f"图片保存成功: {expected_filename}")
                                else:
                                    # 保存失败，使用原始ComfyUI URL作为备用
                                    fallback_url = f"{self.comfyui_service.client.base_url}/view?filename={comfyui_filename}&type=output"
                                    processed_result["output_images"].append({
                                        "filename": comfyui_filename,
                                        "url": fallback_url,
                                        "filepath": "",  # 空路径，表示下载失败
                                        "error": "Failed to download from ComfyUI",
                                        "type": f"{self.workflow_config.id}_output"
                                    })
                                    self.logger.warning(f"图片保存失败，使用备用URL: {comfyui_filename}")
            
            self.logger.info(f"{self.workflow_config.name} 后处理完成，保存了 {len(processed_result['output_images'])} 张图片")
            return processed_result
            
        except Exception as e:
            self.logger.error(f"后处理失败: {e}")
            # 返回原始结果，避免完全失败
            return workflow_result
    
    def get_estimated_time(self, parameters: Dict[str, Any]) -> int:
        """根据参数估算执行时间"""
        base_time = self.workflow_config.estimated_time
        
        # 考虑文件处理时间
        file_count = sum(1 for param_def in self.workflow_config.parameters.values() 
                        if param_def.type == "file")
        download_time = file_count * 8  # 每个文件8秒
        
        estimated_time = base_time + download_time
        return max(estimated_time, 30)  # 最少30秒
    
    def get_resource_requirements(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """获取资源需求"""
        return {
            "gpu_required": True,
            "estimated_memory_mb": 8192,   # 8GB内存
            "estimated_vram_mb": 12288,    # 12GB显存  
            "cpu_cores": 4,
            "disk_space_mb": 500,
            "network_required": True
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
            from app.config import get_settings
            settings = get_settings()
            return f"http://{settings.host}:{settings.port}"
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
        
        # 验证参数映射路径
        try:
            workflow_json = self._get_workflow_json()
            invalid_paths = ParameterMapper.validate_workflow_template(
                workflow_json, self.parameter_mappings
            )
            if invalid_paths:
                missing_requirements.extend([f"无效的参数映射: {path}" for path in invalid_paths])
        except Exception as e:
            missing_requirements.append(f"参数映射验证失败: {str(e)}")
        
        return missing_requirements