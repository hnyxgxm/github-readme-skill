# GitHub README Skill

[English](README.en.md) · 简体中文

给 AI 编程助手一套写 README 的规则：先按仓库现状定这份首页该承担多少内容，再把真实能力排成陌生读者能判断要不要试、能走完第一次使用的顺序。技能本体与参考资料均为中文。

![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg) ![Node.js 22.20+](https://img.shields.io/badge/Node.js-22.20%2B-blue.svg)

[安装](#安装) · [功能](#功能) · [示例](#示例) · [许可](#许可)

同一份安装段，本仓库两个公开提交里的原文，点开能自己比：

> **改前** · [8d064ad README 第 29 行](https://github.com/hnyxgxm/github-readme-skill/blob/8d064ad/README.md#L29)
> 「按提示选择客户端，或用 `-a` 指定：`claude-code`、`codex`、`qoder`。」

变成每个客户端各一段、各有一条参数填好的命令：

> **改后** · [3e8726c README 第 29–33 行](https://github.com/hnyxgxm/github-readme-skill/blob/3e8726c/README.md#L29)
> `npx skills add hnyxgxm/github-readme-skill -g -a claude-code`

改前要自己弄懂 `-a` 该填哪个值；改后只读自己那段、复制一条命令就走。装好之后给 Agent 一句重写任务，把你那份 README 的安装段也改成这样。

## 安装

已经决定把这份 Skill 装进编程助手、却不知道该跑哪条命令的人，先确认环境，再按客户端选一行。

需要 Node.js 22.20 及以上（出处：`skills@1.7.6` 的 `package.json`，`engines.node` 为 `>=22.20.0`），通过 vercel-labs/skills 的 `skills` CLI 获取 `hnyxgxm/github-readme-skill`。

**Claude Code**

```sh
npx skills add hnyxgxm/github-readme-skill -g -a claude-code
```

**Codex**

```sh
npx skills add hnyxgxm/github-readme-skill -g -a codex
```

**Qoder**

```sh
npx skills add hnyxgxm/github-readme-skill -g -a qoder
```

在终端任意目录执行；`-g` 是用户级安装、所有项目可用，去掉 `-g` 只装当前仓库，此时要在目标仓库目录下执行。命令结束且没有报错，就装好了。

## 快速开始

装好之后不知道第一句该说什么，就把仓库路径和要办的事一起交给 Agent。

> 帮我重写这个仓库的 README，中英双语各一份。

要准备的只有仓库和你的诉求。拿到的是两份写好、互相链得上的 README 首页，可以直接放进仓库；定位段收成什么样子，看上面那组改前改后。

## 功能

不确定能让 Agent 对这份 README 做什么的人：下面每一条都是能直接发起的任务，照你的情况挑一条发给它。

- **从零写一份**：给它仓库路径，它先定形态、列结构方案，你确认了再写全文。
- **把现有的一份改好**：指出哪节顺序不对、哪段该换成证据，出对照，你认可了再动笔。
- **只评审不动文件**：让它把问题列成清单，改不改由你决定。
- **出中英两版**：同一次任务交付两份入口，章节、命令、限制和许可都对齐。
- **发布前单独查一遍**：两版写完后让它只核不改，把缺项和不对齐的地方列出来。

以前：打开仓库，凭印象把项目能做什么写成一大段，边写边想分几节，写完仍不确定别人能不能看懂。
现在：把仓库路径和诉求交给 Agent，它先定形态、按交付物挑证据，再把安装和首个任务排到读者能走完的顺序里。

## 示例

要看差别落在哪一步，数一下上面那组改前改后：改前把三个客户端的参数值挤在一句提示里，改后每个客户端各占一段、各有一条填好参数的命令。

改前那句要读者先弄懂 `-a` 是什么，再从三个值里挑一个填回命令；抄错一个字母就装到别的客户端。改后这一步没了：段标题就是客户端名，命令里的值已经填好，读者只读自己那段。

改后丢的是「按提示选择客户端」这句提示，分段之后它不再需要。三个参数值没丢，分别进了三段命令；`-g` 的含义和执行位置并进了安装段前面那句前提。

本对照只比安装段这一处，不比两版整页，也不拿它说明别的项目该怎么装。

引文都能逐字核到：改前在 [8d064ad 的 README.md 第 29 行](https://github.com/hnyxgxm/github-readme-skill/blob/8d064ad/README.md#L29)，改后是 [3e8726c 的 README.md 第 29–33 行](https://github.com/hnyxgxm/github-readme-skill/blob/3e8726c/README.md#L29) 里 Claude Code 那段的命令；英文版对应的是 `README.en.md` 的同样位置，各自贴自己语言的原文。

看完上面的对照、还想核一核规则或验收口径的人，入口在 [SKILL.md](SKILL.md) 与 [references/](references/)。

## 适用场景

结构已经清楚、只想改个错别字的 README，不必加载这份 Skill；它面向重写、评审和双语首页，不是逐句润色。

它只在支持 Agent Skill 的 claude-code、codex、qoder 里可用，且需要安装一节列出的 Node.js 版本；规则覆盖仓库或软件包的 README，不覆盖完整 API 手册和一般文章。改动范围由你确认，不会自动提交、推送或改产品文件。

写得好不好仍要在目标平台实际看一遍；仓库自带的校验脚本只判格式硬伤。

## 许可

要再分发这份 Skill、或确认能否在项目里使用它的人：本仓库以 MIT 许可发布，完整条款见 [LICENSE](LICENSE)。
