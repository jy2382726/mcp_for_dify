# 架构设计文档：PDF分割Overlap功能

## 1. 核心变更
主要修改 `TextSplitterService` 类，引入 `overlap` 参数并在 PDF 粗切阶段应用。

## 2. 详细设计

### 2.1 接口定义
`split` 方法增加 `overlap` 参数，默认值为 0。

```python
async def split(..., overlap: int = 0) -> Dict[str, Any]
```

### 2.2 数据流
1. 用户调用 `split(mode="pdf", ..., overlap=100)`
2. `split` 调用 `_split_pdf_text(..., overlap=100)`
3. `_split_pdf_text` 调用 `_coarse_split_and_merge(..., overlap=100)`
4. `_coarse_split_and_merge` 内部使用 `_extract_overlap_suffix` 计算重叠部分。

### 2.3 `_extract_overlap_suffix` 算法
该函数负责从带有 Token ID 的文本中提取指定真实长度的后缀。

输入:
- `text`: 包含 Token ID 的字符串
- `overlap_size`: 目标重叠字符数
- `tokens`: Token ID 到真实内容的映射

输出:
- `suffix`: 满足重叠要求的后缀字符串（包含完整的 Token ID）

逻辑:
1. 如果 `overlap_size <= 0` 或 `text` 为空，返回 `""`。
2. 解析 `text` 结构，将其分解为 (Type, Content, RealLength) 的列表。
   - Type: TEXT 或 TOKEN
3. 反向遍历列表，累加真实长度 `accumulated_len`。
4. 收集需要保留的片段。
   - 如果是 TOKEN: 
     - 检查 `token_real_len + accumulated_len` 是否显著超过 `overlap_size` (例如 > overlap * 1.2)。
     - 如果不过分，保留整个 Token。
     - 如果过大，放弃该 Token (重叠部分将小于 `overlap_size`)，并停止。
   - 如果是 TEXT:
     - 计算需要截取的字符数: `need = overlap_size - accumulated_len`。
     - 如果 `text_len <= need`，保留整段。
     - 如果 `text_len > need`，截取后 `need` 个字符。
5. 拼接片段返回。

### 2.4 `_coarse_split_and_merge` 逻辑更新
```python
async def _coarse_split_and_merge(self, text: str, merge_limit: int, tokens: Dict[str, str], overlap: int = 0) -> List[str]:
    # ... 切分 parts ...
    
    merged_blocks = []
    current_block = "" # 初始为空
    
    for part in parts:
        if not part: continue
        
        # 尝试添加
        temp_text = current_block + part
        if await self._get_real_length(temp_text, tokens) <= merge_limit:
            current_block += part
        else:
            # 超限，保存当前块
            if current_block:
                merged_blocks.append(current_block)
                
                # 计算 overlap
                overlap_text = await self._extract_overlap_suffix(current_block, overlap, tokens)
                
                # 新块以 overlap 开始
                current_block = overlap_text + part
            else:
                # 理论上不会发生，除非 part 本身 > limit 且 current_block 为空
                current_block = part
    
    if current_block:
        merged_blocks.append(current_block)
        
    return merged_blocks
```

## 3. 影响范围
- 仅影响 PDF 模式 (`mode="pdf"` 或 `"pdf_text"`).
- 不影响 Image / Table 模式。
- `split` 接口兼容现有调用（`overlap` 默认为 0）。

## 4. 验证计划
- 单元测试：
    - 基本文本重叠。
    - 包含 Token 的文本重叠。
    - Overlap 大于 block size (边缘情况)。
    - Overlap 为 0。

