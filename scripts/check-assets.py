#!/usr/bin/env python3
"""检查 README 引用的图在 GitHub 上会不会坏。

只判"会不会崩"，不判"好不好看"。审美归审稿人，会崩的归脚本。

用法:
    python3 scripts/check-assets.py README.md
    python3 scripts/check-assets.py README.md README.en.md
    python3 scripts/check-assets.py --selftest
    python3 scripts/check-assets.py README.md --json

退出码: 0 = 没有 FAIL, 1 = 有 FAIL, 2 = 用法或路径错误

判据来源分三类，输出里逐条标注:
  [实测] rendering.md 里在 Chrome 156 + 线上 GitHub 量出来的数
  [官方] 平台响应头或官方文档
  [经验] 工程阈值，不是平台规定，可自行调整
"""

from __future__ import annotations

import json
import re
import struct
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote, urlparse

# ---------------------------------------------------------------- 判据常量

# [实测] references/rendering.md：桌面 1280/1440/1920 三档正文列均为 838px，
# 窄屏 390 视口为 324px。验收取 838。
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

# [官方] GitHub 文件大小: 50 MiB 起 git 警告，100 MiB 直接阻止，
# 通过网页上传单文件上限 25 MiB。README 图片没有单独的体积规定。
HARD_FILE_LIMIT = 100 * 1024 * 1024
WEB_UPLOAD_LIMIT = 25 * 1024 * 1024

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
# 注意 "inter" / "roboto" 这类 Web Font 不在此列：它们不是任何系统的默认字体，
# 用户没装就 fallback，按系统字体栈处理会漏掉排版错位。

# [经验] 中文圈常见的内行黑话，对应 SKILL.md §8「删除内行黑话」。
JARGON_WORDS = [
    "hero", "above the fold", "cta", "onboarding", "kpi", "roi", "mvp",
    "pain point", "北向", "闭环", "抓手", "赋能", "对齐颗粒度", "心智",
]


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
    path: str | None          # 本地路径，外链为 None
    decl_width: int | None
    alt: str
    in_table: bool
    line: int
    kind: str = ""            # svg / gif / png / jpg / webp / other
    intrinsic: tuple[int, int] | None = None
    size_bytes: int = 0
    exists: bool = False


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

IMG_MD = re.compile(r"!\[([^\]]*)\]\(\s*<?([^)\s>]+)>?(?:\s+[\"'][^\"']*[\"'])?\s*\)")
IMG_HTML = re.compile(r"<img\b[^>]*>", re.I)
SRC_ATTR = re.compile(r"\bsrc\s*=\s*[\"']([^\"']+)[\"']", re.I)
WIDTH_ATTR = re.compile(r"\bwidth\s*=\s*[\"']?(\d+)", re.I)
ALT_ATTR = re.compile(r"\balt\s*=\s*[\"']([^\"']*)[\"']", re.I)


def is_local(raw: str) -> bool:
    if raw.startswith(("http://", "https://", "//", "data:", "mailto:", "#")):
        return False
    # 通配符和尖括号是文档里写的占位路径，不是真引用
    if any(ch in raw for ch in "*?{}<>"):
        return False
    return True


def blank_fences(text: str) -> str:
    """把代码围栏内的内容换成空行，保留行号。

    示例代码块里的图片引用是给人看的样板，不是真的引用，
    不剥掉会把文档自己的示例判成断链。
    """
    out, in_fence = [], False
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append("\n" if line.endswith("\n") else "")
            continue
        out.append(("\n" if line.endswith("\n") else "") if in_fence else line)
    return "".join(out)


def collect_assets(md_path: Path) -> list[Asset]:
    text = blank_fences(md_path.read_text(encoding="utf-8", errors="replace"))
    root = md_path.parent
    assets: list[Asset] = []
    table_lines = {
        i + 1 for i, line in enumerate(text.splitlines())
        if line.lstrip().startswith("|") or re.match(r"^\s*<t[dr]\b", line, re.I)
    }

    def build(raw, alt, width, line_no, in_table):
        a = Asset(raw=raw, path=None, decl_width=width, alt=alt or "", in_table=in_table, line=line_no)
        if is_local(raw):
            p = unquote(urlparse(raw).path)
            a.path = (root / p.lstrip("/")).resolve() if not p.startswith("/") else Path(p).resolve()
            a.kind = Path(p).suffix.lower().lstrip(".")
            if a.path.exists() and a.path.is_file():
                a.exists = True
                a.size_bytes = a.path.stat().st_size
                if a.kind == "svg":
                    info = svg_info(a.path.read_text(encoding="utf-8", errors="replace"))
                    if info["viewbox"]:
                        a.intrinsic = (int(info["viewbox"][0]), int(info["viewbox"][1]))
                    elif info["attr_w"] and info["attr_h"]:
                        a.intrinsic = (int(info["attr_w"]), int(info["attr_h"]))
                else:
                    a.intrinsic = raster_size(a.path)
        return a

    for m in IMG_MD.finditer(text):
        line_no = text[:m.start()].count("\n") + 1
        assets.append(build(m.group(2), m.group(1), None, line_no, line_no in table_lines))

    for m in IMG_HTML.finditer(text):
        line_no = text[:m.start()].count("\n") + 1
        tag = m.group(0)
        src = SRC_ATTR.search(tag)
        if not src:
            continue
        w = WIDTH_ATTR.search(tag)
        alt = ALT_ATTR.search(tag)
        assets.append(build(src.group(1), alt.group(1) if alt else "", int(w.group(1)) if w else None,
                           line_no, line_no in table_lines))
    return assets


