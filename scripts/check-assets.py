#!/usr/bin/env python3
"""检查 README 引用的图和文件会不会在 GitHub 上坏掉。

只判"会不会崩"，不判"好不好看"。审美归审稿人，会崩的归脚本。

用法:
    python3 <技能目录>/scripts/check-assets.py README.md
    python3 <技能目录>/scripts/check-assets.py README.md README.en.md
    python3 <技能目录>/scripts/check-assets.py README.md --column-width 760
    python3 <技能目录>/scripts/check-assets.py README.md --check-remote
    python3 <技能目录>/scripts/check-assets.py --selftest
    python3 <技能目录>/scripts/check-assets.py README.md --json

注意：脚本要在目标仓库里跑，但脚本自身要按绝对路径调用。
<技能目录> 是这份 Skill 的安装位置，例如 ~/.claude/skills/github-readme-skill。
直接写 scripts/check-assets.py 只在本仓库内成立，装成 Skill 后工作目录是别人的仓库，会找不到文件。

退出码: 0 = 没有 FAIL, 1 = 有 FAIL, 2 = 用法或路径错误

判据来源分三类，输出里逐条标注:
  [实测] rendering.md 里在 Chrome 156 + 线上 GitHub 量出来的数
  [官方] 平台响应头或官方文档
  [经验] 工程阈值，不是平台规定，可自行调整
"""

from __future__ import annotations

import json
import os
import re
import shutil
import struct
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote, urlparse

# 技能安装目录，用来定位自测样本
SKILL_DIR = Path(__file__).resolve().parent.parent

# 围栏和行内代码的识别规则与 check-text.py 共用同一份，
# 两个脚本各抄一份时，改一处忘另一处就会让同一段 Markdown 得出相反结论。
# 关掉字节码缓存：技能可能装在只读目录，也不该往安装目录里写 __pycache__。
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from readme_md import strip_code  # noqa: E402

# ---------------------------------------------------------------- 判据常量

# [实测] references/rendering.md：桌面 1280/1440/1920 三档正文列均为 838px，
# 窄屏 390 视口为 324px。验收取 838。
# 换平台或换主题时要重量，用 --column-width 覆盖，不要改这里。
COLUMN_WIDTH = 838

# [实测] 表格单元格左右内边距合计约 27px，声明 width=410 的图实际渲染 392.3px。
# 并排两张时每张按 392 算，不是 410。
TABLE_CELL_WIDTH = 392

# [经验] 图内文字渲染后低于此值时，中文在 1x 屏上明显吃力。
# 本仓库没有做不同字号的可读性实验，按经验值对待。
MIN_RENDERED_FONT_PX = 12.0
WARN_RENDERED_FONT_PX = 14.0

# [实测] font-size 未声明时的 SVG 初始值。
DEFAULT_SVG_FONT_SIZE = 16.0

# [官方] GitHub 文件大小：git 50 MiB 起警告、100 MiB 直接阻止。
# 通过网页上传时按类型分档：图片和 GIF 10 MiB，视频免费计划 10 MiB、付费 100 MiB，
# 其他文件 25 MiB。出处：docs.github.com「Attaching files」。
HARD_FILE_LIMIT = 100 * 1024 * 1024
WEB_UPLOAD_IMAGE_LIMIT = 10 * 1024 * 1024
WEB_UPLOAD_LIMIT = 25 * 1024 * 1024

# 网页上传按图片档算的类型；其余（视频、附件）走 25 MiB。
IMAGE_KINDS = {"svg", "gif", "png", "jpg", "jpeg", "webp", "avif", "bmp"}

# [经验] 首屏图的加载预算，分两级。与平台限制无关，平台阻止线见 HARD_FILE_LIMIT。
GIF_TARGET_BYTES = 2 * 1024 * 1024     # 超过它，首屏开始让人等
GIF_HEAVY_BYTES = 5 * 1024 * 1024      # 超过它，移动网络下明显拖慢
SOFT_SVG_BYTES = 300 * 1024

# [官方] raw.githubusercontent.com 的响应头:
#   content-security-policy: default-src 'none'; style-src 'unsafe-inline'; sandbox
# 作为 <img> 加载的 SVG 是独立文档，受此约束：除内联样式外一切外部资源都被拦。
# 已用 CDP 验证：img 内的 @import 字体请求不会发出。
EXTERNAL_RESOURCE_PATTERNS = [
    (re.compile(r"@import\s", re.I), "@import 外部样式表"),
    (re.compile(r"@font-face", re.I), "@font-face 远程字体"),
    (re.compile(r"url\(\s*['\"]?(?:https?:)?//", re.I), "url() 指向远程资源"),
    (re.compile(r"<script", re.I), "<script> 脚本"),
    (re.compile(r"""(?:xlink:)?href\s*=\s*['"]https?://""", re.I), "外部链接引用"),
    (re.compile(r"<image[^>]*\b(?:xlink:)?href\s*=\s*['\"](?:https?:)?//", re.I), "<image> 外链图片"),
]

