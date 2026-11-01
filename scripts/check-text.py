#!/usr/bin/env python3
"""检查 README 的文字结构：首屏、锚点、双语对照、术语一致。

只判能机械验证的部分。判断"这段写得好不好"不在脚本范围内。

用法:
    python3 scripts/check-text.py README.md
    python3 scripts/check-text.py README.md README.en.md --pair
    python3 scripts/check-text.py README.md --terms terms.txt
    python3 scripts/check-text.py --selftest

退出码: 0 = 没有 FAIL, 1 = 有 FAIL, 2 = 用法或路径错误

判据来源:
  [规则] SKILL.md 里的明文规定，附章节号
  [经验] 页面版式的工程阈值
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# [规则] SKILL.md §4：首屏控制在约 25 行以内
FIRST_SCREEN_LINES = 25

# [规则] SKILL.md §6 / §4：徽章 2–7 个，功能性优先
BADGE_MAX = 7

# [规则] SKILL.md §8：删除内行黑话。词表按项目补充，不要指望它覆盖全部。
DEFAULT_JARGON = [
    "hero", "above the fold", "CTA", "onboarding", "KPI", "ROI", "MVP",
    "pain point", "核心抓手", "闭环", "赋能", "对齐颗粒度", "心智模型",
]

# [规则] SKILL.md §6：不加可误复制的 $ 提示符
PROMPT_PATTERN = re.compile(r"^\s*\$ \S", re.M)

# [经验] 判断首屏有没有"动作"的关键词
ACTION_PATTERN = re.compile(
    r"\b(?:npx|npm i|npm install|pnpm|yarn|bun|brew|pip|uv|cargo|go install|"
    r"git clone|curl|wget|docker run|mas install)\b|下载|安装|打开站点", re.I)

# [规则] SKILL.md §4：安装排在第 4 节之后时，首屏必须给锚点跳转。
# 有跳转就不算"首屏没有动作"。
JUMP_PATTERN = re.compile(r"\]\(#(?:安装|使用|开始|快速开始|install|usage|get-started|getting-started|quick-?start)[^)]*\)", re.I)

# [经验] 只在中文文档上跑黑话扫描：onboarding 这类词在英文原文里是正常用词。
CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]")

# 只把真命令拿来对照，避免把自然语言示例当成命令不一致
COMMAND_PATTERN = re.compile(
    r"^(?:npx|npm|pnpm|yarn|bun|brew|pip|pip3|uv|cargo|go|git|curl|wget|docker|mas|"
    r"python|python3|node|sh|bash|zsh|chmod|mkdir|export|cd|make|swift)\b")


@dataclass
class Finding:
    level: str
    file: str
    where: str
    detail: str
    basis: str

    def render(self) -> str:
        icon = {"FAIL": "✗", "WARN": "!", "INFO": "·"}[self.level]
        loc = self.file if self.where in ("全文", "") else f"{self.file}:{self.where}"
        return f"  {icon} [{self.level}] {loc} — {self.detail}  ({self.basis})"


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)
    files: list[str] = field(default_factory=list)

    def add(self, level, file, where, detail, basis):
        self.findings.append(Finding(level, file, where, detail, basis))

    @property
    def fails(self):
        return [f for f in self.findings if f.level == "FAIL"]

    @property
    def warns(self):
        return [f for f in self.findings if f.level == "WARN"]


# ---------------------------------------------------------------- 解析

def gh_slug(title: str) -> str:
    """按 GitHub 生成标题锚点的规则：小写、去标点、空格转连字符。"""
    s = title.strip().lower()
    s = re.sub(r"[^\w\u4e00-\u9fff \-]", "", s)
    return s.replace(" ", "-")


def count_word(text: str, word: str) -> int:
    """英文按词边界计数。子串匹配会让 CTA 命中 re-cta-ngle 这类词。"""
    if re.fullmatch(r"[A-Za-z0-9 \-]+", word):
        return len(re.findall(rf"(?<![A-Za-z]){re.escape(word)}(?![A-Za-z])", text, re.I))
    return text.count(word)


def strip_code(text: str) -> str:
    """去掉围栏内的代码，避免把命令里的符号当成正文内容。"""
    return re.sub(r"```.*?```", "", text, flags=re.S)


def headings(text: str) -> list[tuple[int, str, int]]:
    """返回 (级别, 标题, 行号)，跳过代码围栏内的 #。"""
    out, in_fence = [], False
    for i, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if m:
            out.append((len(m.group(1)), m.group(2).strip(), i))
    return out


