# README Skill

[![check](https://github.com/hnyxgxm/github-readme-skill/actions/workflows/check.yml/badge.svg)](https://github.com/hnyxgxm/github-readme-skill/actions/workflows/check.yml) [![license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) [![node](https://img.shields.io/badge/node-22.20%2B-339933)](https://nodejs.org/)

[简体中文](README.md) · English

Makes a coding assistant decide how much a README should carry, then reorganise it on that decision: pick the form, reorder the sections, verify the facts, and run two scripts so mechanical faults never reach a release. It governs triage and evidence, not prose polish.

[Install](#install) · [Quick start](#quick-start) · [Examples](#examples) · [Use cases](#use-cases)

The positioning paragraph below comes from one repository, before and after. Both originals are in the commit history — open them and compare:

> **Before** ([3196ad5](https://github.com/DreamOfXM/ui-taste-skill/blob/3196ad5/README.md)): 面向网页、桌面软件、移动 App 和 Web 工作台的设计工作流。以出众美感、优美秩序、精致质感与产品自身气质为目标：可用和整齐只是底线。通过内容驱动的方向探索、构图与排印、材料样片、连续交互和正向审美验收，帮助模型做出完整而有吸引力的界面；为易漂移或不能读图的实现者提供明确的视觉执行包。不是固定皮肤，也不承诺所有模型必然产出优秀作品；跨模型效果仍需受控实验。

> **After** ([568b9cd](https://github.com/DreamOfXM/ui-taste-skill/blob/568b9cd/README.md)): 让 AI 编程助手把界面改版做成可检查的过程：先比较两个视觉方向，再用设计卡约束实现，最后在最密的一屏和窄屏上验收。

Both paragraphs describe the same thing. The original reaches "helps the model produce a usable interface" in its fifth clause; the rewrite states the purpose in its first sentence and puts the mechanism after a colon.

## Install

This is a judgement rulebook and reference set for a coding assistant, not standalone software. The README exists in Chinese and English; **the skill instructions and reference files are currently Chinese only**.

It needs **Node.js 22.20+** — that is the `engines` requirement of the `skills` package, not a dependency of this repository (source: `package.json` of `skills@1.7.6`, value `>=22.20.0`). Run this in any terminal:

```sh
npx skills add hnyxgxm/github-readme-skill -g
```

Pick clients when prompted, or name one with `-a`: `claude-code`, `codex`, `qoder`. `-g` installs at user level for every project; drop `-g` inside a target repository to install only there. The installer prints which client it landed in — open a new session and the skill appearing in the list is your confirmation.

## Quick start

Select the skill in a project, point it at the repository or the current README, and send:

```text
Use github-readme-skill to review and rewrite this repository's README.
Decide first whether it should be a router page or a manual, then propose a structure before writing.
Treat the current code and release artifacts as the only facts; mark anything you cannot verify as unverified.
Both languages, local edits only — do not commit or push.
```

You get a form judgement and a structure first, and the full text only after you confirm — a finished page written in the wrong direction is a hundred wasted lines. On delivery it has to name four things: the primary evidence, what was moved off the front page, where each command runs, and which facts remain unverified.

Add "review only, do not touch any files" to skip edits; name the scope when only the install section is broken, so it does not redo the whole page.

## Features

Six things, each judged before anything is written:

- **No idea how much the page should carry**: ask "besides this README, does the reader have somewhere else to go", choose one of three forms — router page, middle state, manual — and the form sets length and sections. A repository with `docs/` that the README never links to is a middle state: the fix is adding the entrance, not copying the docs in.
- **An overloaded first screen**: four things only — identity, one positioning sentence, trust markers, first result — within about 25 lines. If install lands after the fourth section, the first screen has to link to it.
- **Adjectives standing in for evidence**: the primary proof follows the deliverable. Terminal output or a benchmark table for a CLI, a minimal call for a library, a real before/after for an Agent Skill. No image invented to fill space.
- **A difference nobody can name**: write it as a comparison of two practices, never as "faster, more elegant"; give numbers an environment and mark anything unverified as unverified instead of inventing a plausible figure.
- **Installation written as a list of directories and keypresses**: when clients share one command, the difference collapses into one parameter and one sentence. Install directories and which key to press afterwards stay out of the README — they expire with the next client release, and one command told three times reads like three ways to install.
- **Checking the mechanical details by eye before release**: broken anchors, image path case, first-screen length, version numbers with no counterpart in the repository. Two scripts decide those, and one run beats three read-throughs.

## Examples

The two paragraphs above are one repository. Its two versions differ structurally as follows — left is [3196ad5](https://github.com/DreamOfXM/ui-taste-skill/blob/3196ad5/README.md), right is [568b9cd](https://github.com/DreamOfXM/ui-taste-skill/blob/568b9cd/README.md):

- **H2**: 4 (Git maintenance, Switching an existing install, Restoring the original install, Verification) → 6 (Rebuild workflow, Install, Try one task, See the examples, Limits and references, License)
- **Install**: no `npx skills add`; only the in-repo script `python3 scripts/install.py` → second H2, one command
- **First screen**: a 181-character paragraph, then 7 bullets, first section on line 15 → one positioning line, three anchors, one piece of primary evidence, first section on line 13
- **Whole page**: 85 lines, 0 images → 116 lines, 1 image

The rewrite is 31 lines longer. All four original sections spoke to people who had already installed it — switching branches, restoring, verifying — so a first-time reader never learned what to do first. Nothing was dropped: the maintenance notes were folded into a collapsible block under "Limits and references", and the front page was reordered for the reader arriving for the first time — what it does, how to install, one task to try, what the output looks like, then the limits.

Line counts, section counts and image counts come from the two commits above; open them and count. Both have changed since, so no "current" numbers appear here.

## Use cases

This is probably how you write one now: open an editor and go from the title down, wherever the writing leads; skim two similar repositories for a structure; add a few badges, drop in a screenshot, end with "stars welcome". It ships, nobody uses it, and you cannot say which part was wrong.

With this skill the order reverses: decide how much the page should carry, order the sections the way a reader meets them, then run the scripts so mechanical faults stop at the release gate.

Built for projects with real code and a release that are heading public — especially personal tools, internal CLIs and Agent Skills with no docs site. Those default to the manual form, so it will not point you at a docs site you do not have.

Do not use it when:

- **You only need a typo or a badge fixed.** Just do it. This is a structural review, and re-flowing the whole page for two lines is a bad trade.
- **You need a full API reference.** That belongs in a docs site or `docs/`; a README is the entrance.
- **You only dislike the tone.** It does not touch tone — that is the project's own voice.
- **There are no verifiable facts yet.** It will keep asking, and with nothing to answer all that is left is structure. Build the thing first.

Other limits:

- It supplies a judging method and an acceptance checklist; it does not guarantee that any model produces a good front page in one pass. The result depends on the model, the repository facts you supply, and whether you check the output item by item.
- It will not choose a licence, a distribution channel or a moment to push. Writing docs is not authorization to commit, push or deploy.
- GitHub strips scripts and inline CSS, cannot render horizontal tabs, and gives Markdown no layout containers. Anything essential has to read at normal width and at roughly 390px.
- The frontmatter declares `allowed-tools`. Per the [compatibility table](https://github.com/vercel-labs/skills/blob/main/docs/agents.md), Qoder, Kiro CLI and Zencoder ignore that field, so tool permissions follow the client's own rules there.

## Development

The judging method, the seven skeletons, the examples, the acceptance checks and the drawing rules all live in [SKILL.md](SKILL.md) and `references/`; read [Maintenance and regression](references/maintenance.md) before changing the skill itself.

Both scripts use nothing but the Python 3 standard library (3.8 or newer) and ship with `--selftest`. Inside this repository:

```sh
python3 scripts/check-assets.py README.md README.en.md
python3 scripts/check-text.py README.md README.en.md --pair --terms references/terms.txt
```

Once installed as a skill, the working directory is someone else's repository while the scripts and the word list stay in the skill directory, so they must be called by absolute path:

```sh
SKILL=<where the skill is installed>   # e.g. ~/.claude/skills/github-readme-skill
python3 "$SKILL/scripts/check-assets.py" README.md
python3 "$SKILL/scripts/check-text.py" README.md README.en.md --pair --terms "$SKILL/references/terms.txt"
```

Exit code 0 means nothing will break; 1 means something must be fixed. Every finding is labelled as measured here, a platform limit, or an engineering threshold. The scripts decide only the mechanical half — a green badge says that half passed, nothing about whether the writing is any good.

## License

Released under the [MIT License](LICENSE): commercial and non-commercial use, modification and redistribution are permitted, provided the copyright and permission notices are kept in copies. Author: hnyxgxm.
