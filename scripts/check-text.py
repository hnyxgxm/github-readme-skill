#!/usr/bin/env python3
"""检查 README 的文字结构：首屏、锚点、双语对照、术语一致。

只判能机械验证的部分。判断"这段写得好不好"不在脚本范围内。

用法:
    python3 <技能目录>/scripts/check-text.py README.md
    python3 <技能目录>/scripts/check-text.py README.md README.en.md --pair
    python3 <技能目录>/scripts/check-text.py README.md --terms <技能目录>/references/terms.txt
    python3 <技能目录>/scripts/check-text.py --selftest

注意：脚本要在目标仓库里跑，但脚本自身要按绝对路径调用。
<技能目录> 是这份 Skill 的安装位置，例如 ~/.claude/skills/github-readme-skill。
直接写 scripts/check-text.py 只在本仓库内成立，装成 Skill 后工作目录是别人的仓库，会找不到文件。

退出码: 0 = 没有 FAIL, 1 = 有 FAIL, 2 = 用法或路径错误

判据来源:
  [规则] SKILL.md 里的明文规定，附章节号
  [经验] 页面版式的工程阈值
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote

# 技能安装目录，用来定位 fixtures、terms 和自测样本
SKILL_DIR = Path(__file__).resolve().parent.parent
# 术语表放在 references/ 里：那三个目录是技能结构里保证会被打包的部分，
# 放根目录时，只留 SKILL.md / scripts / references / assets 的安装器会把它裁掉。
TERMS_HINT = SKILL_DIR / "references" / "terms.txt"

# 围栏和行内代码的识别规则与 check-assets.py 共用同一份，
# 两个脚本各抄一份时，改一处忘另一处就会让同一段 Markdown 得出相反结论。
# 关掉字节码缓存：技能可能装在只读目录，也不该往安装目录里写 __pycache__。
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from readme_md import (  # noqa: E402
    code_only,
    fence_mask,
    fence_unclosed,
    strip_code,
)

# [规则] SKILL.md §4：首屏控制在约 25 行以内。
# 两个用途分开：判"首屏有没有动作"用前 25 行；判"首屏是不是太长"用首个 H2 之前的行数。
FIRST_SCREEN_LINES = 25

# [规则] SKILL.md §4：徽章最多 7 个，功能性优先。
# 脚本只判上限；0 个也可以用出处或赞助信息替代，不按下限扣分。
BADGE_MAX = 7

# [规则] SKILL.md §8：删除内行黑话。词表按项目补充，不要指望它覆盖全部。
DEFAULT_JARGON = [
    "hero", "above the fold", "CTA", "onboarding", "KPI", "ROI", "MVP",
    "pain point", "核心抓手", "闭环", "赋能", "对齐颗粒度", "心智模型",
]

# [规则] SKILL.md §6：不加可误复制的 $ 提示符
PROMPT_PATTERN = re.compile(r"^\s*\$ \S", re.M)

# [经验] 首屏给下载包或 releases 链接，也算给了动作
DOWNLOAD_PATTERN = re.compile(
    r"\]\([^)\s]*(?:\.(?:dmg|pkg|zip|exe|apk|msi)|/releases(?:/|\)))[^)\s]*\)", re.I)

# [规则] SKILL.md §4 还允许「在线入口」。只认链接文字点明在线试用的外链，
# 否则首屏放个仓库或文档链接也会算动作。
# 不收裸 demo：`[Demo 视频](youtu.be/...)` 是片子，不是能上手试的入口。
ONLINE_PATTERN = re.compile(
    r"\[[^\]]*(?:在线|试用|体验|playground|live demo|demo site|try it|try online|sandbox)[^\]]*\]"
    r"\(https?://[^)\s]+\)", re.I)

# [规则] SKILL.md §4：安装排在第 4 节之后时，首屏必须给锚点跳转。
# 有跳转就不算"首屏没有动作"。锚点可能是百分号编码，匹配前先 unquote。
JUMP_PATTERN = re.compile(
    r"\]\(#(?:安装|使用|开始|快速开始|下载|install|usage|setup|get-?started|"
    r"quick-?start|getting-?started)[^)]*\)", re.I)

# [规则] 同上的安装节判定：安装词出现在标题里就算（「用 Homebrew 安装」也是安装节）。
# 英文加词首词尾边界，Uninstalling 不算；中文「卸载」不含「安装」，天然不误中。
INSTALL_HEADING = re.compile(
    r"安装|下载|快速开始|快速上手|"
    r"(?<![A-Za-z])(?:install(?:ation|ing)?|setup|getting[- ]?started|quick[- ]?start)(?![A-Za-z])",
    re.I)

# [经验] 只在中文文档上跑黑话扫描：onboarding 这类词在英文原文里是正常用词。
CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]")

# [规则] SKILL.md §6：H2 用行业通用专业词汇，不写成口头语句。
# 只查 README；技能自身的 SKILL.md / references 有说明性长标题，不适用。
COLLOQUIAL_H2_RE = re.compile(r"它|谁|里头|咱们|啥|看一下|试试|怎么办")

# [规则] SKILL.md §5、§6：仓库文件清单是开发细节，不进 README。
# 这类标题下面必然是一份文件树或脚本清单，所以按标题判，不去猜正文。
# 单说「目录」不算：教程类的章节目录是正当用法，有歧义的不报。
FILE_TREE_TITLES = {
    "目录结构", "文件结构", "文件清单", "文件树",
    "仓库结构", "仓库目录", "仓库文件", "项目结构", "项目目录",
}
FILE_TREE_TITLES_EN = {
    "contents", "project structure", "repository structure", "repository layout",
    "repo layout", "repo structure", "file structure", "file tree",
    "folder structure", "directory structure",
}
FILE_TREE_ISSUE = "是仓库文件清单，属于开发细节，不进 README"


def heading_wording_issues(title: str) -> list[str]:
    """§6：标题是索引，不是句子。返回这个 H2 的用词问题。"""
    out = []
    if COLLOQUIAL_H2_RE.search(title):
        out.append("用了口头语")
    if len(CJK_PATTERN.findall(title)) > 8:
        out.append("太长，像一句话")
    if title.strip() in FILE_TREE_TITLES or title.strip().lower() in FILE_TREE_TITLES_EN:
        out.append(FILE_TREE_ISSUE)
    return out

# 只把真命令拿来对照，避免把自然语言示例当成命令不一致。
# 首屏判"有没有可复制的动作"也用它，所以覆盖常见包管理器，
# 但不含 cd / export / mkdir 这类单独出现时说明不了安装的指令。
COMMAND_PATTERN = re.compile(
    r"^(?:npx|npm|pnpm|yarn|bunx?|brew|pip|pip3|pipx|uv|uvx|poetry|conda|cargo|rustup|go|gem|"
    r"composer|dotnet|deno|winget|choco|scoop|apt|apt-get|snap|flatpak|mas|"
    r"git clone|curl|wget|docker|podman|python|python3|node|sh|bash|zsh|make|swift)\b")

# 徽章不只是 shields.io：GitHub Actions、badge.fury、badgen 都算
BADGE_URL = re.compile(
    r"(?:shields\.io|badge\.fury\.io|badgen\.net|badge\.buildkite\.com|/badge\.(?:svg|png))", re.I)

# Logo、图标、头像属于 §4 第 1 条的身份材料，不算"能说明关系的图"
LOGO_HINT = re.compile(
    r"(?:^|[/_.\-])(?:logo|logotype|wordmark|icon|favicon|avatar|brand)(?:[/_.\-]|$)", re.I)

# 页内锚点：排除标题语法里的 "title"，否则 ](#install "跳到安装") 会把 title 当成锚点
ANCHOR_RE = re.compile(r"\]\(\s*#([^)\s\"']+)")
# 手写锚点 <a name="x"> / <a id="x">，GitHub 会保留它们
HTML_ANCHOR_RE = re.compile(r"<a\b[^>]*\b(?:name|id)\s*=\s*[\"']([^\"']+)[\"']", re.I)

# 围栏与行内代码怎么认，见同目录 readme_md.py。


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

    def add(self, level, file, where, detail, basis):
        self.findings.append(Finding(level, file, where, detail, basis))

    @property
    def fails(self):
        return [f for f in self.findings if f.level == "FAIL"]

    @property
    def warns(self):
        return [f for f in self.findings if f.level == "WARN"]


# ---------------------------------------------------------------- 判据

def has_runnable(text: str) -> bool:
    """首屏里有没有能直接复制的命令。

    只看代码里"行首就是命令"的行。JSON 字符串、注释、日志输出里出现
    "npm i -g x" 这种字样不算，否则任意配置块或说明块都能冒充安装命令。
    """
    code = code_only(text)
    for line in code.splitlines():
        s = line.strip().lstrip("$").strip()
        if s.startswith("sudo "):
            s = s[5:].lstrip()
        if not s or s[0] in "#/\"'{[<>+*-|":
            continue
        if COMMAND_PATTERN.match(s):
            return True
    return False


def strip_refs(text: str) -> str:
    """去掉链接目标、裸 URL 和 HTML 标签，只留读者会读到的字。

    docs/hero.png 里的 hero 是文件名，不是正文用词；
    早期版本直接扫全文，合规 README 只要用了 hero.png 就会被判内行黑话。
    """
    text = re.sub(r"\]\(\s*[^)]*\)", "]", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return text


def headings(text: str) -> list[tuple[int, str, int]]:
    """返回 (级别, 标题, 行号)，跳过代码围栏内的 #。"""
    lines = text.splitlines()
    mask = fence_mask(lines)
    out = []
    for i, (line, in_fence) in enumerate(zip(lines, mask), 1):
        if in_fence:
            continue
        m = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if m:
            out.append((len(m.group(1)), m.group(2).strip(), i))
    return out


