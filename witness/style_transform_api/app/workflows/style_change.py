"""
风格变换工作流模板
这个文件提供了一个基础的工作流模板，可以根据实际的style_change.json进行调整
"""

def get_style_change_workflow_template():
    """
    获取风格变换工作流模板
    
    注意：这是一个示例模板，需要根据实际的style_change.json文件进行调整
    """
    return {
        "1": {
            "class_type": "LoadImage",
            "inputs": {
                "image": "input_image.jpg"  # 这里会被动态替换
            }
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "Clay Style, lovely, 3d, cute",  # 这里会被动态替换
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
                "denoise": 0.6,  # 这里会被动态替换为strength参数
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

def customize_workflow_template(template, input_image, style_prompt, strength=0.6):
    """
    自定义工作流模板参数
    
    Args:
        template: 工作流模板
        input_image: 输入图像名称
        style_prompt: 风格提示词
        strength: 变换强度
    
    Returns:
        自定义后的工作流
    """
    import copy
    
    # 深拷贝模板避免修改原始模板
    workflow = copy.deepcopy(template)
    
    # 更新输入图像
    if "1" in workflow and workflow["1"]["class_type"] == "LoadImage":
        workflow["1"]["inputs"]["image"] = input_image
    
    # 更新风格提示词
    if "2" in workflow and workflow["2"]["class_type"] == "CLIPTextEncode":
        workflow["2"]["inputs"]["text"] = style_prompt
    
    # 更新变换强度
    if "5" in workflow and workflow["5"]["class_type"] == "KSampler":
        workflow["5"]["inputs"]["denoise"] = strength
    
    return workflow 