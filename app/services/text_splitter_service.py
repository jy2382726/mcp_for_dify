import re
import html
import asyncio
from typing import List, Tuple, Dict, Any, Optional

class TextSplitterService:
    """
    文本分块服务
    统一文本分块处理架构（可复用，保持与三类现有实现一致）
    """
    
    # 内部预设大小限制
    INTERNAL_PARENT_SIZE = 1280
    INTERNAL_SUB_SIZE = 320

    async def split(
        self,
        mode: str,
        content: str,
        parent_block_size: int = 1024,
        sub_block_size: int = 512,
        parent_separator: str = "\n\n\n\n",
        sub_separator: str = "\n\n\n",
        preview_url: str = "",
    ) -> Dict[str, Any]:
        """
        统一入口：根据 mode 调度对应的分块函数。
        """
        if not isinstance(mode, str):
            raise TypeError("mode 必须是字符串类型")

        m = mode.strip().lower()
        splited_content = ""
        if m in ("pdf", "pdf_text"):
            splited_content = await self._split_pdf_text(
                content, 
                parent_block_size, 
                sub_block_size,
                parent_separator=parent_separator,
                sub_separator=sub_separator
            )
        elif m in ("table", "md_table", "markdown"):
            # 专用表格分块逻辑
            splited_content = await self._split_table_text(
                content, 
                parent_block_size, 
                sub_block_size,
                parent_separator=parent_separator,
                sub_separator=sub_separator
            )
        elif m in ("image", "img", "text_with_preview", "preview"):
            if not preview_url:
                raise ValueError("preview_url is required for image mode")
            splited_content = await self._split_image_text(
                content,
                parent_block_size,
                sub_block_size,
                parent_separator=parent_separator,
                sub_separator=sub_separator,
                preview_url=preview_url
            )
        else:
            raise ValueError("mode 参数必须是 'pdf' | 'table' | 'image'")

        if isinstance(splited_content, str) and parent_separator:
            escaped_sep = re.escape(parent_separator)
            fix_pattern = rf"#\s*{escaped_sep}\s*([^\n]+)"
            splited_content = re.sub(
                fix_pattern,
                lambda m: f"{parent_separator}# {m.group(1)}",
                splited_content,
            )

        return {"result": splited_content}

    # -------- 核心业务接口 (Rewrite) --------

    async def _split_table_text(
        self,
        content: str,
        parent_block_size: int,
        sub_block_size: int,
        parent_separator: str = "\n\n\n\n",
        sub_separator: str = "\n\n\n"
    ) -> str:
        """
        表格模式专用分块逻辑
        严格遵循输入的 parent_block_size 和 sub_block_size。
        """
        # 1. HTML -> Markdown
        content = await self._convert_html_tables_to_markdown(content)

        # 2. 提取表格结构
        lines = content.splitlines()
        header_idx = -1
        sep_idx = -1
        
        # 简单查找表格头
        for i, line in enumerate(lines):
            if line.strip().startswith("|"):
                if header_idx == -1:
                    header_idx = i
                elif sep_idx == -1 and set(line.strip()) <= {'|', '-', ' ', ':'}:
                    sep_idx = i
                    break
        
        # 如果找不到标准表格结构，回退到 PDF 逻辑
        if header_idx == -1 or sep_idx == -1:
            return await self._split_pdf_text(content, parent_block_size, sub_block_size, parent_separator, sub_separator)

        header_lines = lines[header_idx:sep_idx+1]
        header_str = "\n".join(header_lines)
        
        # 提取数据行
        data_rows = []
        # 保留表格前的文本 (可选，暂时忽略，聚焦表格)
        
        current_row_idx = sep_idx + 1
        while current_row_idx < len(lines):
            line = lines[current_row_idx]
            if line.strip().startswith("|"):
                data_rows.append(line)
            # 忽略空行或非表格行
            current_row_idx += 1
            
        # 3. 分块逻辑
        parent_blocks = []
        current_parent_subs = [] # 存储子块字符串
        current_sub_rows = []    # 存储当前子块的行
        
        def calculate_sub_block_len(rows):
            if not rows: return 0
            return sum(len(r) for r in rows) + len(rows) - 1

        def calculate_parent_block_len(sub_blocks):
            if not sub_blocks: return len(header_str)
            total = len(header_str) + 1 # header + newline
            for i, sub in enumerate(sub_blocks):
                total += len(sub)
                if i < len(sub_blocks) - 1:
                    total += len(sub_separator)
            return total

        # 遍历所有行
        for row in data_rows:
            temp_sub_rows = current_sub_rows + [row]
            temp_sub_len = calculate_sub_block_len(temp_sub_rows)
            
            # 判断当前子块是否是父块的第一个子块
            is_first_sub = (len(current_parent_subs) == 0)
            
            # 确定当前子块的有效大小限制
            # 如果是第一个子块，需要预留表头空间，以保证 visual chunk 符合 sub_block_size (参考 result.txt 行为)
            current_sub_limit = sub_block_size
            if is_first_sub:
                current_sub_limit -= (len(header_str) + 1)
                if current_sub_limit < 0: current_sub_limit = 0 # 保护

            if temp_sub_len <= current_sub_limit:
                # 满足子块限制，检查父块限制
                temp_parent_subs_if_added = []
                if current_parent_subs:
                    temp_parent_subs_if_added = current_parent_subs + ["\n".join(temp_sub_rows)]
                else:
                    temp_parent_subs_if_added = ["\n".join(temp_sub_rows)]
                
                if calculate_parent_block_len(temp_parent_subs_if_added) <= parent_block_size:
                    current_sub_rows.append(row)
                else:
                    # 加上这行后，子块虽然满足子块限制，但会导致父块超限
                    # 策略：结束当前子块（不含新行），结束父块，新行放入新父块的新子块
                    if current_sub_rows:
                        sub_str = "\n".join(current_sub_rows)
                        current_parent_subs.append(sub_str)
                        
                        parent_content = header_str + "\n" + sub_separator.join(current_parent_subs)
                        parent_blocks.append(parent_content)
                        current_parent_subs = []
                        
                        current_sub_rows = [row]
                    else:
                        # 单行就超父块？强制放入（保持行完整性）
                        current_sub_rows.append(row)
            else:
                # 超出子块限制
                # 结束当前子块（不含新行）
                if current_sub_rows:
                    sub_str = "\n".join(current_sub_rows)
                    
                    # 检查这个已完成的子块放入父块是否超限（理论上在添加行时已检查，但需再次确认）
                    temp_parent_subs = current_parent_subs + [sub_str]
                    if calculate_parent_block_len(temp_parent_subs) <= parent_block_size:
                        current_parent_subs.append(sub_str)
                        # 新行开启新子块
                        current_sub_rows = [row]
                        
                        # 检查新子块放入当前父块是否超限
                        # 注意：此时 is_first_sub 为 False
                        temp_parent_subs_new = current_parent_subs + ["\n".join(current_sub_rows)]
                        if calculate_parent_block_len(temp_parent_subs_new) > parent_block_size:
                            # 超限，结束父块
                            parent_content = header_str + "\n" + sub_separator.join(current_parent_subs)
                            parent_blocks.append(parent_content)
                            current_parent_subs = []
                            # current_sub_rows 保持不变，作为新父块的开始
                    else:
                        # 极其罕见：之前的行累积符合子块限制，但突然不符合父块限制？
                        # 逻辑上在 append(row) 时 checked check，所以这里应该是符合的。
                        # 除非是边界情况。为安全起见，若不符合则结束父块。
                        if current_parent_subs:
                            parent_content = header_str + "\n" + sub_separator.join(current_parent_subs)
                            parent_blocks.append(parent_content)
                            current_parent_subs = []
                        # 将当前 sub_str 作为新父块的第一个
                        current_parent_subs.append(sub_str)
                        current_sub_rows = [row]
                        
                        # 再检查新行
                        temp_parent_subs_new = current_parent_subs + ["\n".join(current_sub_rows)]
                        if calculate_parent_block_len(temp_parent_subs_new) > parent_block_size:
                             parent_content = header_str + "\n" + sub_separator.join(current_parent_subs)
                             parent_blocks.append(parent_content)
                             current_parent_subs = []
                else:
                    # 单行超子块限制
                    current_sub_rows.append(row)
        
        # 处理遗留
        if current_sub_rows:
            sub_str = "\n".join(current_sub_rows)
            temp_parent_subs = current_parent_subs + [sub_str]
            if calculate_parent_block_len(temp_parent_subs) <= parent_block_size:
                current_parent_subs.append(sub_str)
                parent_content = header_str + "\n" + sub_separator.join(current_parent_subs)
                parent_blocks.append(parent_content)
            else:
                if current_parent_subs:
                    parent_content = header_str + "\n" + sub_separator.join(current_parent_subs)
                    parent_blocks.append(parent_content)
                # 新父块
                parent_content = header_str + "\n" + sub_str
                parent_blocks.append(parent_content)
        elif current_parent_subs:
             parent_content = header_str + "\n" + sub_separator.join(current_parent_subs)
             parent_blocks.append(parent_content)
             
        return parent_separator.join(parent_blocks)

    async def _split_image_text(
        self,
        content: str,
        parent_block_size: int,
        sub_block_size: int,
        parent_separator: str = "\n\n\n\n",
        sub_separator: str = "\n\n\n",
        preview_url: str = ""
    ) -> str:
        """
        图片解析内容分块逻辑
        
        处理流程：
        1. 计算 mix_content = content + f"\n图片连接：{preview_url}"
        2. 按照输入的 parent_block_size 值匹配 mix_content 长度，如果长度超过 parent_block_size，
           那么从原始 content 尾部裁剪掉对应超出部分长度的内容。
        3. 将裁剪后的 content 与图片连接地址合并 content = content + f"\n图片连接：{preview_url}{parent_separator}"
        4. 对合并后的内容做子块拆分，分块前提条件是保证 preview_url 部分不可拆分。
        """
        # 1. 计算长度 & 2. 裁剪
        # 注意：这里计算 mix_content 长度时不包含 parent_separator，根据需求描述 1
        url_suffix_for_calc = f"\n图片连接：{preview_url}"
        current_len = len(content) + len(url_suffix_for_calc)
        
        if current_len > parent_block_size:
            excess = current_len - parent_block_size
            if excess < len(content):
                content = content[:-excess]
            else:
                content = ""

        # 3. 合并
        # 需求描述 3：content = content + f"\n图片连接：{preview_url}{parent_separator}"
        protected_suffix = f"\n图片连接：{preview_url}{parent_separator}"
        
        # 4. 子块拆分
        # 构造一个 Token 来保护后缀不被拆分
        # 注意：Token 格式必须匹配 _split_into_sub_blocks 中的正则 r"(<<ATOMIC_\w+_\d+>>)"
        token_key = "<<ATOMIC_PREVIEW_URL_SECTION_0>>"
        tokens = {token_key: protected_suffix}
        text_with_token = content + token_key
        
        # 获取有效限制
        _, _, s_target, s_max = await self._determine_effective_limits(parent_block_size, sub_block_size)
        
        # 调用子块拆分
        # _split_into_sub_blocks 会识别 <<ATOMIC_...>> 并保留（因为 key 不含 IMG/TAB，且长度超限时 fallback 为保留）
        # 如果 protected_suffix 长度本身小于 s_max，则更是直接保留。
        sub_blocks = await self._split_into_sub_blocks(text_with_token, s_target, s_max, tokens)
        
        # 过滤空块
        valid_subs = [s.strip() for s in sub_blocks if s.strip()]
        
        # 连接并返回
        return sub_separator.join(valid_subs)

    async def _split_pdf_text(
        self, 
        content: str, 
        parent_block_size: int, 
        sub_block_size: int,
        parent_separator: str = "\n\n\n\n",
        sub_separator: str = "\n\n\n"
    ) -> str:
        """PDF 文本分块：重写逻辑"""
        
        # 1. 确定切分限制
        p_target, p_max, s_target, s_max = await self._determine_effective_limits(parent_block_size, sub_block_size)
        
        # 2. HTML 表格转 Markdown
        content = await self._convert_html_tables_to_markdown(content)
        
        # 3. Tokenize (原子保护)
        # 将图片和表格替换为 Token ID，并存储在 tokens map 中
        # 注意：这里我们只做标记，不做切分（除非超限）。但根据新需求，
        # 如果超子块限制，要在后面切分。这里我们先识别出来。
        content, tokens = await self._tokenize_content(content)
        
        # 4. 一级粗切 + 贪婪合并
        # 保证每个分块结尾有一个父块分隔符 (在 Join 时处理)
        coarse_blocks = await self._coarse_split_and_merge(content, p_target, tokens)
        
        # 5. 父块细化 (Parent Refinement)
        # 校验粗切的每个分块是否符合父块大小上限，如果超过上限，再该块内部按段落结构拆分出多个父块。
        final_parent_blocks = []
        for block in coarse_blocks:
            refined = await self._refine_parent_block(block, p_target, p_max, tokens)
            final_parent_blocks.extend(refined)
            
        # 6. 子块拆分 (Sub Block Splitting)
        # 在每个父块的基础上拆分子块
        processed_parent_blocks = []
        for p_block in final_parent_blocks:
            sub_blocks = await self._split_into_sub_blocks(p_block, s_target, s_max, tokens)
            
            # 过滤空块
            valid_subs = [s.strip() for s in sub_blocks if s.strip()]
            if valid_subs:
                # 子块连接
                processed_parent_blocks.append(sub_separator.join(valid_subs))
                
        # 7. 父块连接
        final_text = parent_separator.join(processed_parent_blocks)

        if parent_separator:
            escaped_sep = re.escape(parent_separator)
            fix_pattern = rf"#\s*{escaped_sep}\s*([^\n]+)"
            final_text = re.sub(
                fix_pattern,
                lambda m: f"{parent_separator}# {m.group(1)}",
                final_text,
            )
        
        # 8. 还原 Token (如果还有遗留的)
        # 注意：子块拆分时可能已经把 Token ID 变回内容了，或者我们留到最后统一变回。
        # 建议在子块拆分阶段就处理好超限问题，并还原成文本，
        # 这样 Join 后的文本就是最终文本。
        # 但为了防止某些 Token 在中间过程中被意外修改，我们通常保留 ID 到最后。
        # 不过根据设计，_split_into_sub_blocks 返回的已经是还原后的文本片段。
        return final_text

    # -------- 辅助方法 --------

    async def _determine_effective_limits(self, user_parent: int, user_sub: int) -> Tuple[int, int, int, int]:
        user_parent = max(1, user_parent)
        user_sub = max(1, user_sub)
        
        p_target = user_parent if user_parent < self.INTERNAL_PARENT_SIZE else self.INTERNAL_PARENT_SIZE
        p_max = user_parent
        
        s_target = user_sub if user_sub < self.INTERNAL_SUB_SIZE else self.INTERNAL_SUB_SIZE
        s_max = user_sub
        
        return p_target, p_max, s_target, s_max

    async def _convert_html_tables_to_markdown(self, text: str) -> str:
        """将文本中的 HTML 表格转换为 Markdown 表格。"""
        table_re = re.compile(r"<table\b[^>]*>(.*?)</table>", re.I | re.S)
        tr_re = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.I | re.S)
        cell_re = re.compile(r"<t(?:d|h)\b[^>]*>(.*?)</t(?:d|h)>", re.I | re.S)

        def html_table_to_md(match) -> str:
            table_html = match.group(1)
            rows_html = tr_re.findall(table_html)
            rows: List[List[str]] = []
            for rh in rows_html:
                cells = cell_re.findall(rh)
                row: List[str] = []
                for c in cells:
                    raw = re.sub(r"<[^>]+>", "", c)
                    raw = html.unescape(raw)
                    raw = raw.strip()
                    raw = raw.replace("|", "\\|")
                    row.append(raw)
                if row:
                    rows.append(row)

            if not rows:
                return match.group(0)

            col_count = max((len(r) for r in rows), default=0)
            if col_count == 0:
                return match.group(0)

            norm_rows: List[List[str]] = []
            for r in rows:
                if len(r) < col_count:
                    r = r + [""] * (col_count - len(r))
                norm_rows.append(r)

            header = norm_rows[0]
            data_rows = norm_rows[1:]

            header_line = "| " + " | ".join(header) + " |"
            sep_line = "| " + " | ".join(["----------"] * col_count) + " |"
            data_lines = ["| " + " | ".join(dr) + " |" for dr in data_rows]

            md = "\n".join([header_line, sep_line] + data_lines)
            return "\n\n" + md + "\n\n" # Ensure separation

        return table_re.sub(html_table_to_md, text)

    async def _tokenize_content(self, text: str) -> Tuple[str, Dict[str, str]]:
        """将图片和表格内容替换为 Token ID"""
        tokens = {}
        
        # 1. 图片处理
        def img_replacer(match):
            full_text = match.group(0)
            token_id = f"<<ATOMIC_IMG_{len(tokens)}>>"
            tokens[token_id] = full_text
            return token_id # 暂时只返回 ID，不强制换行，后续 split 时处理
            
        text = re.sub(r"【(?:图片主题|图片解析内容).*?】", img_replacer, text, flags=re.DOTALL)
        
        # 2. 表格处理
        def table_replacer(match):
            full_text = match.group(0)
            token_id = f"<<ATOMIC_TAB_{len(tokens)}>>"
            tokens[token_id] = full_text
            return token_id
            
        text = re.sub(r"(?:^\s*\|.*\|\s*$\n?)+", table_replacer, text, flags=re.MULTILINE)
        
        return text, tokens

    async def _coarse_split_and_merge(self, text: str, merge_limit: int, tokens: Dict[str, str]) -> List[str]:
        """
        按一级标题 # 切分，然后进行贪婪合并。
        1. 识别 (?=^# ) 或 (?=\n# ) 进行切分。
        2. 遍历切分后的块，进行合并，直到达到 merge_limit。
        3. 使用 _get_real_length 计算真实长度（展开 Token）。
        """
        # 1. Split using lookahead to keep the delimiter with the following block
        # Pattern: Split BEFORE a newline followed by # and space, OR start of string followed by # and space
        pattern = r"(?=(?:^|\n)# )"
        parts = re.split(pattern, text)
        
        merged_blocks = []
        current_block = ""
        
        for part in parts:
            if not part: continue
            
            # Check if merging exceeds limit
            # Calculate length of (current + part)
            temp_text = current_block + part
            if await self._get_real_length(temp_text, tokens) <= merge_limit:
                current_block += part
            else:
                # Exceeds limit, emit current_block if exists
                if current_block:
                    merged_blocks.append(current_block)
                current_block = part
        
        if current_block:
            merged_blocks.append(current_block)
            
        return merged_blocks

    async def _get_real_length(self, text: str, tokens: Dict[str, str]) -> int:
        """计算包含 Token 的文本真实长度"""
        length = 0
        last_pos = 0
        for match in re.finditer(r"<<ATOMIC_\w+_\d+>>", text):
            # 加之前文本长度
            length += len(text[last_pos:match.start()])
            # 加 Token 真实内容长度
            token_id = match.group(0)
            if token_id in tokens:
                length += len(tokens[token_id])
            else:
                length += len(token_id)
            last_pos = match.end()
        length += len(text[last_pos:])
        return length

    async def _refine_parent_block(self, block: str, target: int, max_limit: int, tokens: Dict[str, str]) -> List[str]:
        """
        父块细化：如果超过上限，内部按段落结构拆分。
        """
        real_len = await self._get_real_length(block, tokens)
        if real_len <= max_limit:
            return [block]
            
        # 超过上限，需要拆分。
        # 优先级：二级标题 > 三级标题 > 段落 (\n\n) > 换行 (\n)
        separators = ["\n## ", "\n### ", "\n#### ", "\n\n", "\n", " "]
        
        # 使用递归切分逻辑 (RecursiveCharacterSplitter 思想)
        refined_blocks = await self._recursive_split(block, target, max_limit, tokens, separators)
        refined_blocks = await self._merge_broken_markdown_headers(refined_blocks)
        return refined_blocks

    async def _merge_broken_markdown_headers(self, blocks: List[str]) -> List[str]:
        """
        合并在父块切分过程中被拆开的 Markdown 标题前缀。

        Args:
            blocks: 细化后得到的父块列表

        Returns:
            List[str]: 经过标题前缀修复后的父块列表
        """
        if not blocks:
            return blocks

        fixed_blocks: List[str] = []
        idx = 0

        while idx < len(blocks):
            current = blocks[idx]

            if idx < len(blocks) - 1:
                nxt = blocks[idx + 1]

                current_stripped = current.rstrip("\r\n")
                if current_stripped:
                    last_line = current_stripped.splitlines()[-1]
                else:
                    last_line = ""

                if re.fullmatch(r"#+", last_line.strip()):
                    merged = current + nxt
                    blocks[idx + 1] = merged
                    idx += 1
                    continue

            fixed_blocks.append(current)
            idx += 1

        return fixed_blocks

    async def _recursive_split(self, text: str, target: int, max_limit: int, tokens: Dict[str, str], separators: List[str]) -> List[str]:
        real_len = await self._get_real_length(text, tokens)
        if real_len <= max_limit: # 使用 max_limit 作为硬性停止条件
            return [text]
            
        if not separators:
            return [text] # 无法再分，只能返回
            
        separator = separators[0]
        next_separators = separators[1:]
        
        # 重新实现一个更简单的逻辑：

        # 1. Split text by separator.
        # 2. Re-attach separator to the correct side (usually left of the next part, or right of current).
        #    For headers "\n## ", it effectively starts a new section.
        #    So "Content\n## Header" -> ["Content", "## Header"]
        
        split_pattern = f"({re.escape(separator)})"
        parts = re.split(split_pattern, text)
        # parts: ["Content", "\n## ", "Header...", "\n## ", "Header2..."]
        
        good_blocks = []
        current_buf = ""
        
        for part in parts:
            if not part: continue
            
            # 检查 buffer + part 是否超限
            # 注意：这里我们还没合并 separator。
            # 逻辑：current_buf 累积，直到 > target (或 max)。
            
            temp = current_buf + part
            if await self._get_real_length(temp, tokens) <= target:
                current_buf += part
            else:
                # current_buf 已经够了 (或者加上 part 就爆了)
                if current_buf:
                    good_blocks.append(current_buf)
                current_buf = part
        
        if current_buf:
            good_blocks.append(current_buf)
            
        # 递归检查生成的 blocks
        result = []
        for blk in good_blocks:
            if await self._get_real_length(blk, tokens) > max_limit:
                 result.extend(await self._recursive_split(blk, target, max_limit, tokens, next_separators))
            else:
                 result.append(blk)
                 
        return result

    async def _split_into_sub_blocks(self, parent_block: str, sub_target: int, sub_max: int, tokens: Dict[str, str]) -> List[str]:
        """
        将父块拆分为子块。
        核心逻辑：
        1. 识别 Token。
        2. Token 必须独立（前后有子块分隔符）。
        3. Token 若超限，需拆分。
        4. 普通文本按 sub_limit 拆分。
        """
        # 使用正则切分 Token
        # pattern: (<<ATOMIC_.*?>>)
        parts = re.split(r"(<<ATOMIC_\w+_\d+>>)", parent_block)
        
        sub_blocks = []
        
        for part in parts:
            if not part: continue
            
            if part.startswith("<<ATOMIC_") and part.endswith(">>"):
                # 是 Token
                token_content = tokens.get(part, "")
                if not token_content: continue # Should not happen
                
                if len(token_content) <= sub_max:
                    # 未超限，直接作为独立子块
                    sub_blocks.append(token_content)
                else:
                    # 超限，需要拆分
                    if "ATOMIC_IMG" in part:
                        sub_blocks.extend(await self._split_atomic_image(token_content, sub_max))
                    elif "ATOMIC_TAB" in part:
                        sub_blocks.extend(await self._split_atomic_table(token_content, sub_max))
                    else:
                        sub_blocks.append(token_content) # Fallback
            else:
                # 是普通文本
                # 递归切分
                text_chunks = await self._split_normal_text(part, sub_target, sub_max)
                sub_blocks.extend(text_chunks)
                
        return sub_blocks

    async def _split_normal_text(self, text: str, target: int, max_limit: int) -> List[str]:
        """普通文本切分"""
        if len(text) <= max_limit:
            return [text]
            
        separators = ["\n\n", "\n", "。", "！", "？", "；", ";", " ", ""]
        # 简化的递归切分
        for sep in separators:
            if sep == "":
                # 强制切分
                return [text[i:i+target] for i in range(0, len(text), target)]
            
            if sep in text:
                parts = text.split(sep)
                chunks = []
                current = ""
                for p in parts:
                    if len(current) + len(p) + len(sep) <= target:
                        current += (sep if current else "") + p
                    else:
                        if current: chunks.append(current)
                        current = p
                if current: chunks.append(current)
                
                # Check valid
                final = []
                valid = True
                for c in chunks:
                    if len(c) > max_limit:
                        valid = False
                        break
                
                if valid:
                    return chunks
                # else continue next sep
        
        return [text] # Should not reach here if sep="" exists

    async def _split_atomic_image(self, content: str, limit: int) -> List[str]:
        """
        超大图片内容拆分：
        【图片主题：...】
        按段落拆分。
        """
        # 去除首尾 【 】
        inner = content[1:-1]
        
        # 尝试保留前缀结构
        # 简单按换行切
        lines = inner.split('\n')
        chunks = []
        current = "【图片内容(分段):"
        
        for line in lines:
            if len(current) + len(line) + 1 > limit:
                current += "】"
                chunks.append(current)
                current = "【图片内容(续):" + line
            else:
                current += "\n" + line
                
        current += "】"
        chunks.append(current)
        return chunks

    async def _split_atomic_table(self, content: str, limit: int) -> List[str]:
        """
        超大表格拆分：
        按行拆分，保留表头。
        """
        lines = content.strip().split('\n')
        if len(lines) < 2: return [content]
        
        header = lines[0]
        sep = lines[1]
        rows = lines[2:]
        
        chunks = []
        current_rows = []
        base_len = len(header) + len(sep) + 2 # +2 for newlines
        current_len = base_len
        
        for row in rows:
            if current_len + len(row) + 1 > limit:
                if current_rows:
                    table_str = "\n".join([header, sep] + current_rows)
                    chunks.append(table_str)
                current_rows = [row]
                current_len = base_len + len(row) + 1
            else:
                current_rows.append(row)
                current_len += len(row) + 1
                
        if current_rows:
            table_str = "\n".join([header, sep] + current_rows)
            chunks.append(table_str)
            
        return chunks


