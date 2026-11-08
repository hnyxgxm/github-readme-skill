#!/usr/bin/env python3
"""两个检查脚本共用的 Markdown 解析。

围栏和行内代码的识别规则只写这一份。以前两个脚本各抄一份正则，
改一处忘另一处，同一段 Markdown 在两个脚本里会得出相反的结论：
正文里 `` ``` `` 包住的示例块，一个脚本当成正文扫，另一个当成代码跳过。

这个文件不是入口，不要直接运行。
"""

from __future__ import annotations

import re

# 围栏：三个及以上反引号或波浪号。长度要配对，块内可以合法地出现更短的围栏。
FENCE_RE = re.compile(r"^(\s*)(`{3,}|~{3,})(.*)$")

# 行内代码允许用更长的反引号包住含反引号的内容：`` `code` ``。
# 固定写 `+[^`]*`+ 会把开头的两个反引号和中间的一个先配成一对，
# 真正要展示的链接或图片样例就漏回正文，被误判成断链、断图、死锚点。
INLINE_CODE_RE = re.compile(r"(?<!`)(`+)(?!`)(.*?)(?<!`)\1(?!`)")


def scan_fences(lines: list[str]) -> tuple[list[bool], bool]:
    """标记每一行是否在围栏内，并报告结束时有没有未闭合的围栏。

    按开围栏的反引号个数配对：```` 块里的 ``` 不会把它提前关掉。
    早期版本只看行首有没有反引号，遇到 patterns.md 那种四反引号嵌套块就会错位。
    """
    mask: list[bool] = []
    open_char = ""
    open_len = 0
    for line in lines:
        m = FENCE_RE.match(line)
        if not open_char:
            if m:
                open_char = m.group(2)[0]
                open_len = len(m.group(2))
                mask.append(True)
                continue
            mask.append(False)
            continue
        mask.append(True)
        # 闭合需要：同种字符、不短于开围栏、后面没有内容
        if m and m.group(2)[0] == open_char and len(m.group(2)) >= open_len and not m.group(3).strip():
            open_char, open_len = "", 0
    return mask, bool(open_char)


def fence_mask(lines: list[str]) -> list[bool]:
    return scan_fences(lines)[0]


def fence_unclosed(text: str) -> bool:
    return scan_fences(text.splitlines())[1]


def blank_fences(text: str) -> str:
    """把代码围栏内的内容换成空行，保留行号和换行位置。

    示例代码块里的图片引用是给人看的样板，不是真的引用，
    不剥掉会把文档自己的示例判成断链。
    """
    lines = text.splitlines(keepends=True)
    mask = fence_mask([ln.rstrip("\n") for ln in lines])
    return "".join(
        ("\n" if ln.endswith("\n") else "") if m else ln
        for ln, m in zip(lines, mask)
    )


def blank_inline_code(text: str) -> str:
    """把行内代码换成等长空格，保留行号和列位置。

    正文里写 `[CONTRIBUTING.md](CONTRIBUTING.md)` 是在讲链接怎么写，
    不是真链接；不剥掉会被判成断链。
    """
    return INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), text)


def strip_code(text: str) -> str:
    """去掉围栏和行内代码，避免把示例里的符号当成正文。

    行内代码必须一起剥：表格里写 `<img width="838">` 这种样例，
    不剥会被当成真的图片引用，双语对照就会报出假的"图片数不一致"。
    """
    return blank_inline_code(blank_fences(text))


def code_only(text: str) -> str:
    """只留围栏和行内代码里的内容。

    首屏判"有没有动作"时，散文里写"用 npm 安装"不算动作，
    代码块或行内代码里的 npm i 才算；反过来，代码块里的 JSON 输出、
    diff、配置也不该算，所以由调用方逐行对照命令名。
    """
    lines = text.splitlines()
    mask = fence_mask(lines)
    fenced = [ln for ln, in_fence in zip(lines, mask) if in_fence]
    prose = [ln for ln, in_fence in zip(lines, mask) if not in_fence]
    inline = [m.group(2) for ln in prose for m in INLINE_CODE_RE.finditer(ln)]
    return "\n".join(fenced + inline)