def fences(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.lstrip().startswith("```"))


def badges(text: str) -> list[str]:
    return re.findall(r"!\[[^\]]*\]\((https?://[^)\s]*shields\.io[^)\s]*)\)", text)


# ---------------------------------------------------------------- 单文件检查

def check_single(path: Path, rep: Report, jargon: list[str], terms: dict[str, list[str]]) -> dict:
    name = path.name
    rep.files.append(str(path))
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    is_readme = "readme" in path.name.lower()
    heads = headings(text)
    h1 = [h for h in heads if h[0] == 1]

    # H1：一份文档一个
    if len(h1) == 0:
        rep.add("FAIL", name, "全文", "没有 H1", "[规则] SKILL.md §6：一份文档一个 H1")
    elif len(h1) > 1:
        rep.add("FAIL", name, f"第 {h1[1][2]} 行", f"出现 {len(h1)} 个 H1：{', '.join(h[1] for h in h1)}",
                "[规则] SKILL.md §6：一份文档一个 H1")

    # 标题层级不跳级
    prev = 0
    for lvl, title, ln in heads:
        if prev and lvl > prev + 1:
            rep.add("WARN", name, f"第 {ln} 行", f"H{prev} 直接跳到 H{lvl}「{title[:24]}」",
                    "[规则] SKILL.md §6：不跳级")
        prev = lvl

    # 首屏行数：到第一个 H2 之前
    first_h2 = next((ln for lvl, _, ln in heads if lvl == 2), None)
    head_len = (first_h2 - 1) if first_h2 else len(lines)
    head_text = "\n".join(lines[:head_len])
    if is_readme and head_len > FIRST_SCREEN_LINES:
        rep.add("WARN", name, "首屏", f"首个 H2 之前有 {head_len} 行，超过 {FIRST_SCREEN_LINES} 行",
                f"[规则] SKILL.md §4：首屏约 {FIRST_SCREEN_LINES} 行内")
    if is_readme and not ACTION_PATTERN.search(head_text) and not JUMP_PATTERN.search(head_text):
        rep.add("WARN", name, "首屏", "没看到安装命令，也没有跳到安装的锚点",
                "[规则] SKILL.md §4：首屏要有动作或证据，或给出跳转")

    # 代码围栏成对
    if fences(text) % 2:
        rep.add("FAIL", name, "全文", f"代码围栏 {fences(text)} 个，不成对，后半篇会被吞进代码块",
                "[规则] Markdown 围栏必须成对")

    # $ 提示符
    if PROMPT_PATTERN.search(text):
        n = len(PROMPT_PATTERN.findall(text))
        rep.add("WARN", name, "命令块", f"{n} 处行首带 `$ `，复制时会带上提示符",
                "[规则] SKILL.md §6：不加可误复制的 $ 提示符")

    # 徽章数量
    n_badge = len(badges(strip_code(text)))
    if is_readme and n_badge > BADGE_MAX:
        rep.add("WARN", name, "首屏", f"{n_badge} 个徽章，超过 {BADGE_MAX} 个",
                f"[规则] SKILL.md §6：徽章 {2}–{BADGE_MAX} 个")

    # 锚点有效性
    slugs = set()
    for _, title, _ in heads:
        s = gh_slug(title)
        slugs.add(s)
    anchors = re.findall(r"\]\(#([^)]+)\)", strip_code(text))
    dead = []
    for a in anchors:
        a_norm = a.lower()
        if a_norm not in slugs and not any(s.startswith(a_norm) for s in slugs):
            dead.append(a)
    if dead:
        rep.add("FAIL", name, "页内锚点", f"指向不存在的标题: {', '.join('#' + d for d in dead[:4])}",
                "[实测] GitHub 锚点由标题小写、去标点、空格转连字符生成")

    # 术语
    body = strip_code(text)
    lower = body.lower()
    cjk_ratio = len(CJK_PATTERN.findall(body)) / max(len(body), 1)
    for term, variants in terms.items():
        found = [(v, count_word(body, v)) for v in variants]
        found = [(v, c) for v, c in found if c]
        if found:
            top = max(found, key=lambda x: x[1])
            rep.add("FAIL", name, "全文",
                    f"应统一用「{term}」，但出现 {', '.join(f'「{v}」×{c}' for v, c in found if c)}",
                    "[规则] SKILL.md §8：同一概念同一术语")
    for word in jargon:
        if cjk_ratio < 0.1:
            break
        cnt = count_word(body, word)
        if cnt:
            rep.add("WARN", name, "全文", f"出现「{word}」×{cnt}，多半是内行黑话",
                    "[规则] SKILL.md §8：删除内行黑话")

    plain = strip_code(text)
    return {
        "name": name,
        "lines": len(lines),
        "h1": len(h1),
        "h2": [t for lvl, t, _ in heads if lvl == 2],
        "fences": fences(text),
        "badges": n_badge,
        "anchors": len(anchors),
        "images": len(re.findall(r"!\[[^\]]*\]\(", plain)) + len(re.findall(r"<img\b", plain, re.I)),
        "first_screen_lines": head_len,
    }