def gh_slug(title: str) -> str:
    """按 GitHub 生成标题锚点的规则：小写、去标点、每个空格换一个连字符。

    连续连字符不合并：「Privacy — exactly」删掉破折号后剩两个空格，
    GitHub 生成 privacy--exactly（线上锚点 user-content-privacy--exactly-what-it-reads 实测）。
    """
    s = title.strip().lower()
    s = re.sub(r"[^\w\u4e00-\u9fff \-]", "", s)
    return s.replace(" ", "-")


def gh_slugs(heads: list[tuple[int, str, int]]) -> set[str]:
    """生成全部锚点，重名标题按 GitHub 规则加 -1、-2 后缀。"""
    seen: dict[str, int] = {}
    out = set()
    for _, title, _ in heads:
        base = gh_slug(title)
        n = seen.get(base, 0)
        seen[base] = n + 1
        out.add(base if n == 0 else f"{base}-{n}")
    return out


def count_word(text: str, word: str) -> int:
    """英文按词边界计数。子串匹配会让 CTA 命中 re-cta-ngle 这类词。"""
    if re.fullmatch(r"[A-Za-z0-9 \-]+", word):
        return len(re.findall(rf"(?<![A-Za-z]){re.escape(word)}(?![A-Za-z])", text, re.I))
    return text.count(word)


