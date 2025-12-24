# DESIGN_text_splitter_rewrite

## 1. 核心流程图 (Mermaid)

```mermaid
graph TD
    A[Input Text] --> B[Convert HTML Tables to MD]
    B --> C[Tokenize: Replace Images/Tables with IDs]
    C --> D[Split by Level-1 Header (# )]
    D --> E{For Each Coarse Block}
    E -->|Size <= Parent Limit| F[Add to Parent List]
    E -->|Size > Parent Limit| G[Refine: Split by Headers/Paragraphs]
    G --> F
    F --> H{For Each Parent Block}
    H --> I[Split into Sub Blocks]
    I --> J{Check Content Type}
    J -->|Token (Image/Table)| K[Handle Atomic Token]
    J -->|Normal Text| L[Split by Sub Limit]
    K -->|Size <= Sub Limit| M[Keep as Single Sub Block]
    K -->|Size > Sub Limit| N[Split Atomic Content (Para/Row)]
    L --> O[Add to Sub List]
    M --> O
    N --> O
    O --> P[Join Sub Blocks with Sub Separator]
    P --> Q[Join Parent Blocks with Parent Separator]
    Q --> R[Restore Tokens (if needed, but structure already handled)]
    R --> S[Output]
```

## 2. 模块详细设计

### 2.1 预处理与 Tokenization
*   **HTML 转 Markdown**: 复用现有 `_convert_html_tables_to_markdown`。
*   **Tokenization**:
    *   Image Regex: `r"【(?:图片主题|图片解析内容).*?】"` (DOTALL)。
    *   Table Regex: `r"(?:^\s*\|.*\|\s*$\\n?)+"` (MULTILINE)。
    *   存储: `self._tokens_map = { "<<ATOMIC_IMG_0>>": content, ... }`。
    *   替换: 将原文中的原子内容替换为 Token ID。

### 2.2 一级粗切 (Coarse Split)
*   使用正则 `r"(?m)(^# .*$)"` 进行切分。
*   逻辑：保留分隔符（标题本身），将 `Header + Body` 组合成一个 Block。
*   **注意**: 如果文本开头没有标题，第一部分作为第一个 Block。

### 2.3 父块细化 (Parent Refinement)
*   输入: Coarse Block (Tokenized)。
*   逻辑:
    *   计算 `real_length` (展开 Token 后的长度)。
    *   如果 `real_length <= parent_block_size`: 直接返回 `[block]`。
    *   如果 `real_length > parent_block_size`:
        *   尝试按二级标题 `## ` 切分。
        *   若仍大，按 `### ` 切分。
        *   若无标题可切，按段落 `\n\n` 切分。
        *   若仍大，按句子切分。
    *   **关键**: 这一步生成的只是 Parent Blocks 列表，每个 Block 内部可能包含多个 Sub Blocks。

### 2.4 子块拆分 (Sub Block Splitting)
*   输入: Parent Block (Tokenized)。
*   逻辑:
    *   按 Token ID 切分当前文本: `re.split(r"(<<ATOMIC_.*?>>)", text)`。
    *   遍历切分后的片段:
        *   **Is Token?**:
            *   获取原始内容。
            *   Check `len(content) <= sub_block_size`.
            *   **Yes**: 添加到 Sub List。
            *   **No**:
                *   **Image**: 按段落 `\n` 切分。每段作为一个 Sub Block。
                *   **Table**: 按行 `\n` 切分。重新组合行，确保 `Header + Rows` 不超限。每组作为一个 Sub Block。
        *   **Is Text?**:
            *   按 `sub_block_size` 递归切分（RecursiveCharacterSplitter）。
            *   添加到 Sub List。
    *   输出: List[Sub Block String] (此时已是原始内容，不再是 Token ID)。

### 2.5 组装
*   Sub Blocks Join: `sub_separator.join(sub_blocks)`.
*   Parent Blocks Join: `parent_separator.join(parent_blocks)`.

## 3. 接口定义

```python
def _split_pdf_text(self, content: str, parent_block_size: int, sub_block_size: int, parent_separator: str, sub_separator: str) -> str:
    # 1. Preprocess
    # 2. Tokenize
    # 3. Coarse Split
    # 4. Loop & Refine & Sub-split
    # 5. Join
```

## 4. 关键算法：超大表格切分
*   解析 Markdown 表格为 `Header` 和 `Rows`。
*   Accumulate Rows: `current_chunk = Header`.
*   Loop Rows:
    *   `if len(current_chunk + row) > sub_limit`:
        *   Yield `current_chunk`.
        *   `current_chunk = Header + row`.
    *   `else`:
        *   `current_chunk += row`.
*   Yield last `current_chunk`.
