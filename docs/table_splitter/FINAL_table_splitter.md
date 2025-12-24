# 表格分块功能重构总结报告

## 1. 任务概述
对 `/root/code/mcp_for_dify/app/services/text_splitter_service.py` 进行重构，实现基于严格大小限制的表格数据分块逻辑。

## 2. 核心变更
- **新增 `_split_table_text` 方法**：
  - 专门处理 `table`, `md_table`, `markdown` 模式的分块请求。
  - 包含 HTML 表格到 Markdown 的转换。
  - 自动识别表头（Header）和数据行（Rows）。
- **严格的分块逻辑**：
  - **父块大小限制 (parent_block_size)**：严格计算包含表头、子块内容及分隔符的总长度，确保不超过限制。
  - **子块大小限制 (sub_block_size)**：严格计算包含数据行的总长度。
  - **表头预留**：对于父块的第一个子块，自动扣除表头长度，以确保在视觉上（Result）和逻辑上都符合预期。
  - **行完整性**：分块时绝不拆断单行数据。
  - **表头补全**：所有非首个父块都会自动补全表头信息。

## 3. 验证结果
使用 `demo/demo.txt` 作为输入，`demo/result.txt` 作为参考标准进行验证。

- **逻辑一致性**：生成的 Markdown 表格结构、表头重复逻辑、行数据完整性均与 `result.txt` 一致。
- **大小限制执行**：
  - 输入参数 `parent_block_size=1024`。
  - `result.txt` 中的第二个父块实际长度为 **1026 字符**（超出 1024 限制 2 字符）。
  - 本次实现严格遵守 1024 限制，因此在处理该边界情况时，会将导致超限的行（Row 36）自动划分到下一个父块中。
  - **结论**：代码实现比参考结果更严格地遵守了 `parent_block_size` 参数限制。

## 4. 文件修改
- `app/services/text_splitter_service.py`: 核心逻辑修改。

## 5. 待办事项 (TODO)
- [ ] 考虑是否需要为 `parent_block_size` 增加少量容差（Tolerance），以兼容类似 `result.txt` 的边缘情况。
- [ ] 建议在前端或调用方明确 `parent_block_size` 的严格性含义。
