#!/usr/bin/env python3
"""
测试双图片上传API的脚本
"""

import sys
import os
import requests
import io
from PIL import Image

def create_test_image(color, size=(300, 300)):
    """创建测试图片"""
    img = Image.new('RGB', size, color)
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes

def test_dual_image_upload():
    """测试双图片上传功能"""
    print("=== 测试双图片上传API ===")
    
    # API端点
    url = "http://localhost:8080/api/transform"
    
    # 创建测试图片
    print("创建测试图片...")
    image1 = create_test_image('red', (300, 300))
    image2 = create_test_image('blue', (300, 300))
    
    # 准备上传数据
    files = {
        'file1': ('test_image1.png', image1, 'image/png'),
        'file2': ('test_image2.png', image2, 'image/png')
    }
    
    data = {
        'style_id': 'person_scene_merge',
        'request_id': 'test-dual-upload-123',
        'user_id': 'test-user-456'
    }
    
    try:
        print("发送双图片上传请求...")
        response = requests.post(url, files=files, data=data, timeout=30)
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 双图片上传API测试成功!")
            print(f"请求ID: {result.get('request_id', 'N/A')}")
            return True
        else:
            print("❌ 双图片上传API测试失败!")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败 - 请确保服务器在 http://localhost:8080 运行")
        return False
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

def test_single_image_upload():
    """测试单图片上传功能（兼容性测试）"""
    print("\n=== 测试单图片上传API（兼容性） ===")
    
    # API端点
    url = "http://localhost:8080/api/transform"
    
    # 创建测试图片
    print("创建测试图片...")
    image = create_test_image('green', (300, 300))
    
    # 准备上传数据
    files = {
        'file': ('test_image.png', image, 'image/png')
    }
    
    data = {
        'style_id': 'clay_style_transform',
        'request_id': 'test-single-upload-123',
        'user_id': 'test-user-456'
    }
    
    try:
        print("发送单图片上传请求...")
        response = requests.post(url, files=files, data=data, timeout=30)
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 单图片上传API测试成功!")
            print(f"请求ID: {result.get('request_id', 'N/A')}")
            return True
        else:
            print("❌ 单图片上传API测试失败!")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败 - 请确保服务器在 http://localhost:8080 运行")
        return False
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

def main():
    """主测试函数"""
    print("双图片上传功能API测试")
    print("=" * 50)
    print("⚠️  请确保以下服务正在运行:")
    print("   - ComfyUI工作流服务器 (http://localhost:8001)")
    print("   - Web前端服务器 (http://localhost:8080)")
    print()
    
    # 运行测试
    tests = [
        test_single_image_upload,  # 先测试兼容性
        test_dual_image_upload     # 再测试新功能
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"测试 {test.__name__} 出现异常: {e}")
            results.append(False)
    
    print(f"\n=== 测试结果 ===")
    test_names = ["单图片上传", "双图片上传"]
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "通过" if result else "失败"
        print(f"{name}: {status}")
    
    overall = all(results)
    print(f"\n整体测试结果: {'通过' if overall else '失败'}")
    
    if not overall:
        print("\n🔧 排查建议:")
        print("1. 检查服务器是否正常运行")
        print("2. 检查配置文件 (BASE_URL, 端口等)")
        print("3. 查看服务器日志获取详细错误信息")
        print("4. 确认双图片工作流已正确配置")
    
    return overall

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)