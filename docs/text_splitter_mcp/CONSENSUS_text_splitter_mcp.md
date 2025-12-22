# 任务共识文档：文本分块服务 MCP 工具化

## 1. 最终需求确认
- 将 `/root/code/mcp_for_dify/demo/doc_spliter.py` 逻辑移植到 MCP 服务中。
- 保持严格的输入输出格式一致性。
- 代码结构符合 `Controller (Plugin) -> Service` 分层。
- 必须包含详细中文注释。

## 2. 技术方案
### 2.1 核心组件
- **Service**: `app/services/text_splitter_service.py`
    - 类 `TextSplitterService`
    - 方法 `split(mode, content, parent_block_size, sub_block_size, preview_url) -> dict`
    - 包含原脚本中的所有私有辅助函数（如 `_convert_html_tables_to_markdown`, `_split_into_units` 等）。
- **Plugin**: `app/plugins/text_splitter.py`
    - 定义 MCP 工具 `text_splitter` (或 `doc_spliter` 以保持一致性，建议命名为 `text_splitter` 更清晰，但功能描述需准确)。
    - 参数:
        - `mode`: str
        - `content`: str
        - `parent_block_size`: int = 1024
        - `sub_block_size`: int = 512
        - `preview_url`: str = ""
- **Config**: `app/mcp/server.py`
    - 注册新插件。

### 2.2 边界与限制
- 不引入新的第三方库（原脚本只使用了 `re`, `html`, `typing`）。
- 不修改原有的 `doc_spliter.py` 文件（作为参考保留）。

## 3. 验收标准
- [ ] 单元测试通过：对比 Service 输出与原脚本输出一致。
- [ ] MCP 工具注册成功，可被调用。
- [ ] 代码注释完整清晰（中文）。
