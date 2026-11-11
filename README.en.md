# GitHub README Skill

[简体中文](README.md) · English

A rule set for AI coding assistants that write READMEs: it first decides how much this homepage should carry, based on what the repository already provides, then arranges the project's real capabilities so a stranger can decide whether to try it and get through a first use. The skill instructions and reference material are written in Chinese.

![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg) ![Node.js 22.20+](https://img.shields.io/badge/Node.js-22.20%2B-blue.svg)

[Install](#install) · [Features](#features) · [Examples](#examples) · [License](#license)

The positioning line of one real README, across two public commits:

> **Before** · [ui-taste-skill README, line 3](https://github.com/DreamOfXM/ui-taste-skill/blob/3196ad5/README.md#L3)
> 「面向网页、桌面软件、移动 App 和 Web 工作台的设计工作流。以出众美感、优美秩序、精致质感与产品自身气质为目标：可用和整齐只是底线。通过内容驱动的方向探索、构图与排印、材料样片、连续交互和正向审美验收，帮助模型做出完整而有吸引力的界面；为易漂移或不能读图的实现者提供明确的视觉执行包。不是固定皮肤，也不承诺所有模型必然产出优秀作品；跨模型效果仍需受控实验。」

becomes:

> **After** · [same repo README, line 5](https://github.com/DreamOfXM/ui-taste-skill/blob/568b9cd/README.md#L5)
> 「让 AI 编程助手把界面改版做成可检查的过程：先比较两个视觉方向，再用设计卡约束实现，最后在最密的一屏和窄屏上验收。」

Both sentences come from public commits and are quoted only as a factual comparison, not an endorsement by that repo. After installing, give the agent a rewrite task and have it compress your own README's positioning line to one sentence too.

## Install

If you have decided to load this Skill into your coding assistant but are not sure which command to run, check the prerequisites, then pick the line for your client.

Requires Node.js 22.20 or later (source: `skills@1.7.6` package.json, `engines.node` is `>=22.20.0`); the `skills` CLI from vercel-labs/skills fetches `hnyxgxm/github-readme-skill`.

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

Run it in a terminal from any directory; `-g` installs at user level for all projects, and dropping `-g` installs only into the current repository, in which case run it from that repository's directory. It is installed once the command finishes without errors.

## Quick start

If you are not sure what to say first after installing, hand the agent the repository path and what you want done.

> Rewrite this repository's README, producing both a Chinese and an English version.

The only things you need to prepare are the repository and your request. What you get back is two mutually linked README homepages you can put into the repo; the pair above shows what a compressed positioning line looks like.

## Features

If you are not sure what you can have the agent do to this README: every line below is a task you can launch directly, so pick the one that fits and hand it to the agent.

- **Write one from scratch**: give it the repository path; it settles the shape and lists a structure proposal, then writes the full text once you confirm.
- **Fix an existing one**: point out which section is out of order and which paragraph should become evidence; it shows a comparison and only starts writing once you approve.
- **Review without touching files**: have it list the problems as a checklist, and you decide whether to change anything.
- **Produce both Chinese and English versions**: one task delivers two entry pages with matching sections, commands, limits and license.
- **Run a standalone pass before publishing**: after both versions are written, have it verify without editing and list what is missing or out of sync.

Before: open the repository, write a long paragraph from memory about what the project does, decide the sections as you go, and still be unsure whether a stranger can follow it.
Now: hand the agent the repository path and what you want; it settles the shape, picks evidence to match the deliverable, then puts install and the first task in an order a reader can finish.

## Examples

To see where the difference lands, count the pair above: four sentences before, one after.

In the before version the purpose does not appear until the third sentence, after a platform list, aesthetic goals and a string of method names; the after version states who acts, the task and the three-step acceptance in its first sentence, replacing a noun-phrase description of the design workflow with an action sentence addressed to the coding assistant.

What the after version drops are those four kinds of padding from the positioning line — platform list, aesthetic goals, method list and disclaimers; they are deleted from this sentence, not moved into it. This comparison uses only these two sentences, does not look at other changes in the same commits, and makes no claim about where that content went elsewhere in that repo.

Both quotes come from the positioning lines of those two `README.md` files: line 3 and line 5 respectively; each link opens to a file where the sentence can be matched word for word.

If you have read the comparison above and want to check the rules or acceptance criteria behind it, start at [SKILL.md](SKILL.md) and [references/](references/).

## Use cases

A README whose structure is already clear and that only needs a typo fixed does not need this Skill; it is for rewrites, reviews and bilingual homepages, not line-by-line polishing.

It works only in claude-code, codex and qoder where Agent Skills are supported, and needs the Node.js version listed under Install; the rules cover READMEs for repositories or packages, not full API manuals or general articles. You confirm the scope of changes; it will not commit, push or modify product files on its own.

Whether the result reads well still has to be seen on the target platform; the repository's own validation scripts only catch structural faults.

## License

For anyone who wants to redistribute this Skill or confirm whether it can be used in a project: this repository is released under MIT; the full terms are in [LICENSE](LICENSE).