# [官方] 平台会拦掉一切远程字体，只会回落到本机字体。
SYSTEM_FONT_HINTS = {
    "system-ui", "-apple-system", "blinkmacsystemfont", "segoe ui", "roboto",
    "helvetica", "helvetica neue", "arial", "sans-serif", "serif", "monospace",
    "ui-sans-serif", "ui-monospace", "ui-serif", "noto sans", "noto sans cjk sc",
    "pingfang sc", "hiragino sans gb", "microsoft yahei", "simhei", "simsun",
    "source han sans", "wenquanyi micro hei", "menlo", "consolas", "courier new",
    "sf mono", "sf pro text", "sf pro display", "georgia", "times new roman",
    "verdana", "tahoma", "trebuchet ms", "emoji", "cursive", "fantasy",
}
# 注意 "inter" 这类 Web Font 不在此列：它们不是任何系统的默认字体，
# 用户没装就 fallback，按系统字体栈处理会漏掉排版错位。

# 围栏和行内代码怎么认，见同目录 readme_md.py。两个脚本共用一份规则，
# 各抄一份时改一处忘另一处，同一段 Markdown 会得出相反结论。


# ---------------------------------------------------------------- 数据结构

@dataclass
class Finding:
    level: str          # FAIL / WARN / INFO
    file: str
    where: str
    detail: str
    basis: str          # 判据来源

    def render(self) -> str:
        icon = {"FAIL": "✗", "WARN": "!", "INFO": "·"}[self.level]
        return f"  {icon} [{self.level}] {self.where}: {self.detail}  ({self.basis})"


@dataclass
class Asset:
    raw: str
    path: Path | None         # 本地路径，外链为 None
    decl_width: int | None
    alt: str
    in_table: bool
    line: int
    kind: str = ""            # svg / gif / png / jpg / webp / other
    intrinsic: tuple[int, int] | None = None
    size_bytes: int = 0
    exists: bool = False
    case_hint: str = ""       # 大小写不符时记下真实文件名
    unverified: bool = False  # 以 / 开头又找不到仓库根，只能提示不能判定


@dataclass
class Report:
    assets: list[Asset] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    scanned_files: list[str] = field(default_factory=list)

    def add(self, level, file, where, detail, basis):
        self.findings.append(Finding(level, file, where, detail, basis))

    @property
    def fails(self):
        return [f for f in self.findings if f.level == "FAIL"]

    @property
    def warns(self):
        return [f for f in self.findings if f.level == "WARN"]


# ---------------------------------------------------------------- 图片尺寸解析

def _png_size(data: bytes) -> tuple[int, int] | None:
    if data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR":
        w, h = struct.unpack(">II", data[16:24])
        return w, h
    return None


def _gif_size(data: bytes) -> tuple[int, int] | None:
    if data[:3] in (b"GIF",) and data[3:6] in (b"87a", b"89a"):
        w, h = struct.unpack("<HH", data[6:10])
        return w, h
    return None


def _jpeg_size(data: bytes) -> tuple[int, int] | None:
    if data[:2] != b"\xff\xd8":
        return None
    i = 2
    while i < len(data) - 9:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        seg_len = struct.unpack(">H", data[i + 2:i + 4])[0]
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            h, w = struct.unpack(">HH", data[i + 5:i + 9])
            return w, h
        i += 2 + seg_len
    return None


def _webp_size(data: bytes) -> tuple[int, int] | None:
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return None
    fmt = data[12:16]
    try:
        if fmt == b"VP8X":
            w = 1 + int.from_bytes(data[24:27], "little")
            h = 1 + int.from_bytes(data[27:30], "little")
            return w, h
        if fmt == b"VP8 ":
            w, h = struct.unpack("<HH", data[26:30])
            return w & 0x3FFF, h & 0x3FFF
        if fmt == b"VP8L":
            b = data[21:25]
            w = 1 + (((b[1] & 0x3F) << 8) | b[0])
            h = 1 + (((b[3] & 0x0F) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6))
            return w, h
    except (IndexError, struct.error):
        return None
    return None


def raster_size(path: Path) -> tuple[int, int] | None:
    try:
        head = path.read_bytes()[:65536]
    except OSError:
        return None
    for parser in (_png_size, _gif_size, _jpeg_size, _webp_size):
        got = parser(head)
        if got:
            return got
    return None