text_splitter_service = TextSplitterService()


if __name__ == "__main__":
    async def main():
        # 读取demo.txt
        try:
            with open("/root/code/mcp_for_dify/demo/demo.txt", "r", encoding="utf-8") as f:
                demo_text = f.read()
        except FileNotFoundError:
            print("Demo file not found, using placeholder text.")
            demo_text = "Title\n# Header 1\nContent under header 1.\n\n# Header 2\nContent under header 2."
            
        # 处理 demo.txt 中的转义换行符 (因为 demo.txt 内容似乎来自 JSON 字符串)
        demo_text = demo_text.replace("\\n", "\n")
            
        # 初始化服务
        service = TextSplitterService()
        
        # 测试切分
        result = await service.split(
            mode="pdf",
            content=demo_text,
            parent_block_size=1536,
            sub_block_size=768,
            parent_separator="/--P--/",
            sub_separator="/--S--/",
        )
        
        res_text = result["result"]
        
        print(f"Total Length: {len(res_text)}")
        print("-" * 20 + " RESULT START " + "-" * 20)
        print(res_text)
        print("-" * 20 + " RESULT END " + "-" * 20)
        
        # 验证分隔符
        p_sep_count = res_text.count("\n\n\n\n")
        s_sep_count = res_text.count("\n\n\n")
        print(f"Parent Separator Count: {p_sep_count}")
        print(f"Sub Separator Count: {s_sep_count}")

    asyncio.run(main())
