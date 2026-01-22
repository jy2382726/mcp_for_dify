# 任务拆分文档：PDF分割Overlap功能

## 任务概览
实现 PDF 文档分割时的 Overlap 支持。

## 任务列表

### Task 1: 接口更新
- **文件**: `app/services/text_splitter_service.py`
- **内容**: 
    - 修改 `split` 方法签名，增加 `overlap: int = 0`。
    - 修改 `_split_pdf_text` 方法签名，增加 `overlap: int = 0`。
    - 在 `split` 中调用 `_split_pdf_text` 时传递 `overlap`。

### Task 2: 实现 Overlap 提取工具函数
- **文件**: `app/services/text_splitter_service.py`
- **内容**:
    - 实现 `_extract_overlap_suffix(self, text: str, overlap: int, tokens: Dict[str, str]) -> str`。
    - 处理 Token 解析和真实长度计算。
    - 处理边界情况。

### Task 3: 实现粗切合并逻辑
- **文件**: `app/services/text_splitter_service.py`
- **内容**:
    - 修改 `_coarse_split_and_merge` 签名，增加 `overlap: int = 0`。
    - 更新 `_split_pdf_text` 调用处。
    - 实现基于 overlap 的贪婪合并逻辑。

### Task 4: 验证
- **文件**: 新建 `tests/test_pdf_overlap.py` (或直接修改 main 进行测试)
- **内容**:
    - 验证纯文本 Overlap。
    - 验证带 Token 的 Overlap。
    - 验证结果长度和格式。

## 依赖关系
Task 1 -> Task 2 -> Task 3 -> Task 4
