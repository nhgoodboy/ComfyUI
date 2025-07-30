"""
人物场景融合工作流

支持双图片输入的人物场景融合工作流，专门为person_scene_merge.json设计。
"""

import copy
import json  
import os
from typing import Dict, Any, List
import logging
from pathlib import Path

from ..base import BaseWorkflow, WorkflowMetadata, WorkflowParameter, WorkflowType
from ...services.comfyui_service import ComfyUIService

logger = logging.getLogger(__name__)

class PersonSceneMergeWorkflow(BaseWorkflow):
    """人物场景融合工作流
    
    专门处理双图片输入的人物场景融合任务。
    """
    
    def __init__(self, style_config: Dict[str, Any], comfyui_service: ComfyUIService):
        """初始化工作流
        
        Args:
            style_config: 风格配置字典
            comfyui_service: ComfyUI服务实例
        """
        self.style_config = style_config
        self.comfyui_service = comfyui_service
        super().__init__()
        
        # 缓存工作流JSON
        self._workflow_json_cache = None
        
        self.logger.info(f"初始化人物场景融合工作流: {style_config.get('name', 'Unknown')}")
    
    def get_metadata(self) -> WorkflowMetadata:
        """获取工作流元数据"""
        return WorkflowMetadata(
            id="person_scene_merge",
            name=self.style_config.get('name', '人物场景融合'),
            description=self.style_config.get('description', '将人物图片与场景图片融合'),
            version="1.0.0",
            workflow_type=WorkflowType.IMAGE_TO_IMAGE,
            author="ComfyUI工作流服务器",
            tags=self.style_config.get('tags', []),
            parameters=[
                WorkflowParameter(
                    name="image1_url",
                    type="string",
                    required=True,
                    description="第一张图像的URL地址（人物图片）"
                ),
                WorkflowParameter(
                    name="image2_url", 
                    type="string",
                    required=True,
                    description="第二张图像的URL地址（场景图片）"
                )
            ],
            input_types=["image", "image"],
            output_types=["image"],
            model_requirements=[],
            node_requirements=[],
            estimated_time=self.style_config.get('estimated_time', 60),
            gpu_required=True
        )
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """验证和处理参数"""
        validated_params = {}
        
        # 验证第一张图片参数
        image1_url = parameters.get("image1_url")
        image1_path = parameters.get("image1_path")
        
        if image1_url:
            if not isinstance(image1_url, str) or not image1_url.strip():
                raise ValueError("参数 'image1_url' 必须是有效的URL字符串")
            validated_params["image1_url"] = image1_url.strip()
        elif image1_path:
            if not isinstance(image1_path, str) or not image1_path.strip():
                raise ValueError("参数 'image1_path' 必须是有效的文件路径")
            validated_params["image1_path"] = image1_path.strip()
        else:
            raise ValueError("必须提供 'image1_url' 或 'image1_path' 参数")
        
        # 验证第二张图片参数
        image2_url = parameters.get("image2_url")
        image2_path = parameters.get("image2_path")
        
        if image2_url:
            if not isinstance(image2_url, str) or not image2_url.strip():
                raise ValueError("参数 'image2_url' 必须是有效的URL字符串")
            validated_params["image2_url"] = image2_url.strip()
        elif image2_path:
            if not isinstance(image2_path, str) or not image2_path.strip():
                raise ValueError("参数 'image2_path' 必须是有效的文件路径")
            validated_params["image2_path"] = image2_path.strip()
        else:
            raise ValueError("必须提供 'image2_url' 或 'image2_path' 参数")
        
        # 添加输出文件名支持
        if "output_filename" in parameters:
            validated_params["output_filename"] = parameters["output_filename"]
        
        return validated_params
    
    async def pre_process(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """预处理步骤：上传图片到ComfyUI"""
        processed_params = parameters.copy()
        
        # 处理第一张图片
        if "image1_path" in parameters:
            image1_path = parameters["image1_path"]
            self.logger.info(f"开始上传第一张图片到ComfyUI: {image1_path}")
            
            # 读取图片文件
            try:
                with open(image1_path, 'rb') as f:
                    image1_data = f.read()
                
                # 上传到ComfyUI
                image1_filename = Path(image1_path).name
                uploaded_filename1 = await self.comfyui_service.upload_image(image1_data, image1_filename)
                processed_params["image1_filename"] = uploaded_filename1
                self.logger.info(f"第一张图片上传完成: {uploaded_filename1}")
                
            except Exception as e:
                self.logger.error(f"第一张图片上传失败: {e}")
                raise RuntimeError(f"图片1上传失败: {str(e)}")
        
        # 处理第二张图片
        if "image2_path" in parameters:
            image2_path = parameters["image2_path"]
            self.logger.info(f"开始上传第二张图片到ComfyUI: {image2_path}")
            
            # 读取图片文件
            try:
                with open(image2_path, 'rb') as f:
                    image2_data = f.read()
                
                # 上传到ComfyUI
                image2_filename = Path(image2_path).name
                uploaded_filename2 = await self.comfyui_service.upload_image(image2_data, image2_filename)
                processed_params["image2_filename"] = uploaded_filename2
                self.logger.info(f"第二张图片上传完成: {uploaded_filename2}")
                
            except Exception as e:
                self.logger.error(f"第二张图片上传失败: {e}")
                raise RuntimeError(f"图片2上传失败: {str(e)}")
        
        return processed_params
    
    def _load_workflow_json(self) -> Dict[str, Any]:
        """加载工作流JSON文件"""
        if self._workflow_json_cache is not None:
            return self._workflow_json_cache
        
        # 获取工作流文件路径
        workflow_file = self.style_config.get('workflow_file', 'person_scene_merge.json')
        
        # 构建完整路径（相对于项目根目录的workflows目录）
        current_dir = Path(__file__).parent.parent.parent.parent
        workflow_path = current_dir / "workflows" / workflow_file
        
        if not workflow_path.exists():
            raise FileNotFoundError(f"工作流文件不存在: {workflow_path}")
        
        try:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                workflow_json = json.load(f)
            
            self._workflow_json_cache = workflow_json
            self.logger.info(f"成功加载工作流文件: {workflow_path}")
            return workflow_json
            
        except json.JSONDecodeError as e:
            raise ValueError(f"工作流文件JSON格式错误: {e}")
        except Exception as e:
            raise RuntimeError(f"加载工作流文件失败: {e}")
    
    async def build_workflow(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """构建ComfyUI工作流JSON"""
        # 加载基础工作流JSON
        workflow_json = copy.deepcopy(self._load_workflow_json())
        
        # 使用上传后的文件名设置工作流
        if "image1_filename" in parameters and "image2_filename" in parameters:
            image1_filename = parameters["image1_filename"]
            image2_filename = parameters["image2_filename"]
            
            # 修改工作流中的图片文件名
            if "30" in workflow_json and "inputs" in workflow_json["30"]:
                workflow_json["30"]["inputs"]["image"] = image1_filename
                
            if "31" in workflow_json and "inputs" in workflow_json["31"]:
                workflow_json["31"]["inputs"]["image"] = image2_filename
                
            self.logger.info(f"工作流配置完成: image1={image1_filename}, image2={image2_filename}")
        
        elif "image1_path" in parameters and "image2_path" in parameters:
            # 兼容本地路径方式（主要用于测试）
            image1_filename = Path(parameters["image1_path"]).name
            image2_filename = Path(parameters["image2_path"]).name
            
            # 修改工作流中的图片文件名
            if "30" in workflow_json and "inputs" in workflow_json["30"]:
                workflow_json["30"]["inputs"]["image"] = image1_filename
                
            if "31" in workflow_json and "inputs" in workflow_json["31"]:
                workflow_json["31"]["inputs"]["image"] = image2_filename
                
            self.logger.info(f"工作流配置完成（本地路径）: image1={image1_filename}, image2={image2_filename}")
        
        elif "image1_url" in parameters and "image2_url" in parameters:
            # 使用URL方式（需要先下载）
            # 这种情况下，下载服务会处理文件并设置正确的文件名
            # 工作流在执行时会被进一步修改
            pass
        
        return workflow_json
    
    async def post_process(self, workflow_result: Dict[str, Any]) -> Dict[str, Any]:
        """后处理工作流结果"""
        self.logger.info(f"开始后处理工作流结果: {workflow_result.get('status', 'unknown')}")
        
        if workflow_result.get('status') != 'completed':
            self.logger.warning(f"工作流未完成，状态: {workflow_result.get('status')}")
            return workflow_result
        
        try:
            # 获取历史记录
            history = workflow_result.get('history', {})
            if not history:
                self.logger.warning("工作流结果中没有历史记录")
                return workflow_result
            
            # 查找输出图片（通常在SaveImage节点中）
            output_images = []
            
            # 检查历史记录结构
            if 'outputs' in history:
                # 直接访问outputs节点
                outputs = history['outputs']
                for node_id, node_output in outputs.items():
                    if 'images' in node_output:
                        for image_info in node_output['images']:
                            # 构建图片信息
                            output_image = {
                                'filename': image_info.get('filename', ''),
                                'subfolder': image_info.get('subfolder', ''),
                                'type': image_info.get('type', 'output'),
                                'node_id': node_id
                            }
                            
                            # 构建完整URL
                            if output_image['filename']:
                                base_url = self.comfyui_service.base_url.rstrip('/')
                                if output_image['subfolder']:
                                    output_image['url'] = f"{base_url}/view?filename={output_image['filename']}&subfolder={output_image['subfolder']}&type={output_image['type']}"
                                else:
                                    output_image['url'] = f"{base_url}/view?filename={output_image['filename']}&type={output_image['type']}"
                                
                                self.logger.info(f"找到输出图片: {output_image['filename']} (节点 {node_id})")
                                output_images.append(output_image)
            else:
                # 兼容旧格式：按prompt_id遍历
                for prompt_id, prompt_data in history.items():
                    if 'outputs' in prompt_data:
                        for node_id, node_output in prompt_data['outputs'].items():
                            if 'images' in node_output:
                                for image_info in node_output['images']:
                                    # 构建图片信息
                                    output_image = {
                                        'filename': image_info.get('filename', ''),
                                        'subfolder': image_info.get('subfolder', ''),
                                        'type': image_info.get('type', 'output'),
                                        'node_id': node_id
                                    }
                                    
                                    # 构建完整URL
                                    if output_image['filename']:
                                        base_url = self.comfyui_service.base_url.rstrip('/')
                                        if output_image['subfolder']:
                                            output_image['url'] = f"{base_url}/view?filename={output_image['filename']}&subfolder={output_image['subfolder']}&type={output_image['type']}"
                                        else:
                                            output_image['url'] = f"{base_url}/view?filename={output_image['filename']}&type={output_image['type']}"
                                        
                                        self.logger.info(f"找到输出图片: {output_image['filename']} (节点 {node_id})")
                                        output_images.append(output_image)
            
            # 构建处理后的结果
            processed_result = {
                'status': 'completed',
                'output_images': output_images,
                'files': {
                    'output': [img['url'] for img in output_images if 'url' in img]
                },
                'metadata': {
                    'workflow_type': 'person_scene_merge',
                    'total_images': len(output_images),
                    'prompt_id': workflow_result.get('prompt_id')
                }
            }
            
            self.logger.info(f"后处理完成，生成了 {len(output_images)} 个输出图片")
            return processed_result
            
        except Exception as e:
            self.logger.error(f"后处理失败: {e}", exc_info=True)
            # 返回原始结果，不要让后处理错误影响整个任务
            return {
                'status': 'completed',
                'output_images': [],
                'error': f"后处理失败: {str(e)}",
                'raw_result': workflow_result
            }