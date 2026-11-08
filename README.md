# README Skill

[![check](https://github.com/hnyxgxm/github-readme-skill/actions/workflows/check.yml/badge.svg)](https://github.com/hnyxgxm/github-readme-skill/actions/workflows/check.yml) [![license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) [![node](https://img.shields.io/badge/node-22.20%2B-339933)](https://nodejs.org/)

[English](README.en.md) · 简体中文

让 AI 编程助手先判断一份 README 该承担多少内容，再把项目的真实能力组织成陌生读者能判断、能上手的首页。它管的是取舍和证据，不是辞藻。

[安装](#安装) · [第一次使用](#第一次使用) · [前后对照](#前后对照) · [仓库结构](#仓库结构)

## 安装

这是给编程助手读取的指令与参考资料包，不是独立软件。README 有中英两版，**技能指令与参考资料目前只有中文**。想先看清楚它会做什么，直接读 [SKILL.md](SKILL.md) 和 `references/`。

三个客户端共用一条 `skills` CLI 命令，装的是同一个完整技能包；需要 **Node.js 22.20+**（`skills` 包当前的 `engines` 要求）和已安装的客户端。在终端任意目录运行：

```sh
npx skills add hnyxgxm/github-readme-skill -g
```

按提示选择客户端，或用 `-a` 指定。`-g` 是用户级安装，所有项目可用；在目标项目目录去掉 `-g` 则只装到该项目。

- **Claude Code**（`-a claude-code`）：`~/.claude/skills/`；新会话输入 `/` 选择 `github-readme-skill`
- **Codex**（`-a codex`）：`~/.agents/skills/`；新会话输入 `$github-readme-skill`
- **Qoder Desktop**（`-a qoder`）：`~/.qoder/skills/`；新任务输入 `/` 选择 `github-readme-skill`

装好后开启新会话，确认技能出现在可选列表里。没有出现时，检查目录里是否包含 `SKILL.md` 和 `references/`、安装路径是否与上面一致，再重启客户端。安装会写入技能目录，已有同名技能时先核对来源。

没有 Node.js 时的后备：把整个仓库目录（含 `references/`）复制到上面任一技能目录，同样需要重启客户端。Cursor、OpenCode、Gemini CLI 等其他客户端走同一条命令，完整清单见[支持列表](https://github.com/vercel-labs/skills/blob/main/docs/agents.md)；安装器支持某个客户端，不等于本技能已在该客户端验证过。

维护：`npx skills update github-readme-skill -g` 更新，`npx skills remove github-readme-skill -g` 卸载；装到多个客户端时会提示选择目标，也可加 `-a`。

## 第一次使用

在已有项目里选中技能，提供仓库路径或现有 README，然后输入：

```text
请使用 github-readme-skill 审阅并重写这个仓库的 README。
先判断它该做路由页还是手册，再列出一版结构给我确认。
事实以仓库当前代码和发布物为准，查不到的不要写。
需要中英两版，本地修改即可，不要提交或推送。
```

第一次应得到形态判断和结构方案，而不是直接一份成稿。交付时应能说出：主证据是什么、哪些内容被移出首页、每条命令在哪个目录执行，以及还有哪些事实没核实。

只想评审就加「先不要修改文件」；只修安装段就指明范围，别让它重做全篇。

## 前后对照

同一个项目的首页，用这份 Skill 重写前后：[改前](https://github.com/DreamOfXM/ui-taste-skill/blob/3196ad5/README.md) → [改后](https://github.com/DreamOfXM/ui-taste-skill/blob/568b9cd/README.md)（[UI Taste Skill](https://github.com/DreamOfXM/ui-taste-skill)）。两个链接都指向固定提交，下面的摘要只是提要，点开看全文才算真看过。

| 对比项 | 改前 | 改后 |
| --- | --- | --- |
| 首屏 | 无图；一段形容词式定位，接 9 条示范与验证记录 | 一句定位 + 三个锚点 + 一张主证据图 |
| 安装 | 只有 `python3 scripts/install.py`，埋在「切换现有安装」一节末尾 | `npx skills add` 一条命令，「安装」在第 22 行独立成节 |
| 前 20 行链接数 | 15 | 6（1 个语言切换、3 个页内锚点、2 张图的链接） |
| H2 章节 | 4 个：Git 维护、切换、恢复、验证 | 6 个：改版流程、安装、试任务、看示范、边界、许可 |
| 全文 | 85 行 / 0 图 | 116 行 / 1 张主证据图 |

改前的首屏是这种口气：

> 面向网页、桌面软件、移动 App 和 Web 工作台的设计工作流。……通过内容驱动的方向探索、构图与排印、材料样片、连续交互和正向审美验收，帮助模型做出完整而有吸引力的界面……

四个 H2 只服务于已经装过的人。改版没有靠换措辞取胜，而是把内容分了一次层：判断依据留在首屏，过程细节退回 `references/`。

## 解决的问题

- **抄文档站或无处可去**：先问一句「除了这份 README，读者还有别处可去吗」，据此在路由页 / 中间态 / 手册三种形态里选一种，再决定写多少；仓库里有 `docs/` 却没在 README 里链过去，算中间态，不是手册。
- **首屏堆满**：首屏只放四件套——身份、一句定位、信任标记、一个动作或一份证据，约 25 行以内。
- **用形容词代替证据**：按交付物挑主证据，CLI 用基准表或终端输出，Agent Skill 用真实任务的前后对照，库用最小调用；不为「有图」硬放图。
- **安装写成五段**：多个客户端共用一条 `npx skills` 命令，差异只落在目标名、目录和启用方式；不给同一个客户端并列两套渠道。
- **双语只翻一半**：两版章节语义对应，命令、包名、版本条件和 URL 原样保留，不把中文的有条件描述强化成保证。

## 仓库结构

- [SKILL.md](SKILL.md)：主链，八节，从判形态到验收。
- [结构、版式与编辑示范](references/patterns.md)：七类项目的骨架、首屏编排、证据矩阵、安装的「一条路径、参数分叉」写法、双语取舍。
- [范例清单](references/examples.md)：14 个真实仓库首页的逐项取舍，以及不该从这些样本推出什么。
- [验收方法](references/acceptance.md)：形态门、事实与边界、按分支走通、首屏证据、双语对照、渲染与收口口径。
- [渲染与尺寸](references/rendering.md)：正文列宽、字号换算与图片宽度行为的实测数据。
- [图怎么画](references/visual-craft.md)：画布与字号换算表、只用系统字体的依据、深浅色的三种做法、动图编码参数实测。
- [维护与回归](references/maintenance.md)：改这份 Skill 时怎么做新旧版对照，不靠改动说明自证有效。
- [`references/terms.txt`](references/terms.txt)：这份 Skill 自己对内叫法的词表，喂给 `check-text.py --terms`。它约束的是本仓库的写法，不是用户 README 的规定；扫别人的文档时命中也只报提示。
- `scripts/check-assets.py`：判图片和文件链接会不会崩——字号、远程字体、缺 viewBox、体积、宽高、路径大小写，也认 `style="width:"`、`=宽x高`、`<picture>` 里的换格式源。
- `scripts/check-text.py`：判首屏行数与首屏有没有动作或证据、徽章数量、锚点、双语结构与术语漂移。
- `scripts/readme_md.py`：两个脚本共用的 Markdown 解析（围栏、行内代码），不是入口，不要直接跑。
- `.github/workflows/check.yml`：每次推送跑两个脚本的自测，再拿两份 README、`SKILL.md` 和 `references/` 自查一遍。

两个脚本都带 `--selftest`；列宽可用 `--column-width` 覆盖，`check-assets.py` 加 `--check-remote` 会去验外链可达。它们只用 python3 标准库（3.8 以上），不需要 pip 装东西。在本仓库内：

```sh
python3 scripts/check-assets.py README.md
python3 scripts/check-text.py README.md README.en.md --pair --terms references/terms.txt
```

装成 Skill 之后，工作目录是别人的仓库，脚本和词表都留在技能目录里，要给绝对路径，否则必然 `No such file or directory`：

```sh
SKILL=~/.claude/skills/github-readme-skill
python3 "$SKILL/scripts/check-assets.py" README.md
python3 "$SKILL/scripts/check-text.py" README.md README.en.md --pair --terms "$SKILL/references/terms.txt"
```

退出码 0 表示没有会崩的项，1 表示有。每条结论都标了是实测、官方限制还是工程经验。脚本只判机械的那一半，徽章绿也只说明这一半过了，写得好不好仍要自己看。

## 使用边界

- 它提供判断方法和验收清单，不保证任何模型一次就产出好首页；产出质量仍取决于模型、你给的仓库事实和你是否逐条验收。
- 它不会替你决定许可证、发布渠道或推送时机；写文档不等于授权提交、推送、部署或安装扩展。
- README 的渲染受平台限制：GitHub 会剥掉脚本与内联样式，做不出水平标签，也不给 Markdown 排版容器；关键内容要在常规宽度和约 390px 窄屏都能读。
- 本技能的 frontmatter 声明了 `allowed-tools`。按 [skills 的兼容表](https://github.com/vercel-labs/skills/blob/main/docs/agents.md)，Qoder、Kiro CLI、Zencoder 不支持这个字段，在这三个客户端上它会被忽略，工具权限仍按客户端自己的规则走；Claude Code、Codex 会照它限制。
- 事实以仓库当前状态为准。本仓库的示例引用了 [UI Taste Skill](https://github.com/DreamOfXM/ui-taste-skill) 的提交历史，那两个链接指向的是固定 commit，不会随对方仓库演进而改变。

## 许可

采用 [MIT 许可证](LICENSE)：允许商业与非商业使用、修改和再分发，需在副本中保留版权声明与许可声明。作者：hnyxgxm。