# ---------------------------------------------------------------- 双语对照

def check_pair(a: Path, b: Path, ra: dict, rb: dict, rep: Report) -> None:
    label = f"{a.name} ↔ {b.name}"

    if len(ra["h2"]) != len(rb["h2"]):
        rep.add("FAIL", label, "章节", f"H2 数 {len(ra['h2'])} vs {len(rb['h2'])}，两版章节不对应",
                "[规则] SKILL.md §7：两版章节语义对应")
    if ra["fences"] != rb["fences"]:
        rep.add("WARN", label, "代码块", f"围栏数 {ra['fences']} vs {rb['fences']}",
                "[规则] SKILL.md §7：同步示例与安装分支")
    if ra["images"] != rb["images"]:
        rep.add("WARN", label, "图片", f"图片数 {ra['images']} vs {rb['images']}",
                "[规则] SKILL.md §7：翻译图注与替代文本，两版证据一致")
    if ra["badges"] != rb["badges"]:
        rep.add("WARN", label, "徽章", f"徽章数 {ra['badges']} vs {rb['badges']}",
                "[规则] SKILL.md §7：两版用途与状态一致")

    ta = a.read_text(encoding="utf-8", errors="replace")
    tb = b.read_text(encoding="utf-8", errors="replace")
    if b.name not in ta:
        rep.add("FAIL", label, "互链", f"{a.name} 里没有指向 {b.name} 的链接",
                "[规则] SKILL.md §7：两版顶部互链")
    if a.name not in tb:
        rep.add("FAIL", label, "互链", f"{b.name} 里没有指向 {a.name} 的链接",
                "[规则] SKILL.md §7：两版顶部互链")

    # 命令与包名应逐字相同
    def cmds(t: str) -> set[str]:
        blocks = re.findall(r"```[^\n]*\n(.*?)```", t, re.S)
        out = set()
        for blk in blocks:
            for line in blk.splitlines():
                s = line.strip()
                if s and not s.startswith("#") and COMMAND_PATTERN.match(s):
                    out.add(s)
        return out

    only_a = cmds(ta) - cmds(tb)
    only_b = cmds(tb) - cmds(ta)
    if only_a or only_b:
        detail = []
        if only_a:
            detail.append(f"仅 {a.name}: {list(only_a)[0][:50]}")
        if only_b:
            detail.append(f"仅 {b.name}: {list(only_b)[0][:50]}")
        rep.add("WARN", label, "命令", "两版命令不一致，" + "；".join(detail),
                "[规则] SKILL.md §7：原样保留命令、参数、包名")


# ---------------------------------------------------------------- 术语表

