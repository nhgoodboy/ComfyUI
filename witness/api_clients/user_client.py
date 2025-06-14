# witness/api_clients/user_client.py
# 备注：此类用于与 ComfyUI 的用户和设置相关 API 进行交互。
from ..utils.http_client import HttpClient

class UserClient:
    def __init__(self, http_client: HttpClient = None):
        """初始化 UserClient。

        参数:
            http_client (HttpClient, 可选): 用于发出 HTTP 请求的客户端。
                                            如果未提供，则创建一个新的 HttpClient 实例。
        """
        self.http_client = http_client or HttpClient()

    def get_users(self):
        """(实验性) 获取用户信息 (如果启用了用户管理)。"""
        try:
            response = self.http_client.get("/users")
            return response
        except Exception as e:
            print(f"获取用户时出错: {e}")
            raise

    def get_user_data(self):
        """(实验性) 获取与当前用户关联的数据。
           如果 ComfyUI 以 --api-key-required 启动，则需要 API 密钥。
        """
        try:
            # 此端点可能需要身份验证 (请求头中的 API 密钥)
            # 如果已配置，HttpClient 应处理添加 API 密钥的操作
            response = self.http_client.get("/userdata")
            return response
        except Exception as e:
            print(f"获取用户数据时出错: {e}")
            raise

    def get_settings(self):
        """(实验性) 获取当前的 ComfyUI 设置。
           如果 ComfyUI 以 --api-key-required 启动，则需要 API 密钥。
        """
        try:
            # 此端点可能需要身份验证 (请求头中的 API 密钥)
            response = self.http_client.get("/settings")
            return response
        except Exception as e:
            print(f"获取设置时出错: {e}")
            raise

    def get_i18n_translations(self, lang: str = 'en-US'):
        """获取给定语言的国际化/本地化数据。

        参数:
            lang (str, 可选): 语言代码 (例如 'en-US', 'zh-CN')。默认为 'en-US'。

        返回:
            dict: 翻译数据。
        """
        params = {'lang': lang}
        try:
            response = self.http_client.get("/i18n", params=params)
            return response
        except Exception as e:
            print(f"获取语言 '{lang}' 的 i18n 翻译时出错: {e}")
            raise

# 示例用法 (可以删除或移动到测试/示例文件)
if __name__ == '__main__':
    # 此示例需要一个正在运行的 ComfyUI 实例。
    # 某些端点可能需要 --enable-cors-header 和/或 --api-key-required 标志
    # 以及 config/settings.py 中的有效 API 密钥才能实现全部功能。
    try:
        user_client = UserClient()
        
        print("尝试获取用户 (实验性)...")
        users = user_client.get_users()
        print("用户:", users)

        print("\n尝试获取用户数据 (实验性, 可能需要 API 密钥)...")
        user_data = user_client.get_user_data()
        print("用户数据:", user_data)

        print("\n尝试获取设置 (实验性, 可能需要 API 密钥)...")
        settings_data = user_client.get_settings()
        print("设置:", settings_data)

        print("\n尝试获取 i18n 翻译 (en-US)...")
        translations_en = user_client.get_i18n_translations()
        # print("i18n (en-US):", translations_en) # 可能很大
        print(f"已检索到 {len(translations_en.keys())} 个 en-US 的翻译键。")

        print("\n尝试获取 i18n 翻译 (zh-CN)...")
        translations_zh = user_client.get_i18n_translations(lang='zh-CN')
        # print("i18n (zh-CN):", translations_zh)
        if translations_zh:
             print(f"已检索到 {len(translations_zh.keys())} 个 zh-CN 的翻译键。")
        else:
            print("未找到 zh-CN 的翻译，或端点未完全支持。")

    except Exception as e:
        print(f"用户客户端示例失败: {e}")
        print("请确保 ComfyUI 正在运行，可能需要使用 --enable-cors-header。")
        print("对于 /userdata 和 /settings，如果使用 --api-key-required，请确保在配置中设置了 API_KEY。")