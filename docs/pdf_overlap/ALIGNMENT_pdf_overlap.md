# 任务对齐文档：PDF文档分割增加Overlap逻辑

## 1. 原始需求
用户要求修改 `/data/software/mcp_for_dify/app/services/text_splitter_service.py` 文件中针对 PDF 文档的分割逻辑。
具体要求：
1. 在做**粗切贪婪合并分块**（`_coarse_split_and_merge` 或相关流程）时，增加重叠度 `overlap` 的计算。
2. 根据输入的 `overlap` 大小计算每个父块的大小。
3. 将前一个块结尾的 `overlap` 长度的字符补充到当前块的首部。
4. 该逻辑只针对 PDF 分割模式，不影响 image 和 table 模式。
5. 文档和注释使用中文。

## 2. 现有系统分析
- **文件**: `app/services/text_splitter_service.py`
- **类**: `TextSplitterService`
- **入口方法**: `split(mode, content, parent_block_size, sub_block_size, ...)`
- **PDF处理方法**: `_split_pdf_text` -> `_coarse_split_and_merge`
- **当前逻辑**:
    - `split` 方法目前没有 `overlap` 参数。
    - `_coarse_split_and_merge` 按照一级标题 `#` 切分，然后贪婪合并，直到达到 `merge_limit` (`parent_block_size`)。
    - 目前没有重叠逻辑，块与块之间是断开的。

## 3. 需求理解与实现方案
### 3.1 接口变更
需要在 `split` 方法中增加 `overlap` 参数。
```python
async def split(
    self,
    mode: str,
    content: str,
    parent_block_size: int = 1024,
    sub_block_size: int = 512,
    parent_separator: str = "\n\n\n\n",
    sub_separator: str = "\n\n\n",
    preview_url: str = "",
    overlap: int = 0,  # 新增参数
) -> Dict[str, Any]:
```

### 3.2 逻辑变更
在 `_split_pdf_text` 中接收 `overlap` 并传递给 `_coarse_split_and_merge`。

在 `_coarse_split_and_merge` 中：
1. 接收 `overlap` 参数。
2. 在生成一个 `merged_block` 后，提取其尾部 `overlap` 长度的内容。
3. 将该内容作为下一个 `current_block` 的初始内容。
4. 长度检查 `_get_real_length(temp_text, tokens) <= merge_limit` 保持不变（这样自然保证了包含 overlap 的总长度不超过 `parent_block_size`）。

### 3.3 疑问与澄清
- **Token 处理**: 如果 overlap 切到了 Token（如图片或表格占位符 `<<ATOMIC_...>>`）中间怎么办？
    - `_get_real_length` 会计算 Token 的真实长度。
    - 如果 overlap 截取是基于字符的，可能会切断 Token ID。
    - **策略**: 必须确保 overlap 不会切断 Token ID。或者在计算 overlap 时，如果落在 Token 内部，需要包含整个 Token 或者放弃该 Token？
    - 考虑到 `_coarse_split_and_merge` 操作的是包含 Token ID 的字符串，简单的字符串切片 `block[-overlap:]` 极有可能破坏 Token ID（例如 `<<ATOMIC` 被切断）。
    - **改进方案**: 在提取 overlap 时，必须感知 Token。如果 overlap 边界落在 Token ID 中间，应该扩展到包含整个 Token ID，或者回退到不包含该 Token。
    - 鉴于 `_get_real_length` 是展开 Token 内容计算长度的，`overlap` 通常也是指“真实内容的重叠字符数”。
    - **复杂点**: `_coarse_split_and_merge` 处理的是带有 Token ID 的 `text`。`merge_limit` 是针对“真实长度”的。
    - 如果 `overlap` 也是针对真实长度的：我们需要找到 text 结尾处对应真实长度为 `overlap` 的子串。
    - 这是一个难点。

### 3.4 关键决策：Overlap 的计算方式
假设 `overlap` 为 50 字符。
我们需要从 `current_block` (带 Token ID) 的末尾，往前找，直到这部分内容的“真实长度” >= 50。
同时不能切断 Token ID。

**算法拟定**:
1. 反向遍历 `current_block` 的 Token/Text 结构。
2. 累加真实长度。
3. 当达到 `overlap` 时，截取对应的 `raw text`。

由于 `_coarse_split_and_merge` 是粗切，这里的块可能很大。
为了简化实现且保证安全：
- 我们实现一个辅助函数 `_get_overlap_suffix(text, overlap_size, tokens)`。
- 它返回 `text` 的一个后缀，该后缀的真实长度尽可能接近（且不小于？或者不大于？）`overlap_size`。
- 通常 overlap 是为了上下文连续，稍微多一点没关系，少了不太好。但也不能太多。
- 考虑到 Token 可能很长（比如大表格），如果 overlap 刚好落在表格里，是否要包含整个表格？表格可能几千字，远超 overlap。
- **调整**: 如果 Token 很大，且必须包含在 overlap 中，会导致下一个块起始就很大。
- 但 `overlap` 通常较小（如 50-200）。
- 如果 overlap 刚好在 Token 内部（图片/表格），最好是**不包含**该 Token，或者如果 Token 代表的内容确实需要重叠（如表格的一部分），但这里 Token 是原子的。
- **结论**: 这里的 Token (ATOMIC_IMG, ATOMIC_TAB) 是原子的，不可分割。如果 overlap 需要包含 Token 的一部分，实际上必须包含整个 Token。
- 如果 Token 真实长度 > overlap，包含它会导致 overlap 激增。
- **策略**: 
    - 尝试从后往前截取。
    - 遇到普通文本，按字符计数。
    - 遇到 Token，如果 `current_overlap + token_real_len <= overlap * tolerance` (比如 1.5倍)，则包含。否则停止截取（即 overlap 会少一些）。
    - 或者：严格保证 overlap，如果 Token 太大就跳过？
    - 简单做法：只对普通文本做 overlap。如果结尾是 Token，且 Token 很大，则 overlap 可能为空或很短。
    - **用户指令**: "增加重叠度overlap的计算...将前一个块结尾的overlap长度的字符补充到当前块的首部"。
    - 我将实现一个 `_extract_overlap_suffix` 方法，尽可能满足 overlap 长度，同时保持 Token 完整性。

## 4. 任务列表
1. 修改 `split` 接口，增加 `overlap` 参数。
2. 实现 `_extract_overlap_suffix` 辅助方法。
3. 修改 `_coarse_split_and_merge` 逻辑，在合并块时处理 overlap。
4. 验证 PDF 模式下的分块结果。
5. 确保 Image/Table 模式不受影响。
