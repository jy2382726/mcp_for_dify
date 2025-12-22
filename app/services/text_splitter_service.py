import re
import html
from typing import List, Tuple, Dict, Any
from app.core.logger import logger

class TextSplitterService:
    """
    文本分块服务
    统一文本分块处理架构（可复用，保持与三类现有实现一致）
    """

    def split(
        self,
        mode: str,
        content: str,
        parent_block_size: int = 1024,
        sub_block_size: int = 512,
        preview_url: str = "",
    ) -> Dict[str, Any]:
        """
        统一入口：根据 mode 调度对应的分块函数。

        参数：
        - mode: 取值 'pdf' | 'table' | 'image'（对应三类实现）
        - content: 待处理文本内容
        - parent_block_size: 父块大小上限
        - sub_block_size: 子块大小上限
        - preview_url: 当 mode=='image' 时必填的图片预览地址

        返回：包含处理后文本的字典 {"result": splited_content}
        """
        logger.info(f"TextSplitterService called with mode={mode}, parent_size={parent_block_size}, sub_size={sub_block_size}")

        if not isinstance(mode, str):
            raise TypeError("mode 必须是字符串类型")

        m = mode.strip().lower()
        splited_content = ""
        if m in ("pdf", "pdf_text"):
            splited_content = self._split_pdf_text(content, parent_block_size, sub_block_size)
        elif m in ("table", "md_table", "markdown"):
            splited_content = self._split_table_text(content, parent_block_size, sub_block_size)
        elif m in ("image", "img", "text_with_preview", "preview"):
            if not isinstance(preview_url, str) or not preview_url:
                raise ValueError("preview_url 不能为空（用于 image 模式）")
            splited_content = self._split_text_with_preview_link(
                content, preview_url, parent_block_size, sub_block_size
            )
        else:
            raise ValueError("mode 参数必须是 'pdf' | 'table' | 'image'")

        return {"result": splited_content}

    # -------- 业务接口 --------

    def _split_pdf_text(self, content: str, parent_block_size: int, sub_block_size: int) -> str:
        """PDF 文本分块：HTML 表格转 Markdown；父块末尾追加四个换行。"""
        if not isinstance(content, str):
            raise TypeError("content 必须是字符串类型")
        if not isinstance(parent_block_size, int) or not isinstance(sub_block_size, int):
            raise TypeError("parent_block_size 和 sub_block_size 必须是整数")

        converted = self._convert_html_tables_to_markdown(content)
        protected_content, tokens = self._protect_special_tokens(converted)

        effective_parent_size = max(1, parent_block_size)
        if sub_block_size < 1:
            sub_block_size = effective_parent_size

        units = self._split_into_units(protected_content, self.BOUNDARY_PDF)
        parent_blocks = self._join_units_with_limit(units, effective_parent_size)

        output_parts: List[str] = []
        for pblock in parent_blocks:
            body = self._apply_subblock_separators(pblock, sub_block_size)
            body = body.rstrip("\n") + "\n\n\n\n"
            output_parts.append(body)

        final_text = "".join(output_parts)
        return self._restore_special_tokens(final_text, tokens)

    def _split_table_text(self, content: str, parent_block_size: int, sub_block_size: int) -> str:
        """Markdown 表格文本分块：提取并复用表头；父块末尾追加四个换行。"""
        if not isinstance(content, str):
            raise TypeError("content 必须是字符串类型")
        if not isinstance(parent_block_size, int) or not isinstance(sub_block_size, int):
            raise TypeError("parent_block_size 和 sub_block_size 必须是整数")

        protected_content, tokens = self._protect_special_tokens(content)
        prefix_text, header_text, body_text = self._extract_md_header_prefix_and_body(
            protected_content
        )

        effective_parent_size = max(1, parent_block_size)
        if sub_block_size < 1:
            sub_block_size = effective_parent_size

        header_units = (
            self._split_into_units(header_text, self.BOUNDARY_GENERIC) if header_text else []
        )
        prefix_units = (
            self._split_into_units(prefix_text, self.BOUNDARY_GENERIC) if prefix_text else []
        )
        body_units = self._split_into_units(body_text, self.BOUNDARY_GENERIC)

        parent_blocks_units: List[List[Tuple[str, str]]] = []
        idx = 0
        first_block = True
        while idx < len(body_units) or first_block:
            current: List[Tuple[str, str]] = []
            current_len = 0

            if first_block and prefix_units:
                for seg, sep in prefix_units:
                    current.append((seg, sep))
                    current_len += len(seg) + len(sep)

            if header_units:
                for seg, sep in header_units:
                    current.append((seg, sep))
                    current_len += len(seg) + len(sep)

            while idx < len(body_units):
                seg, sep = body_units[idx]
                add_len = len(seg) + len(sep)
                if not current:
                    current.append((seg, sep))
                    current_len = add_len
                    idx += 1
                    continue
                if current_len + add_len <= effective_parent_size:
                    current.append((seg, sep))
                    current_len += add_len
                    idx += 1
                else:
                    break

            if current:
                parent_blocks_units.append(current)
            first_block = False
            if idx >= len(body_units) and not header_units and not prefix_units:
                break

        output_parts: List[str] = []
        for pblock_units in parent_blocks_units:
            body = self._apply_subblock_separators(pblock_units, sub_block_size)
            body = body.rstrip("\n") + "\n\n\n\n"
            output_parts.append(body)

        final_text = "".join(output_parts)
        return self._restore_special_tokens(final_text, tokens)

    def _split_text_with_preview_link(
        self, content: str, preview_url: str, parent_block_size: int, sub_block_size: int
    ) -> str:
        """纯文本分块：父块末尾追加图片链接地址与四个换行。"""
        if not isinstance(content, str) or not isinstance(preview_url, str):
            raise TypeError("content 和 preview_url 必须是字符串类型")
        if not isinstance(parent_block_size, int) or not isinstance(sub_block_size, int):
            raise TypeError("parent_block_size 和 sub_block_size 必须是整数")

        protected_content, tokens = self._protect_special_tokens(content)

        effective_parent_size = parent_block_size - len(preview_url)
        if effective_parent_size < 1:
            effective_parent_size = 1
        if sub_block_size < 1:
            sub_block_size = effective_parent_size

        units = self._split_into_units(protected_content, self.BOUNDARY_GENERIC)
        parent_blocks = self._join_units_with_limit(units, effective_parent_size)

        output_parts: List[str] = []
        for pblock in parent_blocks:
            body = self._apply_subblock_separators(pblock, sub_block_size)
            body = body.rstrip("\n") + f"\n图片链接地址：{preview_url}\n\n\n\n"
            output_parts.append(body)

        final_text = "".join(output_parts)
        return self._restore_special_tokens(final_text, tokens)

    # -------- 通用占位保护/恢复 --------

    TOKEN_PREFIX = "<<TB_TOKEN_"
    TOKEN_SUFFIX = ">>"

    def _protect_special_tokens(self, text: str) -> Tuple[str, List[str]]:
        tokens: List[str] = []

        def repl(m: re.Match) -> str:
            tokens.append(m.group(0))
            return f"{self.TOKEN_PREFIX}{len(tokens) - 1}{self.TOKEN_SUFFIX}"

        protected = re.sub(r"`[^`]+`", repl, text)
        protected = re.sub(r"https?://\S+", repl, protected)
        return protected, tokens

    def _restore_special_tokens(self, text: str, tokens: List[str]) -> str:
        for i, tok in enumerate(tokens):
            text = text.replace(f"{self.TOKEN_PREFIX}{i}{self.TOKEN_SUFFIX}", tok)
        return text

    # -------- HTML 表格 -> Markdown 表格（PDF 专用预处理） --------

    def _convert_html_tables_to_markdown(self, text: str) -> str:
        """将文本中的 HTML 表格转换为 Markdown 表格。

        规则：
        - 将 <table>..</table> 内的每个 <tr> 解析为一行；<th>/<td> 作为单元格
        - 第一行作为表头（即便是 <td>），随后添加分隔行
        - 其后各行作为数据行；按最大列数进行缺列补空
        - 对单元格文本：移除内部 HTML 标签、解码实体、去除首尾空白、转义竖线
        - 若解析失败，保留原始 HTML 表格
        """
        table_re = re.compile(r"<table\b[^>]*>(.*?)</table>", re.I | re.S)
        tr_re = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.I | re.S)
        cell_re = re.compile(r"<t(?:d|h)\b[^>]*>(.*?)</t(?:d|h)>", re.I | re.S)

        def html_table_to_md(table_html: str) -> str:
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
                return table_html

            col_count = max((len(r) for r in rows), default=0)
            if col_count == 0:
                return table_html

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
            if not md.endswith("\n"):
                md += "\n"
            return md

        def repl(m: re.Match) -> str:
            full = m.group(0)
            return html_table_to_md(full)

        return table_re.sub(repl, text)

    # -------- Markdown 表头提取（表格专用预处理） --------

    _MD_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
    _MD_SEP_CELL_RE = r"\s*:?\-{2,}:?\s*"
    _MD_SEP_RE = re.compile(rf"^\s*\|?{_MD_SEP_CELL_RE}(\|{_MD_SEP_CELL_RE})+\|?\s*$")

    def _is_md_table_row(self, line: str) -> bool:
        return bool(self._MD_ROW_RE.match(line.strip()))

    def _is_md_separator_row(self, line: str) -> bool:
        line = line.strip()
        if not line:
            return False
        return bool(self._MD_SEP_RE.match(line))

    def _extract_md_header_prefix_and_body(self, text: str) -> Tuple[str, str, str]:
        """提取 Markdown 表头（表头行 + 分隔行）、前置文本和数据体。

        返回 (prefix_text, header_text, body_text)。
        - prefix_text: 表头开始前的文本（保留原始换行），仅放入首块
        - header_text: Markdown 表头（两行），用于第二块起重复
        - body_text: 表数据部分（从第一行数据开始到结尾）
        若未检测到表头，返回 ("", "", 原文本)
        """
        if not text:
            return "", "", ""

        lines = text.splitlines(True)
        n = len(lines)
        header_start = None
        for i in range(n - 1):
            if self._is_md_table_row(lines[i]) and self._is_md_separator_row(lines[i + 1]):
                header_start = i
                break

        if header_start is None:
            return "", "", text

        prefix = "".join(lines[:header_start])
        header = "".join(lines[header_start : header_start + 2])
        body = "".join(lines[header_start + 2 :])
        return prefix, header, body

    # -------- 分段/拼合/渲染通用层 --------

    # 与三类实现一致的边界规则：
    # PDF 使用更严格的英文点号边界，避免拆分小数等
    BOUNDARY_PDF = re.compile(r"((?<!\d)(?<=\.)\s+(?=\s*[^0-9])|\n+|(?<=[。！？!?;；])\s*)")
    # 表格与图片实现使用的通用规则
    BOUNDARY_GENERIC = re.compile(r"((?<=\.)\s+|\n+|(?<=[。！？!?;；])\s*)")

    def _split_into_units(self, text: str, boundary: re.Pattern) -> List[Tuple[str, str]]:
        if not text:
            return []
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        parts = re.split(boundary, text)
        units: List[Tuple[str, str]] = []
        i = 0
        while i < len(parts):
            seg = parts[i]
            sep = parts[i + 1] if i + 1 < len(parts) else ""
            if seg or sep:
                units.append((seg, sep))
            i += 2
        return units

    def _join_units_with_limit(
        self, units: List[Tuple[str, str]], limit: int
    ) -> List[List[Tuple[str, str]]]:
        blocks: List[List[Tuple[str, str]]] = []
        current: List[Tuple[str, str]] = []
        current_len = 0

        for seg, sep in units:
            add_len = len(seg) + len(sep)
            if not current:
                current.append((seg, sep))
                current_len = add_len
                continue
            if current_len + add_len <= limit:
                current.append((seg, sep))
                current_len += add_len
            else:
                blocks.append(current)
                current = [(seg, sep)]
                current_len = add_len

        if current:
            blocks.append(current)
        return blocks

    def _render_units(
        self, units: List[Tuple[str, str]], strip_last_sep_newlines: bool = False
    ) -> str:
        out: List[str] = []
        n = len(units)
        for idx, (seg, sep) in enumerate(units):
            if strip_last_sep_newlines and idx == n - 1:
                sep = re.sub(r"\n+", "", sep)
            out.append(seg + sep)
        return "".join(out)

    def _apply_subblock_separators(
        self, parent_block_units: List[Tuple[str, str]], sub_limit: int
    ) -> str:
        subblocks = self._join_units_with_limit(parent_block_units, sub_limit)
        rendered = [self._render_units(sb, strip_last_sep_newlines=True) for sb in subblocks]
        return "\n\n\n".join(rendered).rstrip("\n")

# 单例实例
text_splitter_service = TextSplitterService()
