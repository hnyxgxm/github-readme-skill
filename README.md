# README Skill

[![check](https://github.com/hnyxgxm/github-readme-skill/actions/workflows/check.yml/badge.svg)](https://github.com/hnyxgxm/github-readme-skill/actions/workflows/check.yml) [![license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) [![node](https://img.shields.io/badge/node-22.20%2B-339933)](https://nodejs.org/)

[English](README.en.md) · 简体中文

给 GitHub 仓库写或改 README 的一份 Agent Skill。它先读项目、判断读者，再动笔。写出来的 README 用短句、主谓宾，只讲功能和用法，不写实现原理。二级标题由读者这一节要做的事定，不是固定模板。

![这份 README 改版前后：改前首屏堆满正文、安装埋在中段；改后首屏只有定位、徽章和一条安装命令](assets/before-after.zh.svg)

这份 README 改版前后的首屏。左边看不出下一步点哪，右边的安装就在首屏下面。

## 它能做什么

- 读项目文件，列出能核对的事实。
- 判断项目属于哪一类、谁来读、读者第一步要做什么。
- 按这个第一步排出段落顺序，再决定放不放图、放不放视频。
- 写完跑检查脚本，查链接、锚点、图片和首屏。

动笔之前，技能会先贴一份六行结论，和你对齐之后才写第一行。

## 安装

这是给编程助手读取的指令与参考资料包，不是独立软件。README 有中英两版，技能指令与参考资料目前只有中文。想先看清楚它会做什么，直接读 [SKILL.md](SKILL.md) 和 `references/`。

三个客户端共用一条 `skills` CLI 命令，装的是同一个完整技能包；需要 Node.js 22.20+ 和已安装的客户端。在终端任意目录运行：

```sh
npx skills add hnyxgxm/github-readme-skill -g
```

按提示选择客户端，或用 `-a` 指定。`-g` 是用户级安装。没有 Node.js 时，把整个目录（含 `references/`）复制到技能目录，例如 `~/.claude/skills/`，再重启客户端。

需要 Python 3.8 以上，只用标准库。生成动图和压缩视频的可选检查需要 `ffmpeg`、`gifsicle`，没装也能用。

## 用法

在已有项目里选中技能，提供仓库路径或现有 README，然后输入：

> 请使用 github-readme-skill 审阅并重写这个仓库的 README。先贴六行结论给我确认，再动笔。事实以仓库当前代码和发布物为准，查不到的不要写。

只想看问题、不想改文件，就加一句「先不要修改文件」。只修安装段就指明范围，别让它重做全篇。

探测脚本可以单独跑：

```bash
python3 scripts/detect_project.py /path/to/repo
python3 scripts/detect_project.py --selftest
```

## 目录

| 路径 | 是什么 |
| --- | --- |
| `SKILL.md` | 主文件：四步分析、段落顺序、句子规矩、约束、判据 |
| `references/project-analysis.md` | 项目分类表和读者分析 |
| `references/section-templates.md` | 六段位置和骨架，标题是占位符 |
| `references/media-decisions.md` | 图片和视频的决策、平台限制 |
| `references/eval-plan.md` | 怎么验证改动有没有用 |
| `references/rendering.md`、`visual-craft.md`、`terms.txt` | 渲染实测、画图、术语表 |
| `scripts/detect_project.py` | 读项目事实，输出 JSON，带自测 |
| `scripts/check-text.py`、`check-assets.py` | 文字结构和图片资源的检查脚本 |

## 开发

脚本都带 `--selftest`。改过判据之后先跑自测，再拿一两个真实仓库试写。

```bash
python3 scripts/detect_project.py --selftest
python3 scripts/check-text.py --selftest
python3 scripts/check-assets.py --selftest
```

写完的 README 用两个脚本检查：

```bash
python3 scripts/check-text.py README.md --terms references/terms.txt
python3 scripts/check-assets.py README.md
```

## 许可

采用 [MIT 许可证](LICENSE)。作者：hnyxgxm。