def svg_info(text: str) -> dict:
    """返回 viewBox 宽高、固有宽高、最小字号、字体声明、有无 title/desc/背景。"""
    info: dict = {
        "viewbox": None, "attr_w": None, "attr_h": None,
        "font_sizes": [], "font_families": [], "has_title": False,
        "has_desc": False, "has_bg_rect": False,
    }
    m = re.search(r"<svg\b[^>]*>", text, re.I | re.S)
    if not m:
        return info
    tag = m.group(0)
    vb = re.search(r"viewBox\s*=\s*['\"]\s*([-\d.]+)[\s,]+([-\d.]+)[\s,]+([-\d.]+)[\s,]+([-\d.]+)", tag, re.I)
    if vb:
        info["viewbox"] = (float(vb.group(3)), float(vb.group(4)))
    for key in ("width", "height"):
        a = re.search(rf"\b{key}\s*=\s*['\"]\s*([\d.]+)\s*(?:px)?\s*['\"]", tag, re.I)
        if a:
            info[f"attr_{key[0]}"] = float(a.group(1))

    info["has_title"] = bool(re.search(r"<title\b", text, re.I))
    info["has_desc"] = bool(re.search(r"<desc\b", text, re.I))

    # 字号：元素属性 / style 属性 / <style> 块中的声明，全部收集后取最小
    for attr in re.finditer(r"\bfont-size\s*[=:]\s*['\"]?\s*([\d.]+)", text, re.I):
        info["font_sizes"].append(float(attr.group(1)))
    # font 简写里也带字号（font: 600 22px/1.5 ...）。不认简写就会退回默认的 16 单位，
    # 于是字号本来就够的图被判成 11.2px。单位只认绝对长度，em/% 之类的相对值跳过。
    for sh in re.finditer(r"\bfont\s*:\s*([^;'\"}>]+)", text, re.I):
        m = re.search(r"([\d.]+)(?:px|pt|pc)\b", sh.group(1))
        if m:
            info["font_sizes"].append(float(m.group(1)))
    for fam in re.finditer(r"font-family\s*[=:]\s*['\"]?([^;'\"}>]+)", text, re.I):
        info["font_families"].append(fam.group(1).strip())

    # 背景：是否存在覆盖 viewBox 起点、宽高等于画布的 rect
    if info["viewbox"]:
        vw, vh = info["viewbox"]
        for rect in re.finditer(r"<rect\b[^>]*>", text, re.I):
            r = rect.group(0)

            def num(name, default=0.0):
                mm = re.search(rf"\b{name}\s*=\s*['\"]\s*([\d.]+)", r, re.I)
                return float(mm.group(1)) if mm else default

            if num("width") >= vw * 0.98 and num("height") >= vh * 0.98:
                if not re.search(r"fill\s*=\s*['\"]\s*(?:none|transparent)", r, re.I):
                    info["has_bg_rect"] = True
    return info


# ---------------------------------------------------------------- 引用提取

# Markdown 图片：![alt](src) 或 ![alt](src =838x300)
IMG_MD = re.compile(
    r"!\[([^\]]*)\]\(\s*<?([^)\s>]+)>?"
    r"(?:\s+=\s*(\d+)(?:x(\d+))?|\s+[\"'][^\"']*[\"'])?\s*\)")
# Markdown 链接：排除图片，用来查普通文件在不在
LINK_MD = re.compile(
    r"(?<!!)\[([^\]]*)\]\(\s*<?([^)\s>]+)>?(?:\s+[\"'][^\"']*[\"'])?\s*\)")
IMG_HTML = re.compile(r"<img\b[^>]*>", re.I)
SOURCE_HTML = re.compile(r"<source\b[^>]*>", re.I)
SRC_ATTR = re.compile(r"\bsrc\s*=\s*[\"']([^\"']+)[\"']", re.I)
SRCSET_ATTR = re.compile(r"\bsrcset\s*=\s*[\"']([^\"']+)[\"']", re.I)
HREF_HTML = re.compile(r"<a\b[^>]*\bhref\s*=\s*[\"']([^\"']+)[\"']", re.I)
WIDTH_ATTR = re.compile(r"\bwidth\s*=\s*[\"']?(\d+)", re.I)
# style="width:838px" 与 width="838px" 同样会被浏览器照做，只认 width= 会漏
STYLE_WIDTH = re.compile(r"style\s*=\s*[\"'][^\"']*?\bwidth\s*:\s*(\d+)", re.I)
ALT_ATTR = re.compile(r"\balt\s*=\s*[\"']([^\"']*)[\"']", re.I)


def is_local(raw: str) -> bool:
    if raw.startswith(("http://", "https://", "//", "data:", "mailto:", "#", "tel:")):
        return False
    # 通配符和尖括号是文档里写的占位路径，不是真引用
    if any(ch in raw for ch in "*?{}<>"):
        return False
    return True


def exact_child(cur: Path, seg: str) -> tuple[Path | None, str]:
    """在当前目录里按精确名字找子项，顺带查大小写。

    GitHub 区分大小写，本地 macOS 不区分：README 写 Images/Hero.png 而实际文件叫
    images/hero.png 时，本地 exists() 为真，线上 404。
    """
    try:
        names = os.listdir(cur)
    except OSError:
        return None, "目录读不到"
    if seg in names:
        return cur / seg, ""
    near = [n for n in names if n.lower() == seg.lower()]
    if near:
        return None, f"大小写不符，实际是 {near[0]}"
    return None, "不存在"


