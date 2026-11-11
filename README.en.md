# GitHub README Skill

[简体中文](README.md) · English

A rule set for AI coding assistants that write READMEs: it first decides how much this homepage should carry, based on what the repository already provides, then arranges the project's real capabilities so a stranger can decide whether to try it and get through a first use. The skill instructions and reference material are written in Chinese.

![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg) ![Node.js 22.20+](https://img.shields.io/badge/Node.js-22.20%2B-blue.svg)

[Install](#install) · [Features](#features) · [Examples](#examples) · [License](#license)

The same Install section, in two public commits of this repo. Both originals are there to open and compare:

> **Before** · [8d064ad, README.en.md line 29](https://github.com/hnyxgxm/github-readme-skill/blob/8d064ad/README.en.md#L29)
> "Pick clients when prompted, or name one with `-a`: `claude-code`, `codex`, `qoder`."

It becomes one section per client, each with a complete command whose arguments are already filled in:

> **After** · [3e8726c, README.en.md lines 29–33](https://github.com/hnyxgxm/github-readme-skill/blob/3e8726c/README.en.md#L29)
> `npx skills add hnyxgxm/github-readme-skill -g -a claude-code`

Before, you had to work out which value `-a` takes. After, you read only your own section and copy one command. Once installed, give the agent a rewrite task and have it do the same for your README's Install section.

## Install

If you have decided to load this Skill into your coding assistant but are not sure which command to run, check the prerequisites, then pick the line for your client.

Requires Node.js 22.20 or later (source: `skills@1.7.6` package.json, `engines.node` is `>=22.20.0`); the `skills` CLI from vercel-labs/skills fetches `hnyxgxm/github-readme-skill`. `-g` installs at user level for all projects; drop `-g` inside a target repository to install only there.

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

**OpenCode**

```sh
npx skills add hnyxgxm/github-readme-skill -g -a opencode
```

**ZCode**

```sh
npx skills add hnyxgxm/github-readme-skill -g -a zcode
```

**Pi**

```sh
npx skills add hnyxgxm/github-readme-skill -g -a pi
```

Cursor, Trae, Continue, OpenClaw and others are supported too: swap the value after `-a` for a name from [the skills CLI's supported agents list](https://github.com/vercel-labs/skills/blob/main/docs/agents.md) (the same list ships as `docs/agents.md` inside `skills@1.7.6`). It is installed once the command finishes without errors.

**WorkBuddy**

WorkBuddy is not in that list; it reads a user-level skills directory, so put the repository there directly:

```sh
git clone https://github.com/hnyxgxm/github-readme-skill.git ~/.workbuddy/skills/github-readme-skill
```

It is installed once `SKILL.md` appears in that directory. Update it later with `git pull` inside the directory.

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

To see where the difference lands, count the pair above: one hint line carrying three client values before, one section per client with a complete command after.

The before line makes you work out what `-a` means, then pick one of the three values and put it back into the command; one wrong letter installs into the wrong client. After, that step is gone: the section heading is the client name and the command already has its value, so you read only your own section.

What the after version drops is the "pick clients when prompted" hint, which is no longer needed once the sections are split. The three values are not lost; each one moved into its own section's command, and the meaning of `-g` plus where to run it sits in the prerequisite line above the Install section.

This comparison looks at the Install section only, not the whole page in both versions, and says nothing about how other projects should install.

Both quotes can be matched word for word: before is [line 29 of README.en.md at 8d064ad](https://github.com/hnyxgxm/github-readme-skill/blob/8d064ad/README.en.md#L29), after is the command in the Claude Code section at [lines 29–33 of README.en.md at 3e8726c](https://github.com/hnyxgxm/github-readme-skill/blob/3e8726c/README.en.md#L29). The Chinese version quotes its own `README.md` at the same positions; each version quotes the file it links to.

If you have read the comparison above and want to check the rules or acceptance criteria behind it, start at [SKILL.md](SKILL.md) and [references/](references/).

## Use cases

A README whose structure is already clear and that only needs a typo fixed does not need this Skill; it is for rewrites, reviews and bilingual homepages, not line-by-line polishing.

It works in agents that support Agent Skills; the Install section gives commands for the common ones and the Node.js version they need, and the rules cover repository or package READMEs rather than full API manuals or general articles. You confirm the scope of changes; it will not commit, push or modify product files on its own.

Whether the result reads well still has to be seen on the target platform; the repository's own validation scripts only catch structural faults.

## License

For anyone who wants to redistribute this Skill or confirm whether it can be used in a project: this repository is released under MIT; the full terms are in [LICENSE](LICENSE).