# ---------------------------------------------------------------- 检查

def check_file(md_path: Path, rep: Report) -> None:
    name = md_path.name
    rep.scanned_files.append(str(md_path))
    assets = collect_assets(md_path)
    rep.assets.extend(assets)

    if not assets:
        rep.add("INFO", name, "全文", "没有引用任何图片", "—")
        return

    for a in assets:
        where = f"第 {a.line} 行 {a.raw.split('/')[-1][:40]}"

        if not is_local(a.raw):
            rep.add("INFO", name, where, "外链图片，不做本地检查", "—")
            continue
        if not a.exists:
            rep.add("FAIL", name, where, f"文件不存在: {a.path}", "GitHub 区分大小写，本地 macOS 不区分")
            continue

        # 体积
        if a.kind == "gif" and a.size_bytes > GIF_HEAVY_BYTES:
            rep.add("WARN", name, where,
                    f"GIF {a.size_bytes/1048576:.1f} MB，移动网络下明显拖慢；先砍尺寸再砍帧率",
                    f"[经验] {GIF_HEAVY_BYTES/1048576:.0f} MB 为告警线，非平台限制（平台阻止线 {HARD_FILE_LIMIT//1048576} MiB）")
        elif a.kind == "gif" and a.size_bytes > GIF_TARGET_BYTES:
            rep.add("WARN", name, where,
                    f"GIF {a.size_bytes/1048576:.1f} MB，超过 {GIF_TARGET_BYTES//1048576} MB 首屏预算",
                    f"[经验] {GIF_TARGET_BYTES//1048576} MB 是加载预算，不是平台限制；见 visual-craft.md §4")
        if a.kind == "svg" and a.size_bytes > SOFT_SVG_BYTES:
            rep.add("WARN", name, where, f"SVG {a.size_bytes/1024:.0f} KB，偏大",
                    f"[经验] {SOFT_SVG_BYTES//1024} KB 为参考上限")
        if a.size_bytes > WEB_UPLOAD_LIMIT:
            rep.add("FAIL", name, where, f"{a.size_bytes/1048576:.1f} MB，超过网页上传单文件上限",
                    "[官方] 网页上传上限 25 MiB；git push 阻止线 100 MiB")

        # 容器宽
        container = TABLE_CELL_WIDTH if a.in_table else COLUMN_WIDTH
        tag = "表格单元格" if a.in_table else "正文列"

        if a.decl_width is not None and a.decl_width > container:
            over = a.decl_width / container
            actual = min(a.decl_width, container)
            rep.add("FAIL" if over > 1.05 else "WARN", name, where,
                    f"声明 width={a.decl_width}，{tag}只有 {container}px，实际渲染 {actual}px"
                    + (f"（压掉 {(1 - actual / a.decl_width) * 100:.1f}%）" if a.decl_width else ""),
                    f"[实测] {tag}可用宽 {container}px（rendering.md）")

        # 渲染宽：声明宽优先，否则取固有宽，再被容器截断
        if a.kind == "svg":
            check_svg(md_path, name, where, a, container, tag, rep)
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


def check_svg(md_path: Path, name: str, where: str, a: Asset,
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

SELFTEST_ROOT = Path(__file__).resolve().parent / "fixtures"


def ensure_fixtures() -> list[str]:
    """自测用的大文件不进仓库，跑之前现生成。

    6 MB 的 GIF 只为了触发体积判据，提交进仓库是纯粹的浪费。
    """
    made = []
    big = SELFTEST_ROOT / "broken" / "huge.gif"
    if not big.exists():
        head = b"GIF89a" + struct.pack("<HH", 800, 450) + bytes([0xF0, 0x00, 0x00])
        big.write_bytes(head + b"\x00" * (6 * 1024 * 1024) + b"\x3B")
        made.append(big.name)
    return made


def selftest() -> int:
    made = ensure_fixtures()
    if made:
        print(f"（已生成自测用的临时样本: {', '.join(made)}）\n")
    cases = [
        ("good", 0, "合格的图应当全部通过"),
        ("broken", 1, "坏样本必须被拦住"),
    ]
    ok_all = True
    for case, expect, what in cases:
        md = SELFTEST_ROOT / case / "README.md"
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
    print()
    print("自测通过" if ok_all else "自测失败")
    return 0 if ok_all else 1


# ---------------------------------------------------------------- 入口

def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a for a in argv[1:] if a.startswith("--")}

    if "--selftest" in flags:
        return selftest()

    if not args:
        print(__doc__)
        return 2

    rep = Report()
    for raw in args:
        p = Path(raw)
        if not p.exists():
            print(f"找不到文件: {raw}", file=sys.stderr)
            return 2
        check_file(p, rep)

    if "--json" in flags:
        print(json.dumps({
            "scanned": rep.scanned_files,
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

    print(f"扫描 {len(rep.scanned_files)} 份文件，{len(rep.assets)} 个图片引用\n")
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
