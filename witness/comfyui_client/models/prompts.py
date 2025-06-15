from pydantic import BaseModel, Field
from typing import Dict, Any, List, Tuple

class NodeInput(BaseModel):
    """
    表示工作流中单个节点的输入。
    这是一个灵活的模型，因为不同的节点有不同的输入。
    """
    class Config:
        extra = 'allow'  # 允许任意字段

class WorkflowNode(BaseModel):
    """
    表示 ComfyUI 工作流中的单个节点。
    """
    inputs: Dict[str, Any]
    class_type: str = Field(..., alias="class_type")

class Workflow(BaseModel):
    """
    表示一个完整的 ComfyUI 工作流，它是一个节点的集合。
    键是节点 ID。
    """
    nodes: Dict[str, WorkflowNode]

    def to_api_format(self) -> Dict[str, Any]:
        """
        将工作流转换为 ComfyUI API 期望的格式。
        API 期望一个扁平的节点字典，而不是嵌套在 "nodes" 键下。
        """
        return {node_id: node.dict(by_alias=True) for node_id, node in self.nodes.items()} 