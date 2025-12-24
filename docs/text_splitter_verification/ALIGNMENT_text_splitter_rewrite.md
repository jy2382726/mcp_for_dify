# ALIGNMENT_text_splitter_rewrite

## 1. 原始需求 (Original Requirements)

用户要求完全重写 `TextSplitterService` 的分块逻辑，具体步骤如下：

1.  **预处理**：将 HTML 表格转换为 Markdown 表格。
2.  **原子保护**：将图片（`【图片主题：...】`）和表格作为原子单元进行保护。
3.  **一级粗切**：按一级标题 `# ` 进行初步切分，确保每个分块结尾有父块分隔符。
4.  **父块细分**：
    *   校验粗切块是否超过父块大小上限 (`parent_block_size`)。
    *   如果超过，在块内部按段落结构进一步拆分为多个父块。
5.  **子块拆分**：
    *   在父块基础上拆分子块。
    *   **核心原则**：原子保护部分（图片/表格）必须独立拆分，即前后必须有子块分隔符。
    *   非原子内容根据子块大小限制 (`sub_block_size`) 插入子块分隔符。
6.  **超限原子处理**：
    *   原子内容不能超过子块限制。
    *   **图片超限**：按完整段落拆分，插入子块分隔符。
    *   **表格超限**：在保证行数据完整性的前提下拆分，插入子块分隔符。
7.  **动态管理**：保持现有的分块大小动态计算逻辑。

## 2. 边界确认 (Boundary Confirmation)

*   **输入**：Raw Text (PDF提取内容)。
*   **输出**：处理后的文本，包含明确的 `parent_separator` 和 `sub_separator`。
*   **关键约束**：
    *   优先级：一级标题 > 大小限制 > 段落结构。
    *   原子性：图片和表格必须尽可能保持完整，且必须与其他文本通过子块分隔符隔离。

## 3. 需求理解 (Understanding)

*   与之前逻辑的区别：
    *   之前是递归切分（# -> ## -> ###），现在强调**先按一级标题切**，然后再处理大小问题。
    *   明确了原子内容必须**前后都有子块分隔符**（之前可能只是换行）。
    *   明确了原子内容超限时的具体处理策略（图片按段，表格按行）。

## 4. 技术实现策略 (Technical Strategy)

1.  **Regex Update**: 确保能匹配 `【图片主题：...】` 和 Markdown 表格。
2.  **Tokenizer**: 使用占位符（如 `<<IMG_0>>`, `<<TBL_1>>`）替换原子内容，记录其原始文本。
3.  **Level-1 Splitter**: 正则 `r"(?m)^# .*"` 切分。
4.  **Parent Refiner**: 遍历 Level-1 块，若 `len > parent_limit`，则使用 `RecursiveCharacterTextSplitter` 策略（按 `\n\n`, `\n` 等）将其切分为多个 `< parent_limit` 的块。
5.  **Sub Splitter**:
    *   输入：一个 Parent Block。
    *   操作：解析内容，识别普通文本和 Token。
    *   构建 Sub Blocks List：
        *   普通文本：按 `sub_limit` 切分。
        *   Token：
            *   若 `len(token_content) <= sub_limit`：独立作为一个 Sub Block。
            *   若 `len(token_content) > sub_limit`：调用特定拆分器（图片拆分器/表格拆分器）生成多个 Sub Blocks。
    *   输出：`sub_separator.join(sub_blocks)`。
6.  **Final Join**: `parent_separator.join(processed_parent_blocks)`.

## 5. 疑问澄清

*   **Q**: 一级标题切分后的内容，如果包含二级标题，是否需要保留层级结构？
    *   **A**: 需求描述中第4点说 "如果超过上限，再该块内部按段落结构拆分"。这暗示如果不超限，就保持原样（包含二级标题）。如果超限，主要目的是降维到大小限制以内，"段落结构"可以理解为优先按 `\n\n` 或 `##` 切分。我会保留优先按标题层级降维的逻辑。

## 6. 下一步计划

*   编写 `DESIGN_text_splitter_rewrite.md` 细化流程。
*   重写代码。
