# TASK_text_splitter_rewrite

## 1. 任务清单

### Task 1: 基础工具方法重构
*   **输入**: 无。
*   **输出**: 更新后的辅助方法。
*   **内容**:
    *   `_convert_html_tables_to_markdown`: 确保存在且有效。
    *   `_tokenize_content`: 实现图片和表格的正则替换与存储。
    *   `_get_real_length`: 计算包含 Token 的文本真实长度。

### Task 2: 核心切分逻辑实现 (`_split_pdf_text`)
*   **输入**: `content`, `limits`, `separators`。
*   **输出**: 最终合并字符串。
*   **内容**:
    *   实现主流程：Preprocessing -> Tokenization -> Coarse Split -> Processing Loop -> Join。
    *   实现 `_coarse_split_by_h1`: 按一级标题切分。

### Task 3: 父块细化逻辑 (`_refine_parent_block`)
*   **输入**: Coarse Block (Tokenized)。
*   **输出**: List[Parent Block] (Tokenized)。
*   **内容**:
    *   检查大小。
    *   递归切分（Headers -> Paragraphs）。

### Task 4: 子块拆分逻辑 (`_split_into_sub_blocks`)
*   **输入**: Parent Block (Tokenized)。
*   **输出**: List[Sub Block String] (Detokenized)。
*   **内容**:
    *   识别 Token 和 Text。
    *   实现 `_split_atomic_token`: 处理超大图片/表格。
    *   实现 `_split_normal_text`: 处理普通文本。

### Task 5: 验证与调试
*   **输入**: `demo.txt`。
*   **输出**: 验证报告。
*   **内容**:
    *   运行脚本，检查输出格式。
    *   确认分隔符位置。

## 2. 依赖关系
Task 1 -> Task 2 -> Task 3 -> Task 4 -> Task 5
