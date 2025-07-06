"""
风格变换工作流

基于现有的风格变换逻辑实现的新架构工作流。
"""

import copy
from typing import Dict, Any, List
import logging

from ..base import BaseWorkflow, WorkflowMetadata, WorkflowParameter, WorkflowType
from ..base.parameter_types import ParameterValidator

logger = logging.getLogger(__name__)

class StyleTransformWorkflow(BaseWorkflow):
    """风格变换工作流
    
    将输入图像转换为指定风格的图像。
    """
    
    def get_metadata(self) -> WorkflowMetadata:
        """获取工作流元数据"""
        return WorkflowMetadata(
            id="style_transform",
            name="风格变换",
            description="将输入图像转换为指定风格的图像，支持多种艺术风格",
            version="1.0.0",
            workflow_type=WorkflowType.IMAGE_TO_IMAGE,
            author="ComfyUI工作流服务器",
            tags=["图像处理", "风格转换", "艺术风格", "AI绘画"],
            parameters=[
                WorkflowParameter(
                    name="image",
                    type="image",
                    required=True,
                    description="输入图像文件路径"
                ),
                WorkflowParameter(
                    name="style_prompt",
                    type="string",
                    required=True,
                    description="风格描述提示词",
                    min_length=1,
                    max_length=500
                ),
                WorkflowParameter(
                    name="negative_prompt",
                    type="string",
                    required=False,
                    default="bad quality, blurry, low resolution",
                    description="负面提示词，描述不想要的效果",
                    max_length=500
                ),
                WorkflowParameter(
                    name="strength",
                    type="number",
                    required=False,
                    default=0.6,
                    description="变换强度，范围0-1，数值越高变换越强烈",
                    min_value=0.0,
                    max_value=1.0
                ),
                WorkflowParameter(
                    name="steps",
                    type="integer",
                    required=False,
                    default=20,
                    description="生成步数，步数越多质量越高但耗时越长",
                    min_value=1,
                    max_value=100
                ),
                WorkflowParameter(
                    name="cfg_scale",
                    type="number",
                    required=False,
                    default=7.0,
                    description="CFG scale，控制生成图像与提示词的一致性",
                    min_value=1.0,
                    max_value=20.0
                ),
                WorkflowParameter(
                    name="seed",
                    type="integer",
                    required=False,
                    default=-1,
                    description="随机种子，-1表示随机生成",
                    min_value=-1,
                    max_value=2147483647
                ),
                WorkflowParameter(
                    name="sampler_name",
                    type="enum",
                    required=False,
                    default="euler",
                    description="采样器类型",
                    enum_values=["euler", "euler_ancestral", "dpm_2", "dpm_2_ancestral", "dpm_pp_2s_ancestral", "dpm_pp_2m", "dpm_pp_sde", "dpm_fast", "dpm_adaptive", "heun", "lms", "ddim", "ddpm", "dpm_solver", "uni_pc"]
                ),
                WorkflowParameter(
                    name="scheduler",
                    type="enum",
                    required=False,
                    default="normal",
                    description="调度器类型",
                    enum_values=["normal", "karras", "exponential", "sgm_uniform", "simple", "ddim_uniform"]
                ),
                WorkflowParameter(
                    name="checkpoint",
                    type="enum",
                    required=False,
                    default="sd_xl_base_1.0.safetensors",
                    description="使用的检查点模型",
                    enum_values=["sd_xl_base_1.0.safetensors", "sd_xl_refiner_1.0.safetensors", "sd_xl_turbo_1.0.safetensors"]
                )
            ],
            input_types=["image"],
            output_types=["image"],
            model_requirements=["sd_xl_base_1.0.safetensors"],
            node_requirements=["LoadImage", "CLIPTextEncode", "CheckpointLoaderSimple", "KSampler", "VAEEncode", "VAEDecode", "SaveImage"],
            estimated_time=30,
            gpu_required=True
        )
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """验证和处理参数"""
        validated_params = {}
        
        # 验证每个参数
        for param in self.metadata.parameters:
            param_name = param.name
            value = parameters.get(param_name)
            
            try:
                # 验证图像文件
                if param.type == "image":
                    if not value:
                        if param.required:
                            raise ValueError(f"参数 '{param_name}' 是必需的")
                        validated_params[param_name] = param.default
                    else:
                        validated_params[param_name] = ParameterValidator.validate_image_file(value)
                        
                # 验证字符串
                elif param.type == "string":
                    validated_params[param_name] = ParameterValidator.validate_string(
                        value if value is not None else param.default,
                        min_length=param.min_length,
                        max_length=param.max_length
                    )
                    
                # 验证数值
                elif param.type == "number":
                    validated_params[param_name] = ParameterValidator.validate_number(
                        value if value is not None else param.default,
                        min_value=param.min_value,
                        max_value=param.max_value
                    )
                    
                # 验证整数
                elif param.type == "integer":
                    validated_params[param_name] = ParameterValidator.validate_integer(
                        value if value is not None else param.default,
                        min_value=param.min_value,
                        max_value=param.max_value
                    )
                    
                # 验证枚举
                elif param.type == "enum":
                    validated_params[param_name] = ParameterValidator.validate_enum(
                        value if value is not None else param.default,
                        enum_values=param.enum_values
                    )
                    
                else:
                    # 其他类型直接使用默认值或提供的值
                    validated_params[param_name] = value if value is not None else param.default
                    
            except Exception as e:
                raise ValueError(f"参数 '{param_name}' 验证失败: {str(e)}")
        
        return validated_params
    
    async def build_workflow(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """构建ComfyUI工作流JSON"""
        # 获取基础模板
        template = self._get_workflow_template()
        
        # 自定义模板参数
        workflow = copy.deepcopy(template)
        
        # 设置输入图像
        if "1" in workflow and workflow["1"]["class_type"] == "LoadImage":
            workflow["1"]["inputs"]["image"] = parameters["image"]
        
        # 设置正面提示词
        if "2" in workflow and workflow["2"]["class_type"] == "CLIPTextEncode":
            workflow["2"]["inputs"]["text"] = parameters["style_prompt"]
        
        # 设置负面提示词
        if "3" in workflow and workflow["3"]["class_type"] == "CLIPTextEncode":
            workflow["3"]["inputs"]["text"] = parameters["negative_prompt"]
        
        # 设置检查点模型
        if "4" in workflow and workflow["4"]["class_type"] == "CheckpointLoaderSimple":
            workflow["4"]["inputs"]["ckpt_name"] = parameters["checkpoint"]
        
        # 设置采样器参数
        if "5" in workflow and workflow["5"]["class_type"] == "KSampler":
            sampler_inputs = workflow["5"]["inputs"]
            sampler_inputs["seed"] = parameters["seed"] if parameters["seed"] != -1 else self._generate_random_seed()
            sampler_inputs["steps"] = parameters["steps"]
            sampler_inputs["cfg"] = parameters["cfg_scale"]
            sampler_inputs["sampler_name"] = parameters["sampler_name"]
            sampler_inputs["scheduler"] = parameters["scheduler"]
            sampler_inputs["denoise"] = parameters["strength"]
        
        return workflow
    
    def _get_workflow_template(self) -> Dict[str, Any]:
        """获取工作流模板"""
        return {
            "1": {
                "class_type": "LoadImage",
                "inputs": {
                    "image": "input_image.jpg"
                }
            },
            "2": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "Clay Style, lovely, 3d, cute",
                    "clip": ["4", 1]
                }
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "bad quality, blurry, low resolution",
                    "clip": ["4", 1]
                }
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "sd_xl_base_1.0.safetensors"
                }
            },
            "5": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": 42,
                    "steps": 20,
                    "cfg": 7.0,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 0.6,
                    "model": ["4", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["6", 0]
                }
            },
            "6": {
                "class_type": "VAEEncode",
                "inputs": {
                    "pixels": ["1", 0],
                    "vae": ["4", 2]
                }
            },
            "7": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["5", 0],
                    "vae": ["4", 2]
                }
            },
            "8": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "style_transform",
                    "images": ["7", 0]
                }
            }
        }
    
    def _generate_random_seed(self) -> int:
        """生成随机种子"""
        import random
        return random.randint(0, 2147483647)
    
    def get_estimated_time(self, parameters: Dict[str, Any]) -> int:
        """根据参数估算执行时间"""
        base_time = 30  # 基础时间30秒
        
        # 根据步数调整时间
        steps = parameters.get("steps", 20)
        time_multiplier = steps / 20  # 20步为基准
        
        # 根据强度调整时间
        strength = parameters.get("strength", 0.6)
        strength_multiplier = 0.5 + (strength * 0.5)  # 强度越高耗时越长
        
        estimated_time = int(base_time * time_multiplier * strength_multiplier)
        return max(estimated_time, 15)  # 最少15秒
    
    def get_resource_requirements(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """获取资源需求"""
        return {
            "gpu_required": True,
            "estimated_memory_mb": 4096,  # 4GB内存
            "estimated_vram_mb": 8192,    # 8GB显存
            "cpu_cores": 2
        }
    
    def validate_requirements(self) -> List[str]:
        """验证工作流运行要求"""
        missing_requirements = []
        
        # 这里可以添加具体的验证逻辑
        # 比如检查模型文件是否存在、ComfyUI节点是否可用等
        # 目前返回空列表表示所有要求都满足
        
        return missing_requirements 