def repo_root(start: Path) -> Path | None:
    """从 README 所在目录往上找 .git，定位仓库根。

    GitHub 把以 / 开头的链接按仓库根解析，而 README 不一定在根目录。
    找不到 .git 时返回 None，调用方只能提示、不能判死。
    """
    for p in [start, *start.parents]:
        if (p / ".git").exists():
            return p
    return None


def resolve_local(root: Path, raw: str, repo: Path | None = None) -> tuple[Path | None, str]:
    rel = unquote(urlparse(raw).path)
    if rel.startswith("/"):
        if repo is None:
            return None, "以 / 开头，找不到仓库根，无法校验"
        cur = repo
        rel = rel.lstrip("/")
    else:
        cur = root
    for seg in [p for p in rel.split("/") if p and p != "."]:
        if seg == "..":
            cur = cur.parent
            continue
        cur, problem = exact_child(cur, seg)
        if problem:
            return None, problem
    return cur, ""


def collect_assets(md_path: Path) -> list[Asset]:
    text = strip_code(md_path.read_text(encoding="utf-8", errors="replace"))
    root = md_path.parent
    top = repo_root(root)
    assets: list[Asset] = []
    table_lines = {
        i + 1 for i, line in enumerate(text.splitlines())
        if line.lstrip().startswith("|") or re.match(r"^\s*<t[dr]\b", line, re.I)
    }

    def build(raw, alt, width, line_no, in_table):
        a = Asset(raw=raw, path=None, decl_width=width, alt=alt or "", in_table=in_table, line=line_no)
        if is_local(raw):
            a.kind = Path(unquote(urlparse(raw).path)).suffix.lower().lstrip(".")
            p, problem = resolve_local(root, raw, top)
            if p is None and raw.startswith("/") and top is None:
                a.unverified = True
                a.case_hint = problem
            elif p is not None and p.is_file():
                a.path = p
                a.exists = True
                a.size_bytes = p.stat().st_size
                if a.kind == "svg":
                    info = svg_info(p.read_text(encoding="utf-8", errors="replace"))
                    if info["viewbox"]:
                        a.intrinsic = (int(info["viewbox"][0]), int(info["viewbox"][1]))
                    elif info["attr_w"] and info["attr_h"]:
                        a.intrinsic = (int(info["attr_w"]), int(info["attr_h"]))
                else:
                    a.intrinsic = raster_size(p)
            else:
                a.path = root / unquote(urlparse(raw).path).lstrip("/")
                a.case_hint = problem
        return a

    for m in IMG_MD.finditer(text):
        line_no = text[:m.start()].count("\n") + 1
        w = int(m.group(3)) if m.group(3) else None
        assets.append(build(m.group(2), m.group(1), w, line_no, line_no in table_lines))

    for m in IMG_HTML.finditer(text):
        line_no = text[:m.start()].count("\n") + 1
        tag = m.group(0)
        src = SRC_ATTR.search(tag)
        if not src:
            continue
        w = WIDTH_ATTR.search(tag) or STYLE_WIDTH.search(tag)
        alt = ALT_ATTR.search(tag)
        assets.append(build(src.group(1), alt.group(1) if alt else "", int(w.group(1)) if w else None,
                           line_no, line_no in table_lines))

    # <picture> 里的 <source srcset>：换格式时真正的加载源，坏了整张图不显示
    for m in SOURCE_HTML.finditer(text):
        line_no = text[:m.start()].count("\n") + 1
        ss = SRCSET_ATTR.search(m.group(0))
        if not ss:
            continue
        first = ss.group(1).split(",")[0].strip().split(" ")[0]
        if first:
            assets.append(build(first, "", None, line_no, line_no in table_lines))
    return assets


# ---------------------------------------------------------------- 检查

def check_links(md_path: Path, rep: Report) -> int:
    """查普通文件链接。README 里的 CONTRIBUTING.md、docs/ 目录同样是会 404 的目标。"""
    name = md_path.name
    text = strip_code(md_path.read_text(encoding="utf-8", errors="replace"))
    top = repo_root(md_path.parent)
    n = 0
    # Markdown 链接和 <a href> 都要查：居中排版、按钮、导航常用 HTML 写链接
    targets = [(m.group(2), m.start()) for m in LINK_MD.finditer(text)]
    targets += [(m.group(1), m.start()) for m in HREF_HTML.finditer(text)]
    for raw, pos in targets:
        if not is_local(raw):
            continue
        # 纯静态资源交给图片检查，避免同一个文件报两次
        if re.search(r"\.(?:png|jpe?g|gif|webp|avif|svg|ico)$", raw, re.I):
            continue
        n += 1
        line_no = text[:pos].count("\n") + 1
        p, problem = resolve_local(md_path.parent, raw, top)
        if p is None and raw.startswith("/") and top is None:
            rep.add("WARN", name, f"第 {line_no} 行", f"链接以 / 开头，找不到仓库根，未校验: {raw}",
                    "[经验] 没有 .git 可定位仓库根，这项只能提示")
            continue
        if p is None or not p.exists():
            rep.add("FAIL", name, f"第 {line_no} 行", f"链接目标不存在: {raw}（{problem or '找不到'}）",
                    "[官方] GitHub 区分大小写，路径写错就是 404")
    return n


