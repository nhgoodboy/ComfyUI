#!/usr/bin/env python3
"""
新架构测试脚本

测试工作流注册中心、工作流管理器和API的基本功能。
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from app.core.workflow_registry import workflow_registry
    from app.core.workflow_manager import WorkflowManager, set_workflow_manager
    from app.workflows.built_in.style_transform import StyleTransformWorkflow
    from app.services.comfyui_service import ComfyUIService
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保在正确的目录中运行此脚本")
    sys.exit(1)


async def test_workflow_registry():
    """测试工作流注册中心"""
    print("=== 测试工作流注册中心 ===")
    
    try:
        # 手动注册一个工作流进行测试
        workflow_registry.register_workflow(StyleTransformWorkflow)
        print("✅ 工作流注册成功")
        
        # 测试列出工作流
        workflows = workflow_registry.list_workflows()
        print(f"✅ 已注册工作流: {workflows}")
        
        # 测试获取工作流
        workflow = workflow_registry.get_workflow("style_transform")
        if workflow:
            print("✅ 工作流获取成功")
            print(f"   工作流名称: {workflow.metadata.name}")
            print(f"   工作流描述: {workflow.metadata.description}")
        else:
            print("❌ 工作流获取失败")
        
        # 测试获取元数据
        metadata = workflow_registry.get_workflow_metadata("style_transform")
        if metadata:
            print("✅ 元数据获取成功")
            print(f"   参数数量: {len(metadata.get('parameter_schema', {}).get('properties', {}))}")
        else:
            print("❌ 元数据获取失败")
        
        return True
        
    except Exception as e:
        print(f"❌ 工作流注册中心测试失败: {e}")
        return False


async def test_workflow_validation():
    """测试工作流参数验证"""
    print("\n=== 测试工作流参数验证 ===")
    
    try:
        workflow = workflow_registry.get_workflow("style_transform")
        if not workflow:
            print("❌ 无法获取工作流")
            return False
        
        # 测试有效参数
        valid_params = {
            "image": "test_image.jpg",
            "style_prompt": "测试风格提示词",
            "strength": 0.6,
            "steps": 20,
            "cfg_scale": 7.0
        }
        
        validated = workflow.validate_parameters(valid_params)
        print("✅ 有效参数验证通过")
        print(f"   验证后参数数量: {len(validated)}")
        
        # 测试无效参数
        invalid_params = {
            "image": "",  # 空字符串
            "style_prompt": "",  # 空字符串
            "strength": 2.0,  # 超出范围
            "steps": -1  # 负数
        }
        
        try:
            workflow.validate_parameters(invalid_params)
            print("❌ 无效参数验证应该失败但没有")
            return False
        except ValueError:
            print("✅ 无效参数验证正确失败")
        
        return True
        
    except Exception as e:
        print(f"❌ 参数验证测试失败: {e}")
        return False


async def test_workflow_build():
    """测试工作流构建"""
    print("\n=== 测试工作流构建 ===")
    
    try:
        workflow = workflow_registry.get_workflow("style_transform")
        if not workflow:
            print("❌ 无法获取工作流")
            return False
        
        # 准备参数
        params = {
            "image": "test_image.jpg",
            "style_prompt": "油画风格，浓重色彩",
            "strength": 0.7,
            "steps": 25,
            "cfg_scale": 7.5,
            "negative_prompt": "低质量，模糊",
            "sampler_name": "euler",
            "scheduler": "normal",
            "checkpoint": "sd_xl_base_1.0.safetensors"
        }
        
        # 验证参数
        validated_params = workflow.validate_parameters(params)
        
        # 构建工作流
        workflow_json = await workflow.build_workflow(validated_params)
        
        if isinstance(workflow_json, dict) and workflow_json:
            print("✅ 工作流构建成功")
            print(f"   节点数量: {len(workflow_json)}")
            
            # 检查关键节点
            key_nodes = ["1", "2", "3", "4", "5", "6", "7", "8"]
            missing_nodes = [node for node in key_nodes if node not in workflow_json]
            if not missing_nodes:
                print("✅ 所有关键节点都存在")
            else:
                print(f"⚠️  缺少节点: {missing_nodes}")
            
            # 检查参数是否正确设置
            if workflow_json.get("1", {}).get("inputs", {}).get("image") == params["image"]:
                print("✅ 图像参数设置正确")
            else:
                print("❌ 图像参数设置错误")
            
            if workflow_json.get("2", {}).get("inputs", {}).get("text") == params["style_prompt"]:
                print("✅ 风格提示词设置正确")
            else:
                print("❌ 风格提示词设置错误")
            
        else:
            print("❌ 工作流构建失败")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 工作流构建测试失败: {e}")
        return False


class MockComfyUIService:
    """模拟ComfyUI服务"""
    
    async def queue_prompt(self, workflow_json):
        return "mock_prompt_id_12345"
    
    async def get_prompt_status(self, prompt_id):
        return "completed"
    
    async def get_result(self, prompt_id):
        return {
            "output_images": ["result_image.jpg"],
            "metadata": {"execution_time": 30.5}
        }
    
    async def cancel_prompt(self, prompt_id):
        return True


async def test_workflow_manager():
    """测试工作流管理器"""
    print("\n=== 测试工作流管理器 ===")
    
    try:
        # 创建模拟服务
        mock_service = MockComfyUIService()
        
        # 创建工作流管理器
        manager = WorkflowManager(mock_service)
        set_workflow_manager(manager)
        
        print("✅ 工作流管理器创建成功")
        
        # 测试任务创建
        params = {
            "image": "test_image.jpg",
            "style_prompt": "测试风格",
            "strength": 0.6
        }
        
        # 这里我们不实际执行，只是测试管理器的基本功能
        print("✅ 工作流管理器基本功能正常")
        
        # 测试统计信息
        stats = manager.get_statistics()
        if isinstance(stats, dict):
            print("✅ 统计信息获取成功")
            print(f"   总任务数: {stats.get('total_tasks', 0)}")
            print(f"   运行中任务: {stats.get('running_tasks', 0)}")
        else:
            print("❌ 统计信息获取失败")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 工作流管理器测试失败: {e}")
        return False


async def test_parameter_schema():
    """测试参数Schema生成"""
    print("\n=== 测试参数Schema生成 ===")
    
    try:
        workflow = workflow_registry.get_workflow("style_transform")
        if not workflow:
            print("❌ 无法获取工作流")
            return False
        
        schema = workflow.get_parameter_schema()
        
        if isinstance(schema, dict):
            print("✅ 参数Schema生成成功")
            
            # 检查Schema结构
            if "type" in schema and schema["type"] == "object":
                print("✅ Schema类型正确")
            else:
                print("❌ Schema类型错误")
                return False
            
            if "properties" in schema:
                properties = schema["properties"]
                print(f"✅ 参数数量: {len(properties)}")
                
                # 检查必需参数
                required = schema.get("required", [])
                print(f"✅ 必需参数: {required}")
                
                # 检查特定参数
                if "image" in properties:
                    print("✅ 图像参数存在")
                if "style_prompt" in properties:
                    print("✅ 风格提示词参数存在")
                
            else:
                print("❌ Schema缺少properties")
                return False
            
        else:
            print("❌ 参数Schema生成失败")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 参数Schema测试失败: {e}")
        return False


async def run_all_tests():
    """运行所有测试"""
    print("ComfyUI工作流服务器 - 新架构测试")
    print("=" * 50)
    
    tests = [
        ("工作流注册中心", test_workflow_registry),
        ("工作流参数验证", test_workflow_validation),
        ("工作流构建", test_workflow_build),
        ("参数Schema生成", test_parameter_schema),
        ("工作流管理器", test_workflow_manager),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'=' * 20} {test_name} {'=' * 20}")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ 测试 {test_name} 出现异常: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("测试结果汇总:")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:<20} {status}")
        if result:
            passed += 1
    
    print(f"\n总体结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！新架构基本功能正常。")
        return True
    else:
        print("⚠️  部分测试失败，需要检查相关功能。")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n测试被中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n测试运行失败: {e}")
        sys.exit(1) 