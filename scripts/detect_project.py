#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读出项目里真实存在的文件事实，输出 JSON，供 SKILL.md 第 1 步使用。

只读，不写任何文件到被检查的项目里。只用 Python 标准库，3.8 以上可用。

    python3 detect_project.py /path/to/repo
    python3 detect_project.py --selftest

注意：这个脚本不判断项目属于哪一类。它只报看见了什么文件，
分类由模型对照 references/project-analysis.md 完成。
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "vendor", "dist", "build",
    "target", "__pycache__", ".venv", "venv", ".idea", ".vscode",
    ".next", ".nuxt", "coverage", ".pytest_cache", ".mypy_cache",
    "fixtures", "testdata",
}
MAX_FILES = 4000
MAX_TEXT = 200000

MANIFESTS = {
    "package.json": "npm / yarn / pnpm",
    "pyproject.toml": "Python (pyproject)",
    "setup.py": "Python (setup.py)",
    "requirements.txt": "Python (pip)",
    "Cargo.toml": "Rust (cargo)",
    "go.mod": "Go modules",
    "Gemfile": "Ruby (bundler)",
    "composer.json": "PHP (composer)",
    "pom.xml": "Java (maven)",
    "build.gradle": "Java/Kotlin (gradle)",
    "Package.swift": "Swift (SwiftPM)",
    "DESCRIPTION": "R package",
}

LANG_BY_EXT = {
    ".py": "Python", ".js": "JavaScript", ".mjs": "JavaScript",
    ".jsx": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript",
    ".go": "Go", ".rs": "Rust", ".java": "Java", ".kt": "Kotlin",
    ".swift": "Swift", ".rb": "Ruby", ".php": "PHP", ".c": "C",
    ".h": "C", ".cc": "C++", ".cpp": "C++", ".cs": "C#",
    ".sh": "Shell", ".sql": "SQL", ".html": "HTML", ".css": "CSS",
    ".vue": "Vue", ".svelte": "Svelte", ".md": "Markdown",
    ".dart": "Dart", ".lua": "Lua", ".ex": "Elixir",
}

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp"}
VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv", ".avi"}

WEB_SIGNS = {
    "index.html", "vite.config.js", "vite.config.ts", "next.config.js",
    "next.config.mjs", "nuxt.config.ts", "astro.config.mjs",
    "vercel.json", "netlify.toml", "webpack.config.js",
}
DOCS_SITE_SIGNS = {
    "mkdocs.yml", "mkdocs.yaml", "CNAME", "_config.yml",
    "docsify", "vuepress.config.js", "book.toml",
}
CI_DIRS = {".github/workflows", ".gitlab-ci.yml", ".circleci"}
ENTRY_FILES = {"main.py", "main.go", "main.rs", "cli.py", "__main__.py", "cmd"}


def scan_files(root):
    """列出文件（跳过依赖目录和缓存目录），最多 MAX_FILES 个。"""
    found = []
    for dirpath, dirnames, filenames in os.walk(str(root)):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        here = Path(dirpath)
        for name in filenames:
            found.append(here / name)
            if len(found) >= MAX_FILES:
                return found
    return found


def read_text(path):
    try:
        if path.stat().st_size > MAX_TEXT:
            return path.read_text(encoding="utf-8", errors="ignore")[:MAX_TEXT]
        return path.read_text(encoding="utf-8", errors="ignore")
    except (OSError, UnicodeError):
        return ""


def find(root, filename):
    p = root / filename
    return p if p.is_file() else None