def check_remote(a: Asset, name: str, where: str, rep: Report) -> None:
    req = urllib.request.Request(a.raw, method="HEAD", headers={"User-Agent": "github-readme-skill"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            if r.status >= 400:
                rep.add("WARN", name, where, f"外链返回 {r.status}", "[实测] 平台不会转存外链图")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
        rep.add("WARN", name, where, f"外链拿不到: {e}", "[实测] 外链挂了图就是破的")


def check_file(md_path: Path, rep: Report, remote: bool = False) -> None:
    name = md_path.name
    rep.scanned_files.append(str(md_path))
    n_links = check_links(md_path, rep)
    assets = collect_assets(md_path)
    rep.assets.extend(assets)

    if not assets:
        rep.add("INFO", name, "全文", f"没有引用任何图片（另有 {n_links} 个文件链接已查）", "—")
        return

    for a in assets:
        where = f"第 {a.line} 行 {a.raw.split('/')[-1][:40]}"

        if not is_local(a.raw):
            if remote:
                check_remote(a, name, where, rep)
            else:
                rep.add("INFO", name, where, "外链图片，未做本地检查（--check-remote 可验可达性）", "—")
            continue
        if not a.exists:
            if a.unverified:
                rep.add("WARN", name, where, f"{a.raw} — {a.case_hint}",
                        "[经验] 没有 .git 可定位仓库根，这项只能提示")
                continue
            detail = f"文件不存在: {a.path}"
            if a.case_hint:
                detail = f"{a.raw} — {a.case_hint}"
            rep.add("FAIL", name, where, detail, "GitHub 区分大小写，本地 macOS 不区分")
            continue

        # 体积
        if a.kind == "gif" and a.size_bytes > GIF_HEAVY_BYTES:
            rep.add("WARN", name, where,
                    f"GIF {a.size_bytes/1048576:.1f} MB，移动网络下明显拖慢；先砍尺寸再砍帧率",
                    f"[经验] {GIF_HEAVY_BYTES/1048576:.0f} MB 为告警线，非平台限制（图片网页上传上限 {WEB_UPLOAD_IMAGE_LIMIT//1048576} MiB）")
        elif a.kind == "gif" and a.size_bytes > GIF_TARGET_BYTES:
            rep.add("WARN", name, where,
                    f"GIF {a.size_bytes/1048576:.1f} MB，超过 {GIF_TARGET_BYTES//1048576} MB 首屏预算",
                    f"[经验] {GIF_TARGET_BYTES//1048576} MB 是加载预算，不是平台限制；见 visual-craft.md §4")
        if a.kind == "svg" and a.size_bytes > SOFT_SVG_BYTES:
            rep.add("WARN", name, where, f"SVG {a.size_bytes/1024:.0f} KB，偏大",
                    f"[经验] {SOFT_SVG_BYTES//1024} KB 为参考上限")
        upload_limit = (WEB_UPLOAD_IMAGE_LIMIT if a.kind in IMAGE_KINDS
                        else WEB_UPLOAD_LIMIT)
        if a.size_bytes > upload_limit:
            rep.add("FAIL", name, where,
                    f"{a.size_bytes/1048576:.1f} MB，超过网页上传上限 {upload_limit//1048576} MiB",
                    "[官方] 网页上传：图片与 GIF 10 MiB，其他文件 25 MiB；git push 阻止线 100 MiB")

        # 容器宽
        container = TABLE_CELL_WIDTH if a.in_table else COLUMN_WIDTH
        tag = "表格单元格" if a.in_table else "正文列"

        if a.decl_width is not None and a.decl_width > container:
            over = a.decl_width / container
            actual = min(a.decl_width, container)
            rep.add("FAIL" if over > 1.05 else "WARN", name, where,
                    f"声明 width={a.decl_width}，{tag}只有 {container}px，实际渲染 {actual}px"
                    + (f"（压掉 {(1 - actual / a.decl_width) * 100:.1f}%）" if a.decl_width else ""),
                    f"[实测] {tag}可用宽 {container}px（rendering.md，可用 --column-width 覆盖）")

        # 渲染宽：声明宽优先，否则取固有宽，再被容器截断
        if a.kind == "svg":
            check_svg(name, where, a, container, tag, rep)
        else:
            intrinsic_w = a.intrinsic[0] if a.intrinsic else None
            if intrinsic_w is None:
                rep.add("WARN", name, where, "读不出原图尺寸，无法判断缩放", "文件头解析失败")
                continue
            # 2 倍屏下截图需要 2×CSS 宽的像素才清晰；动图按 1× 算，否则体积撑不住
            need = container if a.kind == "gif" else container * 2
            if intrinsic_w > need * 1.3:
                used = need / intrinsic_w * 100
                rep.add("WARN", name, where,
                        f"原图 {intrinsic_w}px 宽，2 倍屏下也只需要 {need}px，{100 - used:.0f}% 的像素不会显示",
                        f"[实测] {tag} {container}px；若这张图供点击看原图则忽略")
            elif intrinsic_w < container:
                rep.add("WARN", name, where,
                        f"原图 {intrinsic_w}px 窄于{tag} {container}px，会被拉伸发虚",
                        f"[实测] {tag}宽 {container}px")


def check_svg(name: str, where: str, a: Asset,
              container: int, tag: str, rep: Report) -> None:
    text = a.path.read_text(encoding="utf-8", errors="replace")
    info = svg_info(text)

    if not info["viewbox"]:
        rep.add("FAIL", name, where,
                "缺 viewBox，无法在容器内等比缩放，一个尺寸错了整张图糊",
                "[经验] SVG 规范里 viewBox 定义用户坐标，缺省时按固有尺寸渲染")
        return

    vb_w = info["viewbox"][0]
    rendered_w = min(a.decl_width or vb_w, container)
    scale = rendered_w / vb_w if vb_w else 1.0

    # 远程资源
    for pattern, label in EXTERNAL_RESOURCE_PATTERNS:
        if pattern.search(text):
            rep.add("FAIL", name, where, f"{label}：GitHub 一定拦掉",
                    "[官方] raw 的 CSP 是 default-src 'none'，只放行内联样式；CDP 实测 img 内的字体请求不会发出")

    # 字体是否只依赖系统栈
    for fam in info["font_families"]:
        names = [n.strip().strip("'\"").lower() for n in fam.split(",") if n.strip()]
        if names and not any(n in SYSTEM_FONT_HINTS for n in names):
            rep.add("WARN", name, where,
                    f"font-family 只有 {fam[:40]}，不是系统字体栈，平台会 fallback 成别的字，定宽排版会错位",
                    "[实测] 平台不加载远程字体")

    # 字号换算：只对真含文字的图判定，纯图形不适用
    has_text = bool(re.search(r"<text\b|<tspan\b|<textPath\b", text, re.I))
    sizes = info["font_sizes"] or ([DEFAULT_SVG_FONT_SIZE] if has_text else [])
    if sizes:
        smallest = min(sizes)
        rendered_px = smallest * scale
        if rendered_px < MIN_RENDERED_FONT_PX:
            rep.add("FAIL", name, where,
                    f"最小字号 {smallest:g} 单位 × {scale:.3f} = {rendered_px:.1f}px，低于 {MIN_RENDERED_FONT_PX:g}px",
                    f"[实测] 换算式 {smallest:g} × {rendered_w} ÷ {vb_w:g}；{MIN_RENDERED_FONT_PX:g}px 为[经验]下限")
        elif rendered_px < WARN_RENDERED_FONT_PX:
            rep.add("WARN", name, where,
                    f"最小字号渲染 {rendered_px:.1f}px，接近下限",
                    "[经验] 低于 14px 时中文在 1x 屏上吃力")

    if not info["has_title"] or not info["has_desc"]:
        missing = "、".join(x for x, ok in (("<title>", info["has_title"]), ("<desc>", info["has_desc"])) if not ok)
        rep.add("WARN", name, where, f"缺 {missing}，读屏软件读不出这张图",
                "[经验] 可访问性；也影响图在搜索结果里的描述")

    if not info["has_bg_rect"]:
        rep.add("WARN", name, where,
                "没有铺满画布的背景，深色主题下透明区会露出页面底色，深色文字可能消失",
                "[经验] SVG 作为独立文档不继承页面配色，需自带背景")


# ---------------------------------------------------------------- 自测

SELFTEST_ROOT = SKILL_DIR / "scripts" / "fixtures"
HARD_BYTES = 6 * 1024 * 1024


def prepare_selftest_root() -> tempfile.TemporaryDirectory:
    """把样本拷到临时目录再跑。

    自测要造一个 6 MB 的 GIF 才能触发体积判据。早期版本直接写进技能安装目录，
    打包分发和只读挂载都会失败；现在写临时目录，退出时自动清理。
    """
    tmp = tempfile.TemporaryDirectory(prefix="github-readme-skill-selftest-")
    root = Path(tmp.name) / "fixtures"
    if not SELFTEST_ROOT.is_dir():
        raise FileNotFoundError(f"缺少自测样本目录: {SELFTEST_ROOT}")
    shutil.copytree(SELFTEST_ROOT, root, ignore=shutil.ignore_patterns("huge.gif"))
    big = root / "broken" / "huge.gif"
    if not big.exists():
        head = b"GIF89a" + struct.pack("<HH", 800, 450) + bytes([0xF0, 0x00, 0x00])
        big.write_bytes(head + b"\x00" * HARD_BYTES + b"\x3B")
    return tmp


def selftest() -> int:
    try:
        tmp = prepare_selftest_root()
    except (OSError, FileNotFoundError) as e:
        print(f"✗ 自测准备失败: {e}", file=sys.stderr)
        return 1

    root = Path(tmp.name) / "fixtures"
    cases = [
        ("good", 0, "合格的图应当全部通过"),
        ("broken", 1, "坏样本必须被拦住"),
    ]
    ok_all = True
    for case, expect, what in cases:
        md = root / case / "README.md"
        if not md.exists():
            print(f"✗ 缺少自测样本: {md}")
            ok_all = False
            continue
        rep = Report()
        check_file(md, rep)
        got = 1 if rep.fails else 0
        status = "✓" if got == expect else "✗"
        print(f"{status} {case:8s} 期望退出码 {expect}，实际 {got}  ({what})")
        if got != expect:
            ok_all = False
            for f in rep.findings:
                print("   ", f.level, f.where, f.detail)
        elif case == "broken":
            print(f"   命中 {len(rep.fails)} 个 FAIL / {len(rep.warns)} 个 WARN")
            covered = {f.detail.split("：")[0][:18] for f in rep.fails}
            print(f"   覆盖规则: {', '.join(sorted(covered))}")

    # 回归：只写 width= 会漏掉的三种声明方式
    probe_dir = Path(tmp.name) / "probe"
    probe_dir.mkdir()
    (probe_dir / "a.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 +
                                      struct.pack(">II", 100, 50) + b"IHDR" + b"\x00" * 16)
    (probe_dir / "README.md").write_text(
        "# P\n\n"
        "![a](a.png =1200x300)\n\n"
        '<img src="a.png" style="width:1200px">\n\n'
        "<picture><source srcset=\"a.png 1x\"><img src=\"a.png\"></picture>\n\n"
        "[文档](docs/missing.md)\n",
        encoding="utf-8")
    rep = Report()
    check_file(probe_dir / "README.md", rep)
    got_w = len([f for f in rep.fails if "width=" in f.detail])
    got_link = len([f for f in rep.fails if "链接目标不存在" in f.detail])
    got_srcset = len(rep.assets)
    print(f"{'✓' if got_w >= 2 and got_link == 1 and got_srcset == 4 else '✗'} "
          f"coverage 尺寸三种写法 {got_w}/2、文件链接 {got_link}/1、引用条数 {got_srcset}/4")
    if not (got_w >= 2 and got_link == 1 and got_srcset == 4):
        ok_all = False

    # 回归：双反引号里的写法样例不是真引用，HTML 写的断链同样要抓
    probe2 = Path(tmp.name) / "probe2"
    probe2.mkdir()
    (probe2 / "README.md").write_text(
        "# P\n\n"
        "写法：`` `[x](ghost.md)` ``、`` `![y](nope.png)` ``。\n\n"
        "真链接 [文档](docs/missing.md)。\n\n"
        '<a href="guide/missing.md">指南</a>\n',
        encoding="utf-8")
    rep = Report()
    check_file(probe2 / "README.md", rep)
    got_broken = {
        f.detail.split(": ", 1)[-1].split("（")[0]
        for f in rep.fails if "链接目标不存在" in f.detail
    }
    want_broken = {"docs/missing.md", "guide/missing.md"}
    print(f"{'✓' if got_broken == want_broken else '✗'} links     双反引号样例不误报，HTML 断链要抓"
          f"（实际 {sorted(got_broken)}）")
    if got_broken != want_broken:
        ok_all = False

    # 回归：以 / 开头的链接按仓库根解析，找不到仓库根时只提示
    probe3 = Path(tmp.name) / "probe3"
    (probe3 / ".git").mkdir(parents=True)
    (probe3 / "docs").mkdir()
    (probe3 / "docs" / "guide.md").write_text("内容", encoding="utf-8")
    (probe3 / "images").mkdir()
    (probe3 / "images" / "hero.png").write_bytes(
        b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + struct.pack(">II", 400, 200) + b"IHDR" + b"\x00" * 16)
    (probe3 / "README.md").write_text(
        "# P\n\n[文档](/docs/guide.md)\n\n![图](/images/hero.png)\n\n[坏的](/docs/missing.md)\n",
        encoding="utf-8")
    rep = Report()
    check_file(probe3 / "README.md", rep)
    root_broken = [f for f in rep.fails if "链接目标不存在" in f.detail]
    print(f"{'✓' if len(root_broken) == 1 else '✗'} rootpath  / 开头按仓库根解析"
          f"（FAIL {len(root_broken)}，期望 1）")
    if len(root_broken) != 1:
        ok_all = False

    probe4 = Path(tmp.name) / "probe4"
    probe4.mkdir()
    (probe4 / "README.md").write_text(
        "# P\n\n[文档](/docs/guide.md)\n\n![图](/images/hero.png)\n", encoding="utf-8")
    rep = Report()
    check_file(probe4 / "README.md", rep)
    nofail = not rep.fails and len([f for f in rep.warns if "仓库根" in f.detail]) == 2
    print(f"{'✓' if nofail else '✗'} rootpath  没有 .git 时降级为提示，不判死")
    if not nofail:
        ok_all = False

    width_ok = all((
        parse_positive_px("0") is None,
        parse_positive_px("-1") is None,
        parse_positive_px("abc") is None,
        parse_positive_px("760") == 760,
    ))
    print(f"{'✓' if width_ok else '✗'} width     列宽只收正整数")
    if not width_ok:
        ok_all = False

    tmp.cleanup()
    print()
    print("自测通过" if ok_all else "自测失败")
    return 0 if ok_all else 1


# ---------------------------------------------------------------- 入口

def parse_positive_px(v: str) -> int | None:
    """列宽只接受正整数；0 会在换算字号时触发除零。"""
    try:
        val = int(v)
    except ValueError:
        return None
    return val if val > 0 else None


def take_value(argv: list[str], flag: str) -> str | None:
    if flag not in argv:
        return None
    i = argv.index(flag)
    if i + 1 >= len(argv):
        print(f"{flag} 后面要给数值或路径", file=sys.stderr)
        return None
    return argv[i + 1]


def main(argv: list[str]) -> int:
    global COLUMN_WIDTH, TABLE_CELL_WIDTH

    if "--selftest" in argv:
        return selftest()

    skip = {"--column-width", "--table-width", "--check-remote"}
    args, i = [], 1
    while i < len(argv):
        a = argv[i]
        if a in skip:
            if a != "--check-remote":
                i += 2
                continue
            i += 1
            continue
        if not a.startswith("--"):
            args.append(a)
        i += 1

    for flag, target in (("--column-width", "COLUMN_WIDTH"), ("--table-width", "TABLE_CELL_WIDTH")):
        v = take_value(argv, flag)
        if v is None:
            if flag in argv:
                return 2          # flag 在但没跟值，take_value 已经报过错
            continue
        val = parse_positive_px(v)
        if val is None:
            print(f"{flag} 要给正整数像素，收到 {v!r}", file=sys.stderr)
            return 2
        if target == "COLUMN_WIDTH":
            COLUMN_WIDTH = val
        else:
            TABLE_CELL_WIDTH = val

    if not args:
        print(__doc__)
        return 2

    remote = "--check-remote" in argv
    rep = Report()
    for raw in args:
        p = Path(raw)
        if not p.exists():
            print(f"找不到文件: {raw}", file=sys.stderr)
            return 2
        check_file(p, rep, remote=remote)

    if "--json" in argv:
        print(json.dumps({
            "scanned": rep.scanned_files,
            "column_width": COLUMN_WIDTH,
            "table_cell_width": TABLE_CELL_WIDTH,
            "assets": [
                {"raw": a.raw, "line": a.line, "kind": a.kind, "exists": a.exists,
                 "bytes": a.size_bytes, "intrinsic": a.intrinsic,
                 "declared_width": a.decl_width, "in_table": a.in_table}
                for a in rep.assets
            ],
            "findings": [f.__dict__ for f in rep.findings],
            "fails": len(rep.fails), "warns": len(rep.warns),
        }, ensure_ascii=False, indent=2))
        return 1 if rep.fails else 0

    print(f"扫描 {len(rep.scanned_files)} 份文件，{len(rep.assets)} 个图片引用"
          f"（正文列 {COLUMN_WIDTH}px，表格单元格 {TABLE_CELL_WIDTH}px）\n")
    by_file: dict[str, list[Finding]] = {}
    for f in rep.findings:
        by_file.setdefault(f.file, []).append(f)

    for name, items in by_file.items():
        print(name)
        order = {"FAIL": 0, "WARN": 1, "INFO": 2}
        for f in sorted(items, key=lambda x: (order[x.level], x.where)):
            print(f.render())
        print()

    if not rep.findings:
        print("没有发现问题。")

    print(f"FAIL {len(rep.fails)} 项，WARN {len(rep.warns)} 项")
    if rep.fails:
        print("exit 1：有必须修的项")
        return 1
    print("exit 0：没有会崩的项")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
