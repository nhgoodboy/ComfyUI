"""
动漫风格转换工作流

专门用于将图片转换为动漫风格的工作流。
"""

import copy
from typing import Dict, Any, List
import logging

from ..base import BaseWorkflow, WorkflowMetadata, WorkflowParameter, WorkflowType
from ..base.parameter_types import ParameterValidator

logger = logging.getLogger(__name__)

class AnimeStyleTransformWorkflow(BaseWorkflow):
    """动漫风格转换工作流
    
    将输入图像转换为动漫风格的图像。
    """
    
    def get_metadata(self) -> WorkflowMetadata:
        """获取工作流元数据"""
        return WorkflowMetadata(
            id="anime_style_transform",
            name="动漫风格转换",
            description="将输入图像转换为动漫风格的图像，使用Flux模型和ControlNet技术，呈现鲜艳色彩和漫画风格",
            version="1.0.0",
            workflow_type=WorkflowType.IMAGE_TO_IMAGE,
            author="ComfyUI工作流服务器",
            tags=["图像处理", "动漫风格", "风格转换", "AI绘画", "Flux模型", "漫画", "动画"],
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
            model_requirements=[
                "flux1-dev.safetensors",
                "clip_l.safetensors", 
                "t5xxl_fp8_e4m3fn.safetensors",
                "ae.sft",
                "flux-lora-000005 (1).safetensors",
                "FLUX.1-dev-ControlNet-Union-Pro-2.0.safetensors"
            ],
            node_requirements=[
                "LoadImage", "CLIPTextEncodeFlux", "UNETLoader", "DualCLIPLoader", 
                "VAELoader", "VAEEncode", "VAEDecode", "KSampler", "SaveImage",
                "LoraLoaderModelOnly", "ControlNetLoader", "ControlNetApplyAdvanced",
                "ModelSamplingFlux", "easy positive", "SetUnionControlNetType",
                "ImageScaleToTotalPixels", "LineArtPreprocessor", "easy imageSize",
                "LayerUtility: Florence2Image2Prompt", "JoinStrings", 
                "LayerMask: LoadFlorence2Model", "PreviewImage", "easy showAnything"
            ],
            estimated_time=45,
            gpu_required=True
        )
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """验证和处理参数"""
        validated_params = {}
        
        # 验证图像URL参数
        image_url = parameters.get("image_url")
        if not image_url:
            raise ValueError("参数 'image_url' 是必需的")
        
        # 简单的URL格式验证
        if not isinstance(image_url, str) or not image_url.strip():
            raise ValueError("参数 'image_url' 必须是有效的URL字符串")
        
        # 检查URL格式
        if not (image_url.startswith('http://') or image_url.startswith('https://')):
            raise ValueError("参数 'image_url' 必须以 http:// 或 https:// 开头")
        
        validated_params["image_url"] = image_url.strip()
        
        self.logger.info(f"动漫风格转换参数验证完成: image_url={image_url}")
        return validated_params
    
    async def pre_process(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """预处理步骤：下载图片并上传到ComfyUI"""
        from ...services.comfyui_service import get_comfyui_service
        
        try:
            image_url = parameters["image_url"]
            self.logger.info(f"开始下载图片: {image_url}")
            
            # 获取ComfyUI服务实例
            service = get_comfyui_service()
            
            # 下载图片
            image_data = await service.download_image(image_url)
            self.logger.info(f"图片下载完成，大小: {len(image_data)} bytes")
            
            # 上传到ComfyUI
            filename = await service.upload_image(image_data, "anime_input.jpg")
            self.logger.info(f"图片上传完成，文件名: {filename}")
            
            # 更新参数
            processed_params = parameters.copy()
            processed_params["image_filename"] = filename
            
            return processed_params
            
        except Exception as e:
            self.logger.error(f"图片预处理失败: {e}")
            raise ValueError(f"图片处理失败: {str(e)}")
    
    async def build_workflow(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """构建ComfyUI工作流JSON"""
        # 获取基础模板
        template = self._get_workflow_template()
        
        # 复制模板
        workflow = copy.deepcopy(template)
        
        # 设置输入图像 (节点1: LoadImage)
        if "1" in workflow and workflow["1"].get("class_type") == "LoadImage":
            image_filename = parameters.get("image_filename", "anime_input.jpg")
            workflow["1"]["inputs"]["image"] = image_filename
            self.logger.debug(f"设置输入图像: {image_filename}")
        
        # 确保输出文件名前缀 (节点35: SaveImage)
        if "35" in workflow and workflow["35"].get("class_type") == "SaveImage":
            workflow["35"]["inputs"]["filename_prefix"] = "anime_style"
            self.logger.debug("设置输出文件前缀: anime_style")
        
        self.logger.info(f"动漫风格工作流构建完成，包含 {len(workflow)} 个节点")
        return workflow
    
    def _get_workflow_template(self) -> Dict[str, Any]:
        """从JSON文件读取工作流模板"""
        import json
        import os
        
        try:
            # 获取JSON模板文件路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            template_path = os.path.join(
                current_dir, 
                "../../../workflows/anime_style_transform.json"
            )
            
            # 规范化路径
            template_path = os.path.normpath(template_path)
            
            self.logger.info(f"加载动漫风格工作流模板: {template_path}")
            
            # 读取JSON文件
            with open(template_path, 'r', encoding='utf-8') as f:
                template = json.load(f)
            
            self.logger.info(f"成功加载动漫风格工作流模板，包含 {len(template)} 个节点")
            return template
            
        except FileNotFoundError:
            self.logger.error(f"动漫风格工作流模板文件未找到: {template_path}")
            raise FileNotFoundError(f"动漫风格工作流模板文件不存在: {template_path}")
        except json.JSONDecodeError as e:
            self.logger.error(f"动漫风格工作流模板JSON解析失败: {e}")
            raise ValueError(f"动漫风格工作流模板JSON格式错误: {e}")
        except Exception as e:
            self.logger.error(f"加载动漫风格工作流模板时发生错误: {e}")
            raise RuntimeError(f"加载动漫风格工作流模板失败: {e}")
    
    async def post_process(self, workflow_result: Dict[str, Any]) -> Dict[str, Any]:
        """后处理步骤：处理结果并生成访问URL"""
        from ...services.comfyui_service import get_comfyui_service
        
        try:
            processed_result = {
                "output_images": [],
                "metadata": {
                    "style": "anime",
                    "workflow_type": "anime_style_transform"
                }
            }
            
            # 获取ComfyUI服务实例
            service = get_comfyui_service()
            
            # 处理输出图片
            if "images" in workflow_result:
                for image_info in workflow_result["images"]:
                    filename = image_info.get("filename", "")
                    if filename:
                        # 生成访问URL
                        image_url = f"{service.client.base_url}/view?filename={filename}&type=output"
                        processed_result["output_images"].append({
                            "filename": filename,
                            "url": image_url,
                            "type": "anime_style_image"
                        })
                        self.logger.debug(f"处理输出图片: {filename}")
            
            self.logger.info(f"动漫风格转换后处理完成，生成 {len(processed_result['output_images'])} 张图片")
            return processed_result
            
        except Exception as e:
            self.logger.error(f"动漫风格转换后处理失败: {e}")
            # 返回原始结果，避免完全失败
            return workflow_result
    
    def get_estimated_time(self, parameters: Dict[str, Any]) -> int:
        """根据参数估算执行时间"""
        # 动漫风格转换时间与黏土风格类似
        base_time = 45  # Flux模型基础时间45秒
        
        # 考虑图片下载时间（5-10秒）
        download_time = 8
        
        # 总执行时间
        estimated_time = base_time + download_time
        return max(estimated_time, 30)  # 最少30秒
    
    def get_resource_requirements(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """获取资源需求"""
        return {
            "gpu_required": True,
            "estimated_memory_mb": 8192,   # 8GB内存 (Flux模型需要更多内存)
            "estimated_vram_mb": 12288,    # 12GB显存 (Flux模型需要更多显存)
            "cpu_cores": 4,
            "disk_space_mb": 500,  # 图片下载和处理需要的磁盘空间
            "network_required": True  # 需要网络下载图片
        }
    
    def validate_requirements(self) -> List[str]:
        """验证工作流运行要求"""
        missing_requirements = []
        
        # 这里可以添加具体的验证逻辑
        # 比如检查模型文件是否存在、ComfyUI节点是否可用等
        # 目前返回空列表表示所有要求都满足
        
        return missing_requirements 