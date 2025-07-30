#!/usr/bin/env python3
"""
双图片工作流功能测试脚本

测试person_scene_merge工作流的核心功能
"""

import sys
import os

# 添加正确的路径
sys.path.insert(0, '/mnt/d/workspace/ComfyUI/witness/comfyui_workflow_server')
os.chdir('/mnt/d/workspace/ComfyUI/witness/comfyui_workflow_server')

from app.core.style_registry import StyleRegistry
from app.services.comfyui_service import ComfyUIService

def test_style_registry():
    """测试样式注册表"""
    print("=== 测试样式注册表 ===")
    
    # 创建假的ComfyUI服务（仅用于测试）
    class MockComfyUIService:
        base_url = "http://localhost:8188"
    
    comfyui_service = MockComfyUIService()
    
    # 创建样式注册表
    config_file = "/mnt/d/workspace/ComfyUI/witness/comfyui_workflow_server/configs/style_configs.yaml"
    registry = StyleRegistry(config_file, comfyui_service)
    
    # 检查样式加载
    print(f"加载的样式数量: {len(registry.styles)}")
    for style_id, style_info in registry.styles.items():
        print(f"- {style_id}: {style_info.name} (双图片: {style_info.requires_dual_images})")
    
    # 测试person_scene_merge
    if 'person_scene_merge' in registry.styles:
        style = registry.get_style('person_scene_merge')
        print(f"\nperson_scene_merge详情:")
        print(f"  名称: {style.name}")
        print(f"  描述: {style.description}")
        print(f"  需要双图片: {style.requires_dual_images}")
        print(f"  图片数量: {style.image_count}")
        print(f"  预估时间: {style.estimated_time}秒")
        
        # 测试工作流实例
        workflow = registry.get_workflow('person_scene_merge')
        if workflow:
            print(f"  工作流类型: {type(workflow).__name__}")
            print(f"  工作流ID: {workflow.metadata.id}")
        else:
            print("  错误: 工作流实例未创建")
    else:
        print("错误: person_scene_merge样式未加载")
    
    return True

def test_workflow_parameters():
    """测试工作流参数验证"""
    print("\n=== 测试工作流参数验证 ===")
    
    try:
        from app.workflows.built_in.person_scene_merge_workflow import PersonSceneMergeWorkflow
        
        # 创建假的ComfyUI服务
        class MockComfyUIService:
            base_url = "http://localhost:8188"
        
        comfyui_service = MockComfyUIService()
        
        # 创建工作流实例
        style_config = {
            'name': '人物场景融合',
            'description': '测试用配置',
            'estimated_time': 60,
            'tags': ['测试']
        }
        
        workflow = PersonSceneMergeWorkflow(style_config, comfyui_service)
        
        # 测试参数验证
        print("测试有效参数...")
        valid_params = {
            'image1_path': '/path/to/image1.jpg',
            'image2_path': '/path/to/image2.jpg'
        }
        
        validated = workflow.validate_parameters(valid_params)
        print(f"验证成功: {validated}")
        
        # 测试无效参数
        print("测试无效参数...")
        try:
            invalid_params = {
                'image1_path': '/path/to/image1.jpg'
                # 缺少image2_path
            }
            workflow.validate_parameters(invalid_params)
            print("错误: 应该抛出异常")
        except ValueError as e:
            print(f"正确捕获异常: {e}")
        
        return True
        
    except Exception as e:
        print(f"测试失败: {e}")
        return False

def test_workflow_json_loading():
    """测试工作流JSON加载"""
    print("\n=== 测试工作流JSON加载 ===")
    
    try:
        from app.workflows.built_in.person_scene_merge_workflow import PersonSceneMergeWorkflow
        
        # 创建假的ComfyUI服务
        class MockComfyUIService:
            base_url = "http://localhost:8188"
        
        comfyui_service = MockComfyUIService()
        
        # 创建工作流实例
        style_config = {
            'name': '人物场景融合',
            'description': '测试用配置',
            'workflow_file': 'person_scene_merge.json',
            'estimated_time': 60,
            'tags': ['测试']
        }
        
        workflow = PersonSceneMergeWorkflow(style_config, comfyui_service)
        
        # 尝试加载工作流JSON
        workflow_json = workflow._load_workflow_json()
        
        print(f"工作流JSON加载成功")
        print(f"节点数量: {len(workflow_json)}")
        
        # 检查关键节点
        if '30' in workflow_json:
            print(f"节点30 (第一张图片): {workflow_json['30'].get('class_type', 'Unknown')}")
        if '31' in workflow_json:
            print(f"节点31 (第二张图片): {workflow_json['31'].get('class_type', 'Unknown')}")
        
        return True
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("双图片工作流功能测试")
    print("=" * 50)
    
    tests = [
        test_style_registry,
        test_workflow_parameters,
        test_workflow_json_loading
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"测试 {test.__name__} 出现异常: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print(f"\n=== 测试结果 ===")
    for i, result in enumerate(results):
        status = "通过" if result else "失败"
        print(f"测试 {i+1}: {status}")
    
    overall = all(results)
    print(f"\n整体测试结果: {'通过' if overall else '失败'}")
    
    return overall

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)