def guess_name(root, files):
    """返回 (名字, 出处)。出处很重要：目录名不一定是项目真名。"""
    pkg = find(root, "package.json")
    if pkg:
        m = re.search(r'"name"\s*:\s*"([^"]+)"', read_text(pkg))
        if m:
            return m.group(1).lstrip("@").split("/")[-1], "package.json 的 name"
    pyproject = find(root, "pyproject.toml")
    if pyproject:
        m = re.search(r'(?m)^\s*name\s*=\s*["\']([^"\']+)["\']', read_text(pyproject))
        if m:
            return m.group(1), "pyproject.toml 的 name"
    for fn in ("Cargo.toml", "go.mod", "DESCRIPTION"):
        p = find(root, fn)
        if not p:
            continue
        text = read_text(p)
        if fn == "Cargo.toml":
            m = re.search(r'(?m)^\s*name\s*=\s*["\']([^"\']+)["\']', text)
        elif fn == "go.mod":
            m = re.search(r"(?m)^module\s+(\S+)", text)
        else:
            m = re.search(r"(?m)^Package:\s*(\S+)", text)
        if m:
            return m.group(1).rstrip("/").split("/")[-1], fn
    return root.name or "未找到项目名", "目录名（可能不是项目真名，请以 README 标题为准）"


