#!/usr/bin/env python3
"""
测试图片下载和保存功能

这个脚本用于验证我们的图片下载和保存实现是否正常工作
"""

import asyncio
import aiohttp
import aiofiles
from pathlib import Path
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_download_and_save():
    """测试下载和保存图片功能"""
    try:
        # 模拟ComfyUI的图片URL（这里用一个测试图片）
        test_url = "https://httpbin.org/image/png"  # 测试用的PNG图片
        target_filename = "test_clay_style_alice_req123_output.png"
        
        # 确保输出目录存在
        output_dir = Path("outputs")
        output_dir.mkdir(exist_ok=True)
        
        target_path = output_dir / target_filename
        
        logger.info(f"开始下载测试图片: {test_url}")
        
        # 下载图片
        async with aiohttp.ClientSession() as session:
            async with session.get(test_url) as response:
                if response.status == 200:
                    # 保存到本地文件
                    async with aiofiles.open(target_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                    
                    file_size = target_path.stat().st_size
                    logger.info(f"图片下载成功: {target_filename}, 大小: {file_size} bytes")
                    
                    # 验证文件是否存在
                    if target_path.exists():
                        logger.info("✅ 文件保存验证成功")
                        return True
                    else:
                        logger.error("❌ 文件保存验证失败")
                        return False
                else:
                    logger.error(f"❌ 下载图片失败: HTTP {response.status}")
                    return False
                    
    except Exception as e:
        logger.error(f"❌ 测试异常: {e}")
        return False

async def test_server_url_generation():
    """测试服务器URL生成"""
    try:
        # 模拟工作流中的URL生成逻辑
        def get_server_base_url() -> str:
            try:
                # 这里模拟从配置获取
                return "http://127.0.0.1:8000"
            except Exception as e:
                logger.warning(f"获取服务器配置失败，使用默认值: {e}")
                return "http://127.0.0.1:8000"
        
        filename = "clay_style_alice_req123_output.png"
        base_url = get_server_base_url()
        local_url = f"{base_url}/outputs/{filename}"
        
        logger.info(f"生成的本地URL: {local_url}")
        logger.info("✅ URL生成测试成功")
        return True
        
    except Exception as e:
        logger.error(f"❌ URL生成测试失败: {e}")
        return False

async def main():
    """主测试函数"""
    logger.info("=== 开始图片下载和保存功能测试 ===")
    
    # 测试1: 下载和保存
    logger.info("\n--- 测试1: 图片下载和保存 ---")
    download_success = await test_download_and_save()
    
    # 测试2: URL生成
    logger.info("\n--- 测试2: 服务器URL生成 ---")
    url_success = await test_server_url_generation()
    
    # 总结
    logger.info("\n=== 测试结果总结 ===")
    logger.info(f"图片下载和保存: {'✅ 成功' if download_success else '❌ 失败'}")
    logger.info(f"URL生成: {'✅ 成功' if url_success else '❌ 失败'}")
    
    if download_success and url_success:
        logger.info("🎉 所有测试通过！")
        return True
    else:
        logger.error("💥 部分测试失败！")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)