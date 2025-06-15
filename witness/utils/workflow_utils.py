import json
from witness.app_server.models.image_processing import UserInfo # 确保可以正确导入
from typing import Dict, Any

def load_workflow(workflow_path: str) -> Dict[str, Any]:
    """
    从指定路径加载 ComfyUI 工作流 JSON 文件。

    参数:
    - workflow_path (str): 工作流 JSON 文件的路径。

    返回:
    - dict: 解析后的工作流字典。

    异常:
    - FileNotFoundError: 如果文件未找到。
    - json.JSONDecodeError: 如果文件不是有效的 JSON。
    """
    try:
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)
        print(f"工作流已从 {workflow_path} 加载。")
        return workflow
    except FileNotFoundError:
        print(f"错误: 工作流文件未找到于 {workflow_path}")
        raise
    except json.JSONDecodeError as e:
        print(f"错误: 解析工作流文件 {workflow_path} 失败: {e}")
        raise

def update_workflow_image_and_user(
    workflow: Dict[str, Any],
    uploaded_image_filename: str, 
    user_info: UserInfo,
    load_image_node_title: str = "Load Image", # 假设加载图像节点的标题
    save_image_node_title: str = "Save Image"  # 假设保存图像节点的标题
) -> Dict[str, Any]:
    """
    动态修改加载的 ComfyUI 工作流，以设置输入图像和用户信息（通过修改输出文件名前缀）。

    参数:
    - workflow (dict): 已加载的 ComfyUI 工作流字典。
    - uploaded_image_filename (str): 已上传到 ComfyUI 服务器的图像文件名 (例如 'input/uploaded_image.png')。
    - user_info (UserInfo): 用户信息对象。
    - load_image_node_title (str): 工作流中加载图像节点的预期标题。
    - save_image_node_title (str): 工作流中保存图像节点的预期标题。

    返回:
    - dict: 修改后的工作流字典。
    """
    updated_workflow = workflow.copy() # 操作副本以避免修改原始对象
    found_load_image = False
    found_save_image = False

    for node_id, node_data in updated_workflow.items():
        # 节点数据本身是一个字典，包含 class_type, inputs 等
        if not isinstance(node_data, dict):
            continue

        node_class_type = node_data.get("class_type")
        node_inputs = node_data.get("inputs", {})
        node_title = node_data.get("_meta", {}).get("title") # ComfyUI 通常将标题存储在 _meta 中

        # 查找并更新加载图像节点
        if node_class_type == "LoadImage" or node_title == load_image_node_title:
            if "image" in node_inputs:
                node_inputs["image"] = uploaded_image_filename
                print(f"节点 '{node_title or node_id}' (LoadImage) 的输入图像已更新为: {uploaded_image_filename}")
                found_load_image = True
            else:
                print(f"警告: 节点 '{node_title or node_id}' (LoadImage) 没有 'image' 输入项。")

        # 查找并更新保存图像节点的文件名前缀
        if node_class_type == "SaveImage" or node_title == save_image_node_title:
            if "filename_prefix" in node_inputs:
                original_prefix = node_inputs["filename_prefix"]
                new_prefix = f"{user_info.user_id}_{original_prefix}"
                node_inputs["filename_prefix"] = new_prefix
                print(f"节点 '{node_title or node_id}' (SaveImage) 的文件名前缀已更新为: {new_prefix}")
                found_save_image = True
            else:
                print(f"警告: 节点 '{node_title or node_id}' (SaveImage) 没有 'filename_prefix' 输入项。")

    if not found_load_image:
        print(f"警告: 未在工作流中找到标题为 '{load_image_node_title}' 或类型为 'LoadImage' 的加载图像节点。")
    if not found_save_image:
        print(f"警告: 未在工作流中找到标题为 '{save_image_node_title}' 或类型为 'SaveImage' 的保存图像节点。")

    return updated_workflow

# 示例用法 (用于测试)
if __name__ == "__main__":
    # 假设有一个 style_change.json 在 ../workflows/ 目录下
    # 并且该 JSON 中有一个 LoadImage 节点和一个 SaveImage 节点
    mock_workflow_path = "../workflows/style_change.json" # 调整路径使其能够找到
    
    # 创建一个临时的 mock workflow json 文件用于测试
    mock_workflow_content = {
        "3": {
            "inputs": {"image": "example.png"},
            "class_type": "LoadImage",
            "_meta": {"title": "Load Image"}
        },
        "9": {
            "inputs": {"filename_prefix": "ComfyUI"},
            "class_type": "SaveImage",
            "_meta": {"title": "Save Image"}
        }
    }
    # 为了能独立运行此脚本进行简单测试，我们直接使用这个 mock_workflow_content
    # 而不是依赖于一个实际的文件，除非你确保路径正确且文件存在
    # with open(mock_workflow_path, 'w') as f:
    #     json.dump(mock_workflow_content, f)

    try:
        # loaded_wf = load_workflow(mock_workflow_path)
        loaded_wf = mock_workflow_content # 使用内存中的 mock 数据
        print("原始工作流:", json.dumps(loaded_wf, indent=2))

        mock_user = UserInfo(user_id="test_user_123", user_group="test_group")
        mock_image_file = "uploaded/on_server/my_image.png"

        updated_wf = update_workflow_image_and_user(loaded_wf, mock_image_file, mock_user)
        print("\n更新后的工作流:", json.dumps(updated_wf, indent=2))

    except Exception as e:
        print(f"示例用法中发生错误: {e}")
    
    # 清理 mock 文件 (如果创建了)
    # import os
    # if os.path.exists(mock_workflow_path):
    #     os.remove(mock_workflow_path)