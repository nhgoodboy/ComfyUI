# 请求ID统一化重构需求文档

## 项目介绍

本项目旨在统一witness/comfyui_workflow_server系统中的标识符管理，将原本分离的task_id和request_id统一为单一的request_id标识符。这将简化系统架构，减少标识符映射的复杂性，提高代码的可维护性和一致性。

## 需求

### 需求1：统一标识符架构

**用户故事：** 作为系统开发者，我希望系统使用统一的request_id作为任务标识符，这样可以简化代码逻辑并减少标识符映射的复杂性。

#### 验收标准

1. WHEN 创建转换任务时 THEN 系统应该只使用request_id作为唯一标识符
2. WHEN 查询任务状态时 THEN 系统应该接受request_id作为查询参数
3. WHEN 存储任务数据时 THEN 系统应该使用request_id作为主键
4. WHEN 进行任务映射时 THEN 系统不应该维护task_id到request_id的映射关系

### 需求2：RPC接口参数统一

**用户故事：** 作为API用户，我希望所有RPC方法都使用一致的参数名称，这样可以提供更好的API使用体验。

#### 验收标准

1. WHEN 调用transform.get_status方法时 THEN 应该使用request_id参数而不是task_id
2. WHEN 调用transform.get_result方法时 THEN 应该使用request_id参数而不是task_id
3. WHEN 调用transform.cancel方法时 THEN 应该使用request_id参数而不是task_id
4. WHEN 调用transform.list方法时 THEN 返回的任务列表应该使用request_id作为标识符

### 需求3：数据存储结构优化

**用户故事：** 作为系统维护者，我希望任务数据存储结构使用统一的标识符，这样可以简化数据管理和查询逻辑。

#### 验收标准

1. WHEN 存储用户任务数据时 THEN 应该使用request_id作为字典键
2. WHEN 建立prompt_id映射时 THEN 应该直接映射到request_id
3. WHEN 查询任务数据时 THEN 应该使用request_id进行查询
4. WHEN 清理旧任务时 THEN 应该基于request_id进行清理操作

### 需求4：WebSocket推送消息统一

**用户故事：** 作为前端开发者，我希望WebSocket推送的消息格式使用一致的标识符，这样可以简化客户端的消息处理逻辑。

#### 验收标准

1. WHEN 推送任务状态更新时 THEN 消息应该包含request_id字段
2. WHEN 推送任务进度时 THEN 应该使用request_id标识任务
3. WHEN 推送任务完成结果时 THEN 应该使用request_id作为任务标识
4. WHEN 客户端接收推送消息时 THEN 应该能够通过request_id识别对应的任务

### 需求5：错误处理和日志统一

**用户故事：** 作为系统运维人员，我希望错误消息和日志都使用统一的标识符，这样可以更容易地追踪和调试问题。

#### 验收标准

1. WHEN 记录任务相关日志时 THEN 应该使用request_id作为标识符
2. WHEN 返回错误消息时 THEN 应该在错误详情中包含request_id
3. WHEN 进行任务追踪时 THEN 应该使用request_id进行端到端追踪
4. WHEN 调试任务问题时 THEN 应该能够通过request_id快速定位相关日志

### 需求6：向后兼容性处理

**用户故事：** 作为API用户，我希望在过渡期间系统能够处理旧的API调用，这样可以平滑地迁移到新的接口。

#### 验收标准

1. WHEN 使用旧的task_id参数调用API时 THEN 系统应该返回清晰的错误消息指导使用request_id
2. WHEN 迁移现有数据时 THEN 系统应该能够处理历史数据中的task_id字段
3. WHEN 更新API文档时 THEN 应该明确说明参数变更和迁移指南
4. WHEN 部署新版本时 THEN 应该提供迁移脚本或工具

### 需求7：性能和一致性保证

**用户故事：** 作为系统用户，我希望重构后的系统保持原有的性能水平，并且数据访问更加一致。

#### 验收标准

1. WHEN 查询任务状态时 THEN 响应时间应该不超过原系统的1.2倍
2. WHEN 处理并发任务时 THEN 系统应该能够正确处理request_id的唯一性
3. WHEN 进行任务操作时 THEN 不应该出现标识符冲突或混淆
4. WHEN 系统重启后 THEN 应该能够正确恢复基于request_id的任务状态