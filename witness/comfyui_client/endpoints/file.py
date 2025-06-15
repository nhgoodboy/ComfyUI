from .prompt import BaseAPI
from typing import Optional
import io

class FileAPI(BaseAPI):
    """
    用于管理文件的 API。
    """
    async def upload_image(self, *, image_bytes: bytes = None, image_path: str = None, filename: str = None, overwrite: bool = False, subfolder: Optional[str] = None):
        """
        上传图片到输入目录。

        :param image_bytes: 图片的字节流。
        :param image_path: 图片文件的本地路径。
        :param filename: 图片的文件名。
        :param overwrite: 是否覆盖同名的现有文件。
        :param subfolder: 要上传到的输入目录中的子文件夹。
        :return: API 返回的 JSON 响应。
        """
        if not image_bytes and not image_path:
            raise ValueError("必须提供 image_bytes 或 image_path")

        # 准备文件字段
        if image_bytes:
            files = {"image": io.BytesIO(image_bytes)}
            if filename:
                files["image"].name = filename
        else:
            f = open(image_path, "rb")
            files = {"image": f}

        data = {"overwrite": str(overwrite).lower()}
        if subfolder:
            data["subfolder"] = subfolder

        try:
            return await self._client._request("POST", "/upload/image", files=files, json_data=data)
        finally:
            # 关闭文件句柄
            if not image_bytes and image_path:
                f.close()

    async def view_file(self, filename: str, file_type: str, subfolder: str = ""):
        """
        检索输出文件（例如，图片、蒙版）。

        :param filename: 要查看的文件名。
        :param file_type: 目录的类型，例如 'output', 'input', 'temp'。
        :param subfolder: 文件所在的子文件夹。
        :return: 文件的原始内容（例如，图片的字节流）。
        """
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": file_type
        }
        return await self._client._request("GET", "/view", params=params) 