def badges(text: str) -> list[str]:
    """数功能性徽章。不只 shields.io：GitHub Actions、badge.fury、badgen 也算。

    早期只认 shields.io，CI 徽章和包管理器徽章都数不到，
    "超过 7 个"与双语徽章数不一致都会漏报。
    """
    md = [url for _, url in re.findall(r"!\[([^\]]*)\]\((https?://[^)\s]+)\)", text)]
    html = re.findall(r"<img\b[^>]*\bsrc\s*=\s*[\"'](https?://[^\"']+)[\"']", text, re.I)
    return [url for url in md + html if BADGE_URL.search(url)]


def has_evidence_image(text: str) -> bool:
    """§4 允许用一张能说明关系的图代替动作。

    徽章只是信任标记，Logo 属于 §4 第 1 条的身份材料，
    两者都不回答"它长什么样、能干什么"，不能顶替证据。
    """
    md = re.findall(r"!\[[^\]]*\]\(\s*<?([^)\s>]+)", text)
    html = re.findall(r"<img\b[^>]*\bsrc\s*=\s*[\"']([^\"']+)[\"']", text, re.I)
    for url in md + html:
        if BADGE_URL.search(url) or LOGO_HINT.search(url):
            continue
        return True
    return False


def head_window(lines: list[str]) -> tuple[int, str]:
    """首屏检测窗口：前 FIRST_SCREEN_LINES 行。

    SKILL.md §4 把首屏定为「约 25 行」，没有规定它必须止于第一个 H2。
    早期版本把窗口卡在首个 H2 之前，比 §4 的行数窄，
    安装命令落在 H2 之后时就会一直报"首屏没有动作"。
    """
    upto = min(len(lines), FIRST_SCREEN_LINES)
    return upto, "\n".join(lines[:upto])


# ---------------------------------------------------------------- 单文件检查

# ---------------------------------------------------------------- 版本声明核对

# [规则] SKILL.md §5、§8：README 写的版本与系统下限，要能在仓库里找到出处。
# 只认「技术名 + 数字 + 下限写法」的组合，避免把发布记录里的普通版本号当成安装要求。
# 行内已经给出链接或注明来源的跳过：作者指过出处，就不必再去仓库里找。
VERSION_CLAIM_RE = re.compile(
    r"(?P<tech>Node(?:\.js)?|node(?:\.js)?|Python|python|Golang|Go|go|Rust|rust"
    r"|Swift|swift|Ruby|ruby|Java|java|macOS|MacOS|iOS|IOS)"
    r"\s*(?:版本)?\s*(?P<op>>=|≥|不低于|至少|要求|需要)?\s*v?"
    r"(?P<ver>\d+(?:\.\d+){0,2})\s*"
    r"(?P<tail>\+|以上|及以上|或更高|or later|or above)?"
)
LOWER_BOUND_OPS = {">=", "≥", "不低于", "至少", "要求", "需要"}
SOURCE_HINTS_RE = re.compile(r"https?://|出处|来源|依据|官方|source", re.I)


def _read_soft(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _versions_in(s: str) -> list[str]:
    return re.findall(r"\d+(?:\.\d+){0,2}", s)


def _repo_root(readme: Path) -> Path:
    """README 可能在仓库根，也可能在 packages/x/ 下，向上找一层就够。"""
    start = readme.parent.resolve()
    marks = (".git", "package.json", "pyproject.toml", "Cargo.toml",
             "Package.swift", "go.mod", "setup.py", "pom.xml")
    for cand in [start] + list(start.parents)[:3]:
        if any((cand / m).exists() for m in marks):
            return cand
    return start


def _ci_matrix(root: Path, key: str):
    wf = root / ".github" / "workflows"
    if not wf.is_dir():
        return None
    pat = re.compile(key + r"\s*:\s*\[?([^\n\]}]*)")
    for f in sorted(list(wf.glob("*.yml")) + list(wf.glob("*.yaml"))):
        m = pat.search(_read_soft(f))
        if m:
            nums = _versions_in(m.group(1))
            if nums:
                return nums, f".github/workflows/{f.name}"
    return None


def _evidence(tech: str, root: Path):
    """返回 (仓库里写的版本号列表, 出处)，找不到依据返回 None。"""
    t = tech.lower()
    if t.startswith("node"):
        pkg = root / "package.json"
        if pkg.is_file():
            try:
                data = json.loads(_read_soft(pkg) or "{}")
            except ValueError:
                data = {}
            eng = data.get("engines") if isinstance(data, dict) else None
            if isinstance(eng, dict) and isinstance(eng.get("node"), str):
                return _versions_in(eng["node"]), "package.json engines.node"
        for name in (".nvmrc", ".node-version"):
            f = root / name
            if f.is_file():
                nums = _versions_in(_read_soft(f))
                if nums:
                    return nums, name
        return _ci_matrix(root, "node-version")
    if t == "python":
        py = root / "pyproject.toml"
        if py.is_file():
            m = re.search(r"requires-python\s*=\s*[\"']([^\"']+)", _read_soft(py))
            if m:
                return _versions_in(m.group(1)), "pyproject.toml requires-python"
        for name in ("setup.py", "setup.cfg"):
            f = root / name
            if f.is_file():
                m = re.search(r"python_requires\s*=\s*[\"']([^\"']+)", _read_soft(f))
                if m:
                    return _versions_in(m.group(1)), name
        f = root / ".python-version"
        if f.is_file():
            nums = _versions_in(_read_soft(f))
            if nums:
                return nums, ".python-version"
        return _ci_matrix(root, "python-version")
    if t in ("go", "golang"):
        gm = root / "go.mod"
        if gm.is_file():
            m = re.search(r"^go\s+(\S+)", _read_soft(gm), re.M)
            if m:
                return _versions_in(m.group(1)), "go.mod"
        return None
    if t == "rust":
        ct = root / "Cargo.toml"
        if ct.is_file():
            m = re.search(r"rust-version\s*=\s*[\"']([^\"']+)", _read_soft(ct))
            if m:
                return _versions_in(m.group(1)), "Cargo.toml rust-version"
        return None
    if t in ("macos", "ios"):
        ps = root / "Package.swift"
        if ps.is_file():
            m = re.search(r"\.(?:macOS|iOS)\((?:\.v(\d+)|[\"']([\d.]+)[\"'])\)", _read_soft(ps))
            if m:
                return _versions_in(m.group(1) or m.group(2)), "Package.swift platforms"
        plist = root / "Info.plist"
        if plist.is_file():
            m = re.search(r"LSMinimumSystemVersion</key>\s*<string>([\d.]+)", _read_soft(plist))
            if m:
                return _versions_in(m.group(1)), "Info.plist LSMinimumSystemVersion"
        return None
    if t == "swift":
        ps = root / "Package.swift"
        if ps.is_file():
            m = re.search(r"swift-tools-version\s*:\s*([\d.]+)", _read_soft(ps))
            if m:
                return _versions_in(m.group(1)), "Package.swift swift-tools-version"
        return None
    if t == "ruby":
        f = root / ".ruby-version"
        if f.is_file():
            nums = _versions_in(_read_soft(f))
            if nums:
                return nums, ".ruby-version"
        for g in sorted(root.glob("*.gemspec")):
            m = re.search(r"required_ruby_version\s*=\s*[\"']([^\"']+)", _read_soft(g))
            if m:
                return _versions_in(m.group(1)), f"{g.name} required_ruby_version"
        return None
    if t == "java":
        pom = root / "pom.xml"
        if pom.is_file():
            m = re.search(r"<(?:java\.version|maven\.compiler\.source)>([\d.]+)<", _read_soft(pom))
            if m:
                return _versions_in(m.group(1)), "pom.xml"
        for g in sorted(root.glob("build.gradle*")):
            m = re.search(r"sourceCompatibility\s*=?\s*[\"']?([\d.]+)", _read_soft(g))
            if m:
                return _versions_in(m.group(1)), g.name
        return None
    return None


def _version_fits(claim: str, evidence: list[str]) -> bool:
    """22.20 与 >=22.20.0 算一致；3.11 与 >=3.9 不算。"""
    for ev in evidence:
        if claim == ev or ev.startswith(claim) or claim.startswith(ev):
            return True
    return False


def version_claim_issues(readme: Path) -> list[tuple[int, str, str, object]]:
    root = _repo_root(readme)
    out, seen = [], set()
    for i, line in enumerate(_read_soft(readme).splitlines(), 1):
        if SOURCE_HINTS_RE.search(line):
            continue
        for m in VERSION_CLAIM_RE.finditer(line):
            if m.group("op") not in LOWER_BOUND_OPS and not m.group("tail"):
                continue
            tech, ver = m.group("tech"), m.group("ver")
            key = (tech.lower(), ver)
            if key in seen:
                continue
            seen.add(key)
            out.append((i, tech, ver, _evidence(tech, root)))
    return out


def check_single(path: Path, rep: Report, jargon: list[str], terms: dict[str, list[str]]) -> dict:
    name = path.name
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

    # 标题用词：只查 README；技能自身的说明性长标题不受这条约束
    if is_readme:
        for lvl, title, ln in heads:
            if lvl == 2:
                for issue in heading_wording_issues(title):
                    reason = ("[规则] SKILL.md §5：项目结构、目录清单不进 README"
                              if issue == FILE_TREE_ISSUE
                              else "[规则] SKILL.md §6：H2 用行业通用专业词汇")
                    rep.add("WARN", name, f"第 {ln} 行",
                            f"二级标题「{title}」{issue}", reason)

    # 首屏长度：到第一个 H2 之前的行数就是读者滚屏前会看到的内容量
    first_h2 = next((ln for lvl, _, ln in heads if lvl == 2), None)
    screen_len = (first_h2 - 1) if first_h2 else len(lines)
    if is_readme and screen_len > FIRST_SCREEN_LINES:
        rep.add("WARN", name, "首屏", f"首个 H2 之前有 {screen_len} 行，超过 {FIRST_SCREEN_LINES} 行",
                f"[规则] SKILL.md §4：首屏约 {FIRST_SCREEN_LINES} 行内")

    # 首屏有没有动作：只认代码里的命令、下载链接、跳到安装的锚点。
    # 散文里出现"安装"不算；代码块里是 JSON 输出、diff 或配置也不算。
    win_len, win_text = head_window(lines)
    win_plain = strip_code(win_text)
    has_action = bool(
        has_runnable(win_text)
        or DOWNLOAD_PATTERN.search(win_plain)
        or ONLINE_PATTERN.search(win_plain)
        or JUMP_PATTERN.search(unquote(win_plain))
        or has_evidence_image(win_plain)
    )
    if is_readme and not has_action:
        rep.add("WARN", name, "首屏",
                f"前 {win_len} 行内没有安装命令、下载或在线入口、说明图或跳到安装的锚点",
                "[规则] SKILL.md §4：首屏要有动作或证据，或给出跳转")

    # 安装节排在第 4 节之后时，首屏必须能跳到安装；首屏直接放了可复制命令则无需跳转。
    # 有图就算"有动作"放行的是上一条，这条单独查，否则安装埋深永远漏报。
    h2_titles = [t for lvl, t, _ in heads if lvl == 2]
    install_pos = next((i for i, t in enumerate(h2_titles) if INSTALL_HEADING.search(t)), None)
    if is_readme and install_pos is not None and install_pos >= 4:
        install_slugs = {gh_slug(t) for t in h2_titles if INSTALL_HEADING.search(t)}
        win_anchors = {unquote(a).strip().lower().replace(" ", "-")
                       for a in ANCHOR_RE.findall(win_plain)}
        if not (win_anchors & install_slugs) and not has_runnable(win_text):
            rep.add("WARN", name, "首屏",
                    f"安装排在第 {install_pos + 1} 节，前 {win_len} 行没有跳到安装的锚点",
                    "[规则] SKILL.md §4：安装排在第 4 节之后时，首屏必须给出跳转")

    # 代码围栏成对：按长度配对后仍没关上才算
    if fence_unclosed(text):
        rep.add("FAIL", name, "全文", "代码围栏没有闭合，后半篇会被吞进代码块",
                "[规则] Markdown 围栏必须成对")

    # $ 提示符
    if PROMPT_PATTERN.search(text):
        n = len(PROMPT_PATTERN.findall(text))
        rep.add("WARN", name, "命令块", f"{n} 处行首带 `$ `，复制时会带上提示符",
                "[规则] SKILL.md §6：不加可误复制的 $ 提示符")

    # 正文（已剥围栏与行内代码），后续检查都用它
    body = strip_code(text)

    # 徽章数量
    n_badge = len(badges(body))
    if is_readme and n_badge > BADGE_MAX:
        rep.add("WARN", name, "首屏", f"{n_badge} 个徽章，超过 {BADGE_MAX} 个",
                f"[规则] SKILL.md §4：徽章不超过 {BADGE_MAX} 个")

    # 版本与系统下限：写进 README 的数字要能在仓库里找到出处，写高了比没写更糟
    if is_readme:
        for ln, tech, ver, ev in version_claim_issues(path):
            if ev is None:
                rep.add("WARN", name, f"第 {ln} 行",
                        f"提到 {tech} {ver}，仓库里找不到对应依据",
                        "[提示] SKILL.md §5：补上出处（package.json、pyproject.toml、CI 矩阵等），"
                        "或说明这是外部工具的额外要求")
            elif not _version_fits(ver, ev[0]):
                rep.add("WARN", name, f"第 {ln} 行",
                        f"README 写 {tech} {ver}，{ev[1]} 里是 {'/'.join(ev[0][:3])}",
                        "[规则] SKILL.md §5：版本要求以仓库里写的为准，写高了会让人以为装不了")

    # 锚点有效性：严格匹配，不解码会把 GitHub 复制来的编码锚点判死；
    # 手写 <a name> / <a id> 也是合法锚点，从正文里补进候选。
    slugs = gh_slugs(heads)
    slugs |= {
        unquote(m.group(1)).strip().lower().replace(" ", "-")
        for m in HTML_ANCHOR_RE.finditer(body)
    }
    anchors = ANCHOR_RE.findall(body)
    dead = []
    for a in anchors:
        a_norm = unquote(a).strip().lower().replace(" ", "-")
        if a_norm not in slugs:
            dead.append(a)
    if dead:
        rep.add("FAIL", name, "页内锚点", f"指向不存在的标题: {', '.join('#' + d for d in dead[:4])}",
                "[实测] GitHub 锚点由标题小写、去标点、每个空格转一个连字符生成（连续连字符不合并），重名标题追加 -1")

    # 术语：词表是这份 Skill 的内部口径，用户文档里出现变体只提示，不算必须修
    prose = strip_refs(body)
    cjk_ratio = len(CJK_PATTERN.findall(prose)) / max(len(prose), 1)
    for term, variants in terms.items():
        found = [(v, count_word(prose, v)) for v in variants]
        found = [(v, c) for v, c in found if c]
        if found:
            rep.add("WARN", name, "全文",
                    f"术语表建议统一用「{term}」，但出现 {', '.join(f'「{v}」×{c}' for v, c in found)}",
                    "[提示] 词表来自 --terms，属于写作者自己的口径，不是平台规定")
    if cjk_ratio >= 0.1:
        for word in jargon:
            cnt = count_word(prose, word)
            if cnt:
                rep.add("WARN", name, "全文", f"出现「{word}」×{cnt}，多半是内行黑话",
                        "[规则] SKILL.md §8：删除内行黑话")

    mask = fence_mask(lines)
    return {
        "name": name,
        "lines": len(lines),
        "h1": len(h1),
        "h2": [t for lvl, t, _ in heads if lvl == 2],
        "fences": sum(1 for i, m in enumerate(mask) if m and (i == 0 or not mask[i - 1])),
        "badges": n_badge,
        "anchors": len(anchors),
        "images": len(re.findall(r"!\[[^\]]*\]\(", body)) + len(re.findall(r"<img\b", body, re.I)),
        "first_screen_lines": screen_len,
    }


# ---------------------------------------------------------------- 双语对照

def strip_shell_comment(s: str) -> str:
    """剥 shell 行尾注释：只切引号外、前面是空白的 #。

    §7 允许说明自然改写，注释翻译不同不构成命令不一致；命令本身仍逐字比对。
    """
    quote = ""
    for i, ch in enumerate(s):
        if quote:
            if ch == quote:
                quote = ""
        elif ch in ("'", '"'):
            quote = ch
        elif ch == "#" and (i == 0 or s[i - 1].isspace()):
            return s[:i].rstrip()
    return s.rstrip()


def check_pair(a: Path, b: Path, ra: dict, rb: dict, rep: Report) -> None:
    label = f"{a.name} ↔ {b.name}"

    diff = len(ra["h2"]) - len(rb["h2"])
    if abs(diff) >= 2:
        rep.add("FAIL", label, "章节", f"H2 数 {len(ra['h2'])} vs {len(rb['h2'])}，两版章节不对应",
                "[规则] SKILL.md §7：两版章节语义对应")
    elif diff:
        rep.add("WARN", label, "章节",
                f"H2 数 {len(ra['h2'])} vs {len(rb['h2'])}，差 {abs(diff)} 节；"
                f"多一节可能是 License 这类正常差异，人工确认语义对应即可",
                "[规则] SKILL.md §7：两版章节语义对应，不强求数量相等")
    if ra["fences"] != rb["fences"]:
        rep.add("WARN", label, "代码块", f"代码块数 {ra['fences']} vs {rb['fences']}",
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
                s = strip_shell_comment(line.strip())
                if s and COMMAND_PATTERN.match(s):
                    out.add(s)
        return out

    only_a = cmds(ta) - cmds(tb)
    only_b = cmds(tb) - cmds(ta)
    if only_a or only_b:
        detail = []
        if only_a:
            detail.append(f"仅 {a.name}: {sorted(only_a)[0][:50]}")
        if only_b:
            detail.append(f"仅 {b.name}: {sorted(only_b)[0][:50]}")
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

FIXTURES = SKILL_DIR / "scripts" / "fixtures"


NEEDED_FIXTURES = (
    "text/good.md",
    "text/broken.md",
    "text/pair-zh.md",
    "text/pair-en.md",
    "text/anchors.md",
)


def selftest() -> int:
    # 样本缺失必须报错。早期版本把每条用例套在 if exists 里，
    # 打包器丢掉 fixtures 后整个自测会静默通过，CI 上显示绿勾。
    # 清单要覆盖下面每一处用到样本的地方，漏一个就是裸 traceback。
    missing = [rel for rel in NEEDED_FIXTURES if not (FIXTURES / rel).exists()]
    if missing:
        print(f"✗ 缺少自测样本，无法确认脚本行为: {', '.join(missing)}", file=sys.stderr)
        print(f"  样本应在 {FIXTURES}，检查打包时是否把它漏掉了。", file=sys.stderr)
        return 1

    ok = True

    # 1. 合格的 README 不应有 FAIL
    rep = Report()
    check_single(FIXTURES / "text" / "good.md", rep, DEFAULT_JARGON, {})
    got = 1 if rep.fails else 0
    print(f"{'✓' if got == 0 else '✗'} good     期望退出码 0，实际 {got}")
    if got:
        ok = False
        for f in rep.fails:
            print("   ", f.render())

    # 2. 坏样本必须命中全部规则
    rep = Report()
    check_single(FIXTURES / "text" / "broken.md", rep, DEFAULT_JARGON, {"首屏": ["hero", "主视觉"]})
    got = 1 if rep.fails else 0
    print(f"{'✓' if got == 1 else '✗'} broken   期望退出码 1，实际 {got}")
    if got != 1:
        ok = False
    else:
        print(f"   命中 {len(rep.fails)} 个 FAIL / {len(rep.warns)} 个 WARN")
        for f in rep.fails:
            print("   ✗", f.where, f.detail[:50])

    # 3. 双语对照：互链缺失要 FAIL；翻译注释不算命令差异，围栏按块数比
    zh, en = FIXTURES / "text" / "pair-zh.md", FIXTURES / "text" / "pair-en.md"
    rep = Report()
    ra = check_single(zh, rep, [], {})
    rb = check_single(en, rep, [], {})
    check_pair(zh, en, ra, rb, rep)
    got = 1 if rep.fails else 0
    print(f"{'✓' if got == 1 else '✗'} pair     期望退出码 1（故意漏互链），实际 {got}")
    if got != 1:
        ok = False
    cmd_diff = [f for f in rep.warns if f.where == "命令"]
    pair_precise = (len(cmd_diff) == 1 and "npm i example" in cmd_diff[0].detail
                    and "npx example scan" not in cmd_diff[0].detail
                    and not any(f.where == "代码块" for f in rep.warns))
    print(f"{'✓' if pair_precise else '✗'} pair-cmd 注释翻译不算差异，只抓 npm i example；块数相同不报围栏")
    if not pair_precise:
        ok = False

    # 4. 解析器本身的回归：四反引号块里的内容不能被当成正文
    probe = (
        "# 标题\n\n"
        "````markdown\n"
        "## 示例里的标题\n\n"
        "![坏图](nope/ghost.png)\n"
        "```sh\nnpm i\n```\n"
        "````\n\n"
        "## 真章节\n\n正文。\n"
    )
    heads = headings(probe)
    n_h2 = len([h for h in heads if h[0] == 2])
    fences_ok = not fence_unclosed(probe)
    print(f"{'✓' if n_h2 == 1 and fences_ok else '✗'} fence    四反引号块里的标题应被忽略"
          f"（H2={n_h2}，围栏闭合={fences_ok}）")
    if not (n_h2 == 1 and fences_ok):
        ok = False

    # 5. 锚点：编码形式要认，前缀不算命中，链接标题与手写锚点不算死链
    rep = Report()
    probe_md = FIXTURES / "text" / "anchors.md"
    check_single(probe_md, rep, [], {})
    dead_tokens: set[str] = set()
    for f in rep.fails:
        if "锚点" in f.where:
            tail = f.detail.split(": ", 1)[-1]
            dead_tokens |= {t.strip().lstrip("#") for t in tail.split(",")}
    want_dead = {"install", "ghost", "privacy-exactly-what-it-reads"}
    print(f"{'✓' if dead_tokens == want_dead else '✗'} anchor   只该抓 #install、#ghost 与单连字符变体"
          f"（实际抓到 {sorted(dead_tokens)}）")
    if dead_tokens != want_dead:
        ok = False

    # 6. 首屏：代码里的命令字样不算动作，真命令、说明图、跳转算
    screen_cases = [
        ("json",    '# T\n\n一句话。\n\n```json\n{"cmd": "npm i -g x"}\n```\n', True),
        ("comment", '# T\n\n一句话。\n\n```sh\n# 用 brew install 装依赖\n```\n', True),
        ("cmd",     '# T\n\n一句话。\n\n```sh\nnpm i -g x\n```\n', False),
        ("inline",  '# T\n\n一句话。\n\n装：`npm i -g x`\n', False),
        ("sudo",    '# T\n\n一句话。\n\n```sh\nsudo apt install x\n```\n', False),
        ("image",   '# T\n\n一句话。\n\n![关系图](shot.png)\n', False),
        ("badge",   '# T\n\n一句话。\n\n![b](https://img.shields.io/badge/x-blue)\n', True),
        ("online",  '# T\n\n一句话。\n\n[在线试一下](https://demo.example.com/app)\n', False),
        ("weblink", '# T\n\n一句话。\n\n[文档](https://example.com/docs)\n', True),
        ("logo",    '# T\n\n一句话。\n\n![Logo](assets/logo.png)\n', True),
        ("video",   '# T\n\n一句话。\n\n[Demo 视频](https://youtu.be/abc)\n', True),
        ("jump",    '# T\n\n一句话。\n\n[安装](#%E5%AE%89%E8%A3%85)\n\n## 安装\n\n内容。\n', False),
    ]
    with tempfile.TemporaryDirectory(prefix="github-readme-skill-text-") as td:
        probe = Path(td) / "README.md"
        wrong = []
        for label, body, want_warn in screen_cases:
            probe.write_text(body, encoding="utf-8")
            rep = Report()
            check_single(probe, rep, [], {})
            got_warn = any("行内没有" in f.detail for f in rep.warns)
            if got_warn != want_warn:
                wrong.append(label)
        print(f"{'✓' if not wrong else '✗'} screen    首屏动作与证据判据"
              f"（{len(screen_cases) - len(wrong)}/{len(screen_cases)}）")
        if wrong:
            print(f"   不符: {', '.join(wrong)}")
            ok = False

        # 7. 双反引号包住含反引号的写法样例，不能被当成真的死锚点
        probe.write_text(
            "# T\n\n一句话。\n\n写法：`` `[跳](#ghost)` ``、`` `![x](nope.png)` ``。\n\n"
            "## 安装\n\n```sh\nnpm i -g x\n```\n", encoding="utf-8")
        rep = Report()
        check_single(probe, rep, [], {})
        ghost = [f for f in rep.fails if "ghost" in f.detail]
        print(f"{'✓' if not ghost else '✗'} inline    双反引号里的样例不判断锚点")
        if ghost:
            ok = False

        # 8. HTML 写法的徽章也要计数
        probe.write_text(
            "# T\n\n一句话。\n\n" +
            "\n".join(f'<img src="https://img.shields.io/badge/b{i}-blue" alt="b{i}">'
                      for i in range(9)) +
            "\n\n## 安装\n\n```sh\nnpm i -g x\n```\n", encoding="utf-8")
        rep = Report()
        check_single(probe, rep, [], {})
        hit = any("徽章" in f.detail for f in rep.warns)
        print(f"{'✓' if hit else '✗'} badge     HTML 徽章超过 7 个要提示")
        if not hit:
            ok = False

        # 9. 安装位置：排在第 4 节之后时首屏要有跳转；首屏有锚点或命令就不报
        late = ("# T\n\n一句话。\n\n![图](shot.png)\n\n"
                "## 一\n\n## 二\n\n## 三\n\n## 四\n\n## 安装\n\n到文档站下载。\n")
        install_cases = [
            ("late",      late, True),
            ("late-jump", late.replace("一句话。", "一句话。[安装](#安装)"), False),
            ("late-cmd",  late.replace("![图](shot.png)", "```sh\nnpm i -g x\n```"), False),
            ("early",     "# T\n\n一句话。\n\n## 安装\n\n到文档站下载。\n\n## 用法\n\n内容。\n", False),
        ]
        wrong = []
        for label, body, want_warn in install_cases:
            probe.write_text(body, encoding="utf-8")
            rep = Report()
            check_single(probe, rep, [], {})
            got_warn = any("安装排在第" in f.detail for f in rep.warns)
            if got_warn != want_warn:
                wrong.append(label)
        print(f"{'✓' if not wrong else '✗'} install   安装埋深时首屏必须有跳转"
              f"（{len(install_cases) - len(wrong)}/{len(install_cases)}）")
        if wrong:
            print(f"   不符: {', '.join(wrong)}")
            ok = False

        # 10. 标题用词：口头语和长句标题要报，专业词汇不报；文件清单标题要报
        wording_cases = {
            "它能做什么": True, "里头有什么": True, "看它先给结论": True,
            "谁适合用": True, "这个工具到底应该怎么用才对": True,
            "仓库结构": True, "目录结构": True, "项目结构": True,
            "Repository layout": True, "Project structure": True,
            "安装": False, "用法": False, "功能": False, "适用场景": False,
            "常见问题": False, "开发": False, "目录": False,
            "Install": False, "Use cases": False,
        }
        wording_bad = [(t, v) for t, v in wording_cases.items()
                       if bool(heading_wording_issues(t)) != v]
        print(f"{'✓' if not wording_bad else '✗'} heading   口头语和文件清单标题要报，专业词汇不报"
              f"（{len(wording_cases) - len(wording_bad)}/{len(wording_cases)}）")
        if wording_bad:
            print(f"   错判: {', '.join(t for t, _ in wording_bad)}")
            ok = False

    # 11. 版本声明：仓库里有依据且一致时不报，写高了报出仓库里的值，查不到依据给提示
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        readme = root / "README.md"
        (root / "package.json").write_text('{"engines": {"node": ">=22.20.0"}}', encoding="utf-8")

        def _ver_warns(text: str) -> list:
            readme.write_text(text, encoding="utf-8")
            rep = Report()
            check_single(readme, rep, [], {})
            return [f for f in rep.warns if f.where.startswith("第 ")]

        base = ("# T\n\n一句话说明用途。\n\n要求 {req}。\n\n"
                "## 安装\n\n```sh\nnpx demo-tool\n```\n")
        same = _ver_warns(base.format(req="Node.js 22.20 及以上"))
        higher = _ver_warns(base.format(req="Node.js 24.0 及以上"))
        print(f"{'✓' if not same and higher else '✗'} version   一致的版本声明不报，写高了报出仓库里的值")
        if same or not higher:
            ok = False
            for f in (same or higher):
                print("   ", f.render())

        (root / "package.json").unlink()
        no_src = _ver_warns(base.format(req="Python 3.11 以上"))
        print(f"{'✓' if no_src else '✗'} version   仓库里查不到依据时给提示")
        if not no_src:
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
            print(f"这份词表在技能目录里，不在目标仓库：{TERMS_HINT}", file=sys.stderr)
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

    if "--pair" in flags:
        if len(paths) == 2:
            check_pair(paths[0], paths[1], info[paths[0].name], info[paths[1].name], rep)
        else:
            rep.add("WARN", "—", "双语对照",
                    f"--pair 需要恰好 2 个文件，本次给了 {len(paths)} 个，对照已跳过；"
                    f"多语言版本请两两成对跑",
                    "[用法] 一次只对比一对")

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
              f"代码块 {d['fences']}, 徽章 {d['badges']}, 图 {d['images']}, 首屏 {d['first_screen_lines']} 行")
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