def load_terms(path: Path) -> dict[str, list[str]]:
    """格式：首选词 | 变体1, 变体2   （# 开头为注释）"""
    terms: dict[str, list[str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "|" not in line:
            continue
        canonical, variants = line.split("|", 1)
        terms[canonical.strip()] = [v.strip() for v in variants.split(",") if v.strip()]
    return terms


# ---------------------------------------------------------------- 自测

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def selftest() -> int:
    ok = True

    # 1. 合格的 README 不应有 FAIL
    good = FIXTURES / "text" / "good.md"
    if good.exists():
        rep = Report()
        check_single(good, rep, DEFAULT_JARGON, {})
        got = 1 if rep.fails else 0
        print(f"{'✓' if got == 0 else '✗'} good     期望退出码 0，实际 {got}")
        if got:
            ok = False
            for f in rep.fails:
                print("   ", f.render())

    # 2. 坏样本必须命中全部规则
    bad = FIXTURES / "text" / "broken.md"
    if bad.exists():
        rep = Report()
        check_single(bad, rep, DEFAULT_JARGON, {"首屏": ["hero", "主视觉"]})
        got = 1 if rep.fails else 0
        print(f"{'✓' if got == 1 else '✗'} broken   期望退出码 1，实际 {got}")
        if got != 1:
            ok = False
        else:
            print(f"   命中 {len(rep.fails)} 个 FAIL / {len(rep.warns)} 个 WARN")
            for f in rep.fails:
                print("   ✗", f.where, f.detail[:50])

    # 3. 双语对照
    zh, en = FIXTURES / "text" / "pair-zh.md", FIXTURES / "text" / "pair-en.md"
    if zh.exists() and en.exists():
        rep = Report()
        ra = check_single(zh, rep, [], {})
        rb = check_single(en, rep, [], {})
        check_pair(zh, en, ra, rb, rep)
        got = 1 if rep.fails else 0
        print(f"{'✓' if got == 1 else '✗'} pair     期望退出码 1（故意漏互链），实际 {got}")
        if got != 1:
            ok = False

    print()
    print("自测通过" if ok else "自测失败")
    return 0 if ok else 1


# ---------------------------------------------------------------- 入口

def main(argv: list[str]) -> int:
    flags = {a for a in argv[1:] if a.startswith("--")}
    args = [a for a in argv[1:] if not a.startswith("--")]

    if "--selftest" in flags:
        return selftest()

    terms: dict[str, list[str]] = {}
    if "--terms" in argv:
        idx = argv.index("--terms")
        if idx + 1 >= len(argv):
            print("--terms 后面要给文件路径", file=sys.stderr)
            return 2
        tp = Path(argv[idx + 1])
        if not tp.exists():
            print(f"找不到术语表: {tp}", file=sys.stderr)
            return 2
        terms = load_terms(tp)
        args = [a for a in args if a != argv[idx + 1]]

    if not args:
        print(__doc__)
        return 2

    paths = []
    for raw in args:
        p = Path(raw)
        if not p.exists():
            print(f"找不到文件: {raw}", file=sys.stderr)
            return 2
        paths.append(p)

    rep = Report()
    info = {}
    for p in paths:
        info[p.name] = check_single(p, rep, DEFAULT_JARGON, terms)

    if "--pair" in flags and len(paths) == 2:
        check_pair(paths[0], paths[1], info[paths[0].name], info[paths[1].name], rep)

    if "--json" in flags:
        print(json.dumps({
            "files": info,
            "findings": [f.__dict__ for f in rep.findings],
            "fails": len(rep.fails), "warns": len(rep.warns),
        }, ensure_ascii=False, indent=2))
        return 1 if rep.fails else 0

    print(f"扫描 {len(paths)} 份文件\n")
    for name, d in info.items():
        print(f"{name}: {d['lines']} 行, H1 {d['h1']}, H2 {len(d['h2'])}, "
              f"围栏 {d['fences']}, 徽章 {d['badges']}, 图 {d['images']}, 首屏 {d['first_screen_lines']} 行")
    print()

    order = {"FAIL": 0, "WARN": 1, "INFO": 2}
    for f in sorted(rep.findings, key=lambda x: (order[x.level], x.file)):
        print(f.render())

    if not rep.findings:
        print("没有发现问题。")
    print()
    print(f"FAIL {len(rep.fails)} 项，WARN {len(rep.warns)} 项")
    if rep.fails:
        print("exit 1：有必须修的项")
        return 1
    print("exit 0：结构没有硬伤")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
