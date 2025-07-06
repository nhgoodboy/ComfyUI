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
                    name="lora_strength",
                    type="number",
                    required=False,
                    default=1.0,
                    description="LoRA模型强度，影响风格转换的程度",
                    min_value=0.0,
                    max_value=2.0
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
                "ModelSamplingFlux", "easy positive", "SetUnionControlNetType"
            ],
            estimated_time=45,
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
                        min_value=int(param.min_value) if param.min_value is not None else None,
                        max_value=int(param.max_value) if param.max_value is not None else None
                    )
                    
                # 验证枚举
                elif param.type == "enum":
                    validated_params[param_name] = ParameterValidator.validate_enum(
                        value if value is not None else param.default,
                        enum_values=param.enum_values or []
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
        
        # 设置输入图像 (节点1: LoadImage)
        if "1" in workflow and workflow["1"].get("class_type") == "LoadImage":
            workflow["1"]["inputs"]["image"] = parameters["image"]
            self.logger.debug(f"设置输入图像: {parameters['image']}")
        
        # 设置正面提示词 (节点79: easy positive)
        if "79" in workflow and workflow["79"].get("class_type") == "easy positive":
            # 构建完整的正面提示词，包含风格前缀
            full_prompt = f"Clay Style, lovely, 3d, cute, {parameters['style_prompt']}"
            workflow["79"]["inputs"]["positive"] = full_prompt
            self.logger.debug(f"设置正面提示词: {full_prompt}")
        
        # 设置采样器参数 (节点73: KSampler)
        if "73" in workflow and workflow["73"].get("class_type") == "KSampler":
            sampler_inputs = workflow["73"]["inputs"]
            sampler_inputs["seed"] = parameters["seed"] if parameters["seed"] != -1 else self._generate_random_seed()
            sampler_inputs["steps"] = parameters["steps"]
            sampler_inputs["cfg"] = parameters["cfg_scale"]
            sampler_inputs["sampler_name"] = parameters["sampler_name"]
            sampler_inputs["scheduler"] = parameters["scheduler"]
            sampler_inputs["denoise"] = parameters["strength"]
            self.logger.debug(f"设置采样器参数: steps={parameters['steps']}, cfg={parameters['cfg_scale']}, denoise={parameters['strength']}")
        
        # 设置输出文件名 (节点35: SaveImage)
        if "35" in workflow and workflow["35"].get("class_type") == "SaveImage":
            workflow["35"]["inputs"]["filename_prefix"] = "style_transform"
            self.logger.debug("设置输出文件前缀: style_transform")
        
        # 设置LoRA强度 (节点90: LoraLoaderModelOnly) - 如果存在
        if "90" in workflow and workflow["90"].get("class_type") == "LoraLoaderModelOnly":
            # 使用lora_strength参数，如果没有则使用strength参数的映射
            lora_strength = parameters.get("lora_strength", parameters["strength"] * 2.0)
            lora_strength = min(lora_strength, 2.0)  # 最大2.0
            workflow["90"]["inputs"]["strength_model"] = lora_strength
            self.logger.debug(f"设置LoRA强度: {lora_strength}")
        
        self.logger.info(f"工作流构建完成，包含 {len(workflow)} 个节点")
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
                "../../../workflows/style_change.json"
            )
            
            # 规范化路径
            template_path = os.path.normpath(template_path)
            
            self.logger.info(f"加载工作流模板: {template_path}")
            
            # 读取JSON文件
            with open(template_path, 'r', encoding='utf-8') as f:
                template = json.load(f)
            
            self.logger.info(f"成功加载工作流模板，包含 {len(template)} 个节点")
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
    
    def _generate_random_seed(self) -> int:
        """生成随机种子"""
        import random
        return random.randint(0, 2147483647)
    
    def get_estimated_time(self, parameters: Dict[str, Any]) -> int:
        """根据参数估算执行时间"""
        base_time = 45  # Flux模型基础时间45秒
        
        # 根据步数调整时间
        steps = parameters.get("steps", 20)
        time_multiplier = steps / 20  # 20步为基准
        
        # 根据强度调整时间
        strength = parameters.get("strength", 0.6)
        strength_multiplier = 0.7 + (strength * 0.3)  # 强度越高耗时越长
        
        # LoRA强度也会影响时间
        lora_strength = parameters.get("lora_strength", 1.0)
        lora_multiplier = 0.9 + (lora_strength * 0.1)  # LoRA强度影响较小
        
        estimated_time = int(base_time * time_multiplier * strength_multiplier * lora_multiplier)
        return max(estimated_time, 25)  # 最少25秒
    
    def get_resource_requirements(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """获取资源需求"""
        return {
            "gpu_required": True,
            "estimated_memory_mb": 8192,   # 8GB内存 (Flux模型需要更多内存)
            "estimated_vram_mb": 12288,    # 12GB显存 (Flux模型需要更多显存)
            "cpu_cores": 4
        }
    
    def validate_requirements(self) -> List[str]:
        """验证工作流运行要求"""
        missing_requirements = []
        
        # 这里可以添加具体的验证逻辑
        # 比如检查模型文件是否存在、ComfyUI节点是否可用等
        # 目前返回空列表表示所有要求都满足
        
        return missing_requirements 