def top_languages(files, limit=5):
    counts = {}
    for f in files:
        lang = LANG_BY_EXT.get(f.suffix.lower())
        if lang and lang != "Markdown":
            counts[lang] = counts.get(lang, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [{"name": n, "files": c} for n, c in ranked[:limit]]


def entry_points(root, files):
    """找可执行入口的线索。只报看见的东西，不推断这是不是命令行工具。"""
    out = []
    names = {f.name for f in files}
    pkg = find(root, "package.json")
    if pkg:
        text = read_text(pkg)
        m = re.search(r'"bin"\s*:\s*(\{[^}]*\}|"[^"]+")', text, re.S)
        if m:
            out.append({"file": "package.json", "field": "bin", "value": m.group(1)[:200]})
    pyproject = find(root, "pyproject.toml")
    if pyproject and re.search(r"(?m)^\s*\[project\.scripts\]", read_text(pyproject)):
        out.append({"file": "pyproject.toml", "field": "project.scripts"})
    cargo = find(root, "Cargo.toml")
    if cargo and re.search(r"(?m)^\s*\[\[bin\]\]", read_text(cargo)):
        out.append({"file": "Cargo.toml", "field": "[[bin]]"})
    gomod = find(root, "go.mod")
    if gomod and any(f.parts and "cmd" in f.parts for f in files):
        out.append({"file": "go.mod", "field": "cmd/ 目录"})
    for name in sorted(ENTRY_FILES & names):
        out.append({"file": name, "field": "常见入口文件"})
    for f in files:
        if f.suffix == "" and f.name in {"bin", "cli", "main"}:
            out.append({"file": f.name, "field": "无扩展可执行文件"})
            break
    return out


def web_signs(root, files):
    names = {f.name for f in files}
    out = sorted(names & WEB_SIGNS)
    pkg = find(root, "package.json")
    if pkg:
        text = read_text(pkg)
        for word in ("react", "vue", "next", "nuxt", "svelte", "vite"):
            if re.search(r'"' + word + r'"\s*:', text):
                out.append("package.json 依赖 " + word)
    if find(root, "Dockerfile"):
        out.append("Dockerfile")
    return out[:12]


def docs_info(root, files):
    names = {f.name for f in files}
    dirs = sorted({p.name for p in root.iterdir() if p.is_dir() and
                   p.name in {"docs", "doc", "references", "examples", "chapters", "tutorials"}})
    site = sorted(names & DOCS_SITE_SIGNS)
    for f in files:
        if f.name.startswith("docusaurus.config"):
            site.append(f.name)
    return {"document_dirs": dirs or "没找到", "docs_site_signs": site or "没找到"}


def ci_info(root, files):
    wf = root / ".github" / "workflows"
    out = []
    if wf.is_dir():
        out = sorted(p.name for p in wf.iterdir() if p.suffix in {".yml", ".yaml"})
    for name in (".gitlab-ci.yml", "Jenkinsfile", "azure-pipelines.yml"):
        if find(root, name):
            out.append(name)
    return out or "没找到"


def media_info(files):
    images, videos = [], []
    for f in files:
        ext = f.suffix.lower()
        if ext in IMAGE_EXT:
            images.append(f.name)
        elif ext in VIDEO_EXT:
            videos.append(f.name)
    return {"images": sorted(images)[:20], "image_count": len(images),
            "videos": sorted(videos)[:20], "video_count": len(videos)}


def readme_info(root, files):
    out = []
    for f in files:
        if f.parent == root and re.fullmatch(r"README(?:\.[A-Za-z0-9_-]+)?\.md", f.name, re.I):
            text = read_text(f)
            lines = text.splitlines()
            head = "\n".join(lines[:25])
            out.append({
                "file": f.name,
                "lines": len(lines),
                "has_command_in_first_25_lines": bool(re.search(r"(?m)^\s*(?:npx |npm |pip |pip3 |python3? |brew |cargo |go |apt |git clone |\$ )", head)),
                "has_bash_fence_in_first_25_lines": "```" in head,
            })
    return out or "没找到"


def install_hints(root, files):
    out = []
    pkg = find(root, "package.json")
    if pkg:
        m = re.search(r'"scripts"\s*:\s*\{([^}]*)\}', read_text(pkg), re.S)
        if m:
            for key in ("install", "build", "start", "dev"):
                if re.search(r'"' + key + r'"\s*:', m.group(1)):
                    out.append("package.json scripts." + key)
    for fn in ("Makefile", "justfile", "Taskfile.yml", "Dockerfile", "docker-compose.yml"):
        if find(root, fn):
            out.append(fn)
    for f in files:
        if f.parent == root and re.fullmatch(r"README(?:\.[A-Za-z0-9_-]+)?\.md", f.name, re.I):
            for line in read_text(f).splitlines()[:60]:
                if re.match(r"^\s*(?:npx |npm i? |pip3? install |brew install |cargo install |go install |git clone )", line):
                    out.append(f.name + ": " + line.strip()[:100])
    return out[:10] or "没找到"


def detect(root):
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("目录不存在: " + str(root))
    files = scan_files(root)
    names = {f.name for f in files}
    media = media_info(files)
    docs = docs_info(root, files)
    licenses = sorted(n for n in names if n.upper().startswith(("LICENSE", "LICENCE", "COPYING")))
    project_name, name_source = guess_name(root, files)
    return {
        "project_dir": str(root),
        "project_name": project_name,
        "project_name_source": name_source,
        "package_managers": [label for fn, label in MANIFESTS.items() if fn in names] or "没找到",
        "languages": top_languages(files) or "没找到",
        "entry_point_signs": entry_points(root, files) or "没找到",
        "web_ui_signs": web_signs(root, files) or "没找到",
        "docs": docs,
        "license_files": licenses or "没找到",
        "ci_workflows": ci_info(root, files),
        "media": media,
        "readme": readme_info(root, files),
        "install_hints": install_hints(root, files) or "没找到",
        "scanned_file_count": len(files),
        "note": "以上只是文件里看得见的事实，不是项目分类结论。"
                "分类请对照 references/project-analysis.md；"
                "这里写「没找到」的字段要去看代码或问用户，不要补一个看起来合理的答案。",
    }


def selftest():
    import os
    import tempfile

    ok, fail = 0, 0

    def check(label, condition, detail=""):
        nonlocal ok, fail
        if condition:
            ok += 1
        else:
            fail += 1
            print("FAIL  " + label + ("  " + detail if detail else ""))

    def write(base, rel, content):
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="detect-project-") as td:
        home = Path(td)

        # 1. Python 命令行工具
        cli = home / "cli-tool"
        write(cli, "pyproject.toml", '[project]\nname = "cool-cli"\n\n[project.scripts]\ncool = "cool.main:run"\n')
        write(cli, "cool/main.py", "def run():\n    print('ok')\n")
        write(cli, "README.md", "# cool-cli\n\n```bash\npip install cool-cli\n```\n")
        write(cli, "LICENSE", "MIT\n")
        d = detect(cli)
        check("cli: 项目名", d["project_name"] == "cool-cli", str(d["project_name"]))
        check("cli: 名字出处", "pyproject.toml" in d["project_name_source"], str(d["project_name_source"]))
        check("cli: 认出 project.scripts", any(x.get("field") == "project.scripts" for x in d["entry_point_signs"]))
        check("cli: 认出 pyproject 包管理", "Python (pyproject)" in d["package_managers"])
        check("cli: 认出许可证", d["license_files"] == ["LICENSE"])
        check("cli: 现有 README 行数", isinstance(d["readme"], list) and d["readme"][0]["lines"] == 5)
        check("cli: 不给分类结论", "category" not in d and "type" not in d)

        # 2. 前端网站
        web = home / "web-app"
        write(web, "package.json", '{"name":"my-web","dependencies":{"react":"^18"}}\n')
        write(web, "index.html", "<html></html>\n")
        write(web, "vercel.json", "{}\n")
        write(web, "src/App.tsx", "export default () => null\n")
        d = detect(web)
        check("web: 项目名", d["project_name"] == "my-web", str(d["project_name"]))
        check("web: 认出前端线索", "index.html" in d["web_ui_signs"] and "vercel.json" in d["web_ui_signs"])
        check("web: 认出 react", any("react" in x for x in d["web_ui_signs"]))
        check("web: 语言含 TypeScript", any(x["name"] == "TypeScript" for x in d["languages"]))

        # 3. 教程仓库
        tut = home / "tutorial"
        write(tut, "docs/01.md", "# 第一节\n")
        write(tut, "docs/02.md", "# 第二节\n")
        write(tut, "mkdocs.yml", "site_name: demo\n")
        write(tut, "README.md", "# 教程\n")
        d = detect(tut)
        check("tutorial: 认出 docs 目录", "docs" in d["docs"]["document_dirs"])
        check("tutorial: 认出文档站配置", "mkdocs.yml" in d["docs"]["docs_site_signs"])
        check("tutorial: 没有可执行入口", d["entry_point_signs"] == "没找到")

        # 4. 带图和视频的项目
        media = home / "media"
        write(media, "assets/shot.png", "x")
        write(media, "assets/demo.gif", "x")
        write(media, "assets/demo.mp4", "x")
        write(media, "scripts/fixtures/good/fake.png", "x")
        d = detect(media)
        check("media: 图片数", d["media"]["image_count"] == 2, str(d["media"]))
        check("media: 视频数", d["media"]["video_count"] == 1, str(d["media"]))
        check("media: 不算测试样本图", d["media"]["images"] == ["demo.gif", "shot.png"], str(d["media"]["images"]))

        # 5. CI 与依赖目录跳过
        noisy = home / "noisy"
        write(noisy, ".github/workflows/check.yml", "name: check\n")
        write(noisy, "node_modules/junk.py", "x")
        d = detect(noisy)
        check("ci: 认出工作流", "check.yml" in d["ci_workflows"])
        check("skip: 不扫 node_modules", d["languages"] == "没找到", str(d["languages"]))

        # 6. 不存在的目录
        try:
            detect(home / "does-not-exist")
            check("missing: 应报错", False)
        except ValueError:
            check("missing: 应报错", True)

    print("selftest: %d 通过, %d 失败" % (ok, fail))
    return 0 if fail == 0 else 2


def main():
    ap = argparse.ArgumentParser(description="读出项目里真实存在的文件事实")
    ap.add_argument("path", nargs="?", default=".", help="项目目录，默认当前目录")
    ap.add_argument("--selftest", action="store_true", help="跑自带测试，不检查任何真实项目")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    try:
        info = detect(args.path)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
