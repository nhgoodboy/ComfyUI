# witness/api_clients/file_client.py
# 备注：本文件中的注释已翻译为中文。
from ..utils.http_client import HttpClient
import os

class FileClient:
    def __init__(self, http_client: HttpClient = None):
        self.http_client = http_client or HttpClient()

    def upload_image(self, image_path: str, overwrite: bool = False, subfolder: str = None):
        """将图像文件上传到 ComfyUI。

        参数:
            image_path (str): 图像文件的路径。
            overwrite (bool, 可选): 如果同名文件已存在，是否覆盖。
            subfolder (str, 可选): 上传图像到的子文件夹。

        返回:
            dict: API 响应，通常包含名称、子文件夹和类型。
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        files = {'image': (os.path.basename(image_path), open(image_path, 'rb'))}
        data = {}
        if overwrite:
            data['overwrite'] = 'true' # API 需要字符串 'true' 或 'false'
        if subfolder:
            data['subfolder'] = subfolder
        
        try:
            response = self.http_client.multipart_post("/upload/image", files=files, data=data)
            return response
        finally:
            # 确保请求后文件已关闭
            if 'image' in files and files['image'] and hasattr(files['image'][1], 'close'):
                files['image'][1].close()

    def upload_mask(self, mask_path: str, overwrite: bool = False, subfolder: str = None):
        """将掩码文件上传到 ComfyUI。类似于 upload_image。"""
        # 根据文档，/upload/mask 的 API 在结构上与 /upload/image 相同，
        # 只是端点和语义不同。
        if not os.path.exists(mask_path):
            raise FileNotFoundError(f"Mask file not found: {mask_path}")

        files = {'image': (os.path.basename(mask_path), open(mask_path, 'rb'))} # API 使用 'image' 字段名
        data = {}
        if overwrite:
            data['overwrite'] = 'true'
        if subfolder:
            data['subfolder'] = subfolder

        try:
            response = self.http_client.multipart_post("/upload/mask", files=files, data=data)
            return response
        finally:
            if 'image' in files and files['image'] and hasattr(files['image'][1], 'close'):
                files['image'][1].close()

    def view_file(self, filename: str, subfolder: str, file_type: str, channel: str = None, preview: str = None):
        """从 ComfyUI 检索文件（例如图像）。

        参数:
            filename (str): 文件名。
            subfolder (str): 文件所在的子文件夹（例如 'outputs', 'inputs'）。
            file_type (str): 文件夹类型（例如 'output', 'input', 'temp'）。
            channel (str, 可选): 用于多通道图像（rgb, alpha, rgba）。
            preview (str, 可选): 预览格式（png, jpeg）。

        返回:
            bytes: 文件内容。
        """
        params = {
            'filename': filename,
            'subfolder': subfolder,
            'type': file_type
        }
        if channel:
            params['channel'] = channel
        if preview:
            params['preview'] = preview
        
        try:
            # 此端点返回原始文件字节，而非 JSON
            response_content = self.http_client.get("/view", params=params)
            return response_content
        except Exception as e:
            print(f"Error viewing file {filename}: {e}")
            raise

    def view_metadata(self, folder_type: str, filename: str):
        """检索特定文件的元数据（例如，来自 PNG 的工作流程）。

        参数:
            folder_type (str): 文件夹类型（例如 'outputs'）。
            filename (str): 文件名。

        返回:
            dict: 元数据，通常包含工作流程和提示信息。
        """
        endpoint = f"/view_metadata/{folder_type}/{filename}"
        try:
            response = self.http_client.get(endpoint)
            return response
        except Exception as e:
            print(f"Error viewing metadata for {filename} in {folder_type}: {e}")
            raise

# 示例用法 (可以删除或移至测试/示例文件)
if __name__ == '__main__':
    # 此示例需要正在运行的 ComfyUI 实例和示例图像文件。
    # 创建一个用于测试上传的虚拟图像文件
    sample_image_name = "sample_upload_test_image.png"
    try:
        with open(sample_image_name, 'wb') as f:
            f.write(os.urandom(1024)) # 创建一个小的虚拟二进制文件
        
        file_client = FileClient()
        print(f"尝试上传图像: {sample_image_name}...")
        upload_response = file_client.upload_image(sample_image_name, overwrite=True, subfolder="test_uploads")
        print("上传响应:", upload_response)

        if upload_response and 'name' in upload_response:
            uploaded_filename = upload_response['name']
            uploaded_subfolder = upload_response.get('subfolder', '')
            uploaded_type = upload_response.get('type', 'input') # 如果未指定，则默认为 'input'
            
            print(f"\n尝试查看已上传的图像: {uploaded_filename}...")
            image_bytes = file_client.view_file(uploaded_filename, uploaded_subfolder, uploaded_type)
            print(f"已查看图像，大小: {len(image_bytes)} 字节")
            # 你可以在此处保存或处理 image_bytes
            
            # 如果是带有元数据的 PNG (此虚拟文件没有元数据)
            # print(f"\n尝试查看元数据: {uploaded_filename}...")
            # metadata = file_client.view_metadata(uploaded_type, uploaded_filename)
            # print("元数据:", metadata)

    except FileNotFoundError as fnf_err:
        print(f"示例执行期间文件未找到: {fnf_err}")
    except Exception as e:
        print(f"文件客户端示例失败: {e}")
        print("请确保 ComfyUI 正在运行。")
    finally:
        if os.path.exists(sample_image_name):
            os.remove(sample_image_name)