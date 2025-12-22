# 任务对齐文档：文本分块服务 MCP 工具化

## 1. 项目与任务背景
本项目 `mcp_for_dify` 是一个基于 Python 的 MCP 服务框架。当前任务是将一个现有的 Python 脚本 (`demo/doc_spliter.py`) 转化为 MCP 工具，以便在 Dify 等平台中使用。

## 2. 原始需求
- **参考代码**: `/root/code/mcp_for_dify/demo/doc_spliter.py`
- **目标**: 重写为一个文本分块服务，发布为 MCP 工具。
- **约束**:
    - 业务逻辑、输入输出参数格式必须严格按照参考代码。
    - 按照现有项目结构集成 (`app/services`, `app/plugins`).
    - 代码必须有清晰的中文注释。
    - 不要随意编码，保持逻辑一致性。

## 3. 需求理解与分析
### 3.1 现有逻辑分析 (`doc_spliter.py`)
- **入口**: `main(mode, content, parent_block_size, sub_block_size, preview_url)`
- **模式**:
    - `pdf` / `pdf_text`: 处理 HTML 表格转 Markdown，保护特殊 token，分块。
    - `table` / `md_table` / `markdown`: 处理 Markdown 表格（表头提取），分块。
    - `image` / `img` / `text_with_preview`: 纯文本分块，追加图片链接。
- **输出**: `{"result": splited_content}` (JSON 兼容字典，但在 Python 中返回字典即可，MCP 框架会处理序列化)

### 3.2 架构集成
- **Service 层**: 创建 `app/services/text_splitter_service.py`。
    - 将 `doc_spliter.py` 中的逻辑封装进 `TextSplitterService` 类。
    - 保留所有辅助函数（如 `_protect_special_tokens`, `_split_into_units` 等）。
    - 确保 `process_split` 方法参数与 `main` 函数一致。
- **Plugin 层**: 创建 `app/plugins/text_splitter.py`。
    - 定义 `@mcp.tool()`。
    - 参数定义需与 `main` 函数一致。
    - 调用 Service 层逻辑。
- **注册**: 修改 `app/mcp/server.py` 引入插件。

## 4. 关键决策点
- **Q1**: 是否需要保留 `main` 函数作为入口？
    - **A**: 在 Service 层中，我们可以提供一个 `split` 方法作为统一入口，对应 `doc_spliter.py` 的 `main` 函数逻辑。
- **Q2**: 参数类型验证？
    - **A**: MCP (FastMCP) 使用 Type Hints 进行参数验证。我们应在 Tool 定义中保留详细的 Type Hints。
- **Q3**: 错误处理？
    - **A**: 原代码中有 `TypeError` 和 `ValueError`。MCP 工具抛出异常通常会被框架捕获并返回错误信息，这是可接受的。

## 5. 验收标准
1.  **功能一致性**: 新工具的输出必须与原脚本对相同输入的输出完全一致。
2.  **接口规范**: MCP 工具参数包含 `mode`, `content`, `parent_block_size`, `sub_block_size`, `preview_url`。
3.  **代码规范**: 包含完整的中文注释，符合项目结构。
4.  **可用性**: 服务启动后，可以通过 MCP 协议调用该工具。

## 6. 下一步计划
进入 Architect 阶段，设计详细的类结构和文件变更。
