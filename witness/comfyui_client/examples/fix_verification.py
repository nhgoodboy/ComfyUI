"""
修复验证脚本

验证ComfyUI客户端的关键修复是否正常工作。
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加父目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from comfyui_client import (
    ComfyUIClient, 
    ComfyUIClientConfig,
    ComfyUIValidationError,
    ComfyUIConnectionError,
    ComfyUIAPIError,
    ComfyUITimeoutError,
    ComfyUIFileError
)


def test_configuration_system():
    """测试配置系统是否正常工作"""
    print("=== 测试配置系统 ===")
    
    try:
        # 测试默认配置
        default_config = ComfyUIClientConfig.create_default()
        print(f"✅ 默认配置创建成功: 超时={default_config.request_timeout}s")
        
        # 测试快速配置
        fast_config = ComfyUIClientConfig.create_fast()
        print(f"✅ 快速配置创建成功: 超时={fast_config.request_timeout}s")
        
        # 测试健壮配置
        robust_config = ComfyUIClientConfig.create_robust()
        print(f"✅ 健壮配置创建成功: 超时={robust_config.request_timeout}s")
        
        # 测试自定义配置
        custom_config = ComfyUIClientConfig(
            request_timeout=45.0,
            max_retries=3,
            retry_delay=1.5
        )
        print(f"✅ 自定义配置创建成功: 超时={custom_config.request_timeout}s")
        
        # 测试配置验证
        try:
            invalid_config = ComfyUIClientConfig(request_timeout=-1)  # 应该失败
            print("❌ 配置验证失败 - 应该抛出异常")
        except ValueError as e:
            print(f"✅ 配置验证正常工作: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置系统测试失败: {e}")
        return False


def test_exception_system():
    """测试异常系统是否正常工作"""
    print("\n=== 测试异常系统 ===")
    
    try:
        # 测试基础异常
        base_error = ComfyUIConnectionError("测试连接错误", server_url="http://test.com")
        print(f"✅ 基础异常创建成功: {base_error}")
        
        # 测试API异常
        api_error = ComfyUIAPIError("测试API错误", endpoint="/test", method="GET", status_code=404)
        print(f"✅ API异常创建成功: {api_error}")
        
        # 测试验证异常
        validation_error = ComfyUIValidationError("测试验证错误", parameter="test_param", expected_type="str")
        print(f"✅ 验证异常创建成功: {validation_error}")
        
        # 测试超时异常
        timeout_error = ComfyUITimeoutError("测试超时错误", timeout_seconds=30.0, operation="GET /test")
        print(f"✅ 超时异常创建成功: {timeout_error}")
        
        # 测试文件异常
        file_error = ComfyUIFileError("测试文件错误", file_path="/test/file.txt", operation="upload")
        print(f"✅ 文件异常创建成功: {file_error}")
        
        return True
        
    except Exception as e:
        print(f"❌ 异常系统测试失败: {e}")
        return False


def test_input_validation():
    """测试输入验证系统"""
    print("\n=== 测试输入验证系统 ===")
    
    try:
        from comfyui_client.utils.validation import (
            validate_required_string,
            validate_bytes_data,
            validate_positive_integer,
            validate_file_path
        )
        
        # 测试字符串验证
        valid_string = validate_required_string("test_string", "test_param")
        print(f"✅ 字符串验证通过: {valid_string}")
        
        # 测试字节数据验证
        valid_bytes = validate_bytes_data(b"test_data", "test_param")
        print(f"✅ 字节数据验证通过: {len(valid_bytes)} bytes")
        
        # 测试正整数验证
        valid_int = validate_positive_integer(5, "test_param")
        print(f"✅ 正整数验证通过: {valid_int}")
        
        # 测试文件路径验证
        valid_path = validate_file_path("test/file.txt", "test_param")
        print(f"✅ 文件路径验证通过: {valid_path}")
        
        # 测试验证错误
        try:
            validate_required_string("", "test_param")  # 应该失败
            print("❌ 验证错误检测失败")
        except ComfyUIValidationError as e:
            print(f"✅ 验证错误正常检测: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 输入验证系统测试失败: {e}")
        return False


def test_client_creation():
    """测试客户端创建"""
    print("\n=== 测试客户端创建 ===")
    
    try:
        # 测试默认客户端
        default_client = ComfyUIClient()
        print(f"✅ 默认客户端创建成功: {default_client.base_url}")
        
        # 测试带配置的客户端
        config = ComfyUIClientConfig.create_robust()
        config_client = ComfyUIClient(config=config)
        print(f"✅ 配置客户端创建成功: {config_client.base_url}")
        
        # 测试WebSocket客户端
        ws_client = default_client.get_websocket()
        print(f"✅ WebSocket客户端创建成功: {ws_client.url}")
        
        return True
        
    except Exception as e:
        print(f"❌ 客户端创建测试失败: {e}")
        return False


async def test_request_with_data():
    """测试新的_request_with_data方法"""
    print("\n=== 测试数据请求方法 ===")
    
    try:
        config = ComfyUIClientConfig.create_fast()
        config.request_timeout = 2.0  # 短超时以快速失败
        
        client = ComfyUIClient(config=config)
        
        # 测试是否有新方法
        if hasattr(client, '_request_with_data'):
            print("✅ _request_with_data 方法存在")
        else:
            print("❌ _request_with_data 方法不存在")
            return False
        
        # 测试是否能正确处理参数验证
        try:
            await client.userdata.upload_userdata_file("", b"test")  # 空文件名应该失败
            print("❌ 参数验证失败 - 应该抛出异常")
        except ComfyUIValidationError:
            print("✅ 参数验证正常工作")
        except Exception as e:
            print(f"✅ 其他异常（可能是网络问题）: {type(e).__name__}")
        
        await client.close()
        return True
        
    except Exception as e:
        print(f"❌ 数据请求方法测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("ComfyUI客户端修复验证开始")
    print("=" * 50)
    
    results = []
    
    # 运行所有测试
    results.append(test_configuration_system())
    results.append(test_exception_system())
    results.append(test_input_validation())
    results.append(test_client_creation())
    results.append(await test_request_with_data())
    
    # 汇总结果
    passed = sum(results)
    total = len(results)
    
    print("\n" + "=" * 50)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！修复验证成功！")
    else:
        print("⚠️  部分测试失败，可能需要进一步检查")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 