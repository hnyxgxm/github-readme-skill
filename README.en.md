# README Skill

[![check](https://github.com/hnyxgxm/readme-skill/actions/workflows/check.yml/badge.svg)](https://github.com/hnyxgxm/readme-skill/actions/workflows/check.yml)

[简体中文](README.md) · English

A skill that makes AI coding assistants decide how much a README should carry, then turn a project's real capabilities into a front page a stranger can judge and start using. It governs triage and evidence, not prose polish.

[Install](#install) · [Try one task](#try-one-task) · [What it produced](#what-it-produced) · [Reference files](#whats-in-the-repo)

## What it produced

The same project's front page, before and after a rewrite driven by this skill: [before 3196ad5](https://github.com/DreamOfXM/ui-taste-skill/blob/3196ad5/README.md) → [after 568b9cd](https://github.com/DreamOfXM/ui-taste-skill/blob/568b9cd/README.md) ([UI Taste Skill](https://github.com/DreamOfXM/ui-taste-skill)).

| | Before | After |
| --- | --- | --- |
| First screen | no image; one paragraph of adjectives, then 9 demo and validation entries | one positioning line + three anchors + one evidence image |
| Install | only `python3 scripts/install.py`, buried at the end of "switching an existing install" | `npx skills add`, one command, in its own section at line 22 |
| Links in first 20 lines | 15 | 6 (one language switch, three in-page anchors, two image links) |
| H2 sections | 4: Git maintenance, switching, restoring, verification | 6: rewrite process, install, try one task, see the demo, limits, license |
| Whole page | 85 lines / 0 images | 116 lines / 1 evidence image |

The opening paragraph before the rewrite read, in translation from the Chinese original:

> A design workflow for web pages, desktop software, mobile apps and web workbenches. … through content-driven direction exploration, composition and typography, material samples, continuous interaction and positive aesthetic acceptance, it helps the model produce complete and attractive interfaces …

All four H2 sections were written for people who already had it installed. The install command was not missing, just buried at the end of "switching an existing install", and only as the repo-local `python3 scripts/install.py` — the generic client entry point `npx skills add` never appeared. The rewrite won on layering rather than on vocabulary: the judgement stays on the front page, the process detail moved back into `references/`.

## What it fixes

- **Copying a docs site, or leaving readers nowhere to go**: it first asks one question — does the project link to a standalone docs site? — then picks one of three forms (router page, middle state, manual), which decides how much the README carries.
- **An overloaded first screen**: the top of the page gets exactly four things — identity, one positioning sentence, trust markers, one action or one piece of evidence — in roughly 25 lines.
- **Adjectives standing in for evidence**: the primary proof follows the deliverable — a benchmark table or terminal output for a CLI, a real before/after for an Agent Skill, a minimal call for a library. No screenshots invented to fill space.
- **Installation split into five sections**: every client shares one `npx skills` command, and differences land only in target name, directory and how it is enabled; the same client never gets two parallel channels.
- **Half-translated bilingual docs**: the two versions keep matching sections, while commands, package names, version constraints and URLs stay verbatim; a qualified claim in Chinese never becomes a guarantee in English.

## How it works

Once selected, it moves through a fixed order instead of editing wording straight away:

1. Decide the form: router page, middle state or manual — which sets how much the README must carry.
2. Fix the reader and the language coverage: who is doing what with it, and whether both languages get a full version.
3. Check facts across six headings: deliverable, value, display, onboarding, limits, follow-ups. Anything unverifiable narrows the claim instead of becoming an invented URL, package name or compatibility list.
4. Write the four-part first screen, then order the body by evidence: proof → entry → first result → capabilities → limits → signposting.
5. Apply the layout rules: one H1 per document, commands separated into input and output, collapsibles reserved for optional branches.
6. Review against the [acceptance method](references/acceptance.md): facts, every install branch actually walked, bilingual parity, and rendering at narrow width — only then is it delivered.

## Install

This is an instruction and reference package for coding assistants, not standalone software. The README exists in Chinese and English; **the skill instructions and reference files are currently Chinese only**.

Review [SKILL.md](SKILL.md) and `references/` first to see what it will tell an assistant to do. Installing writes into a skills directory; if a skill with the same name already exists, check its source first.

All three clients share one `skills` CLI command and install the same complete package. It needs **Node.js 22.20+** (the current `engines` requirement of the `skills` package) and the client itself. Run this in any directory:

```sh
npx skills add hnyxgxm/readme-skill -g
```

Pick clients when prompted, or specify them with `-a`. `-g` installs at user level for all projects; drop `-g` inside a target project to install only there.

- **Claude Code** (`-a claude-code`): `~/.claude/skills/`; type `/` in a new session and choose `readme-skill`
- **Codex** (`-a codex`): `~/.agents/skills/`; type `$readme-skill` in a new session
- **Qoder Desktop** (`-a qoder`): `~/.qoder/skills/`; type `/` in a new task and choose `readme-skill`

Start a new session afterwards and confirm the skill appears in the picker. If it does not, check that the directory contains `SKILL.md` and `references/`, that the path matches the list above, then restart the client.

Fallback without Node.js: copy the whole repository directory (including `references/`) into any of the skill directories above, then restart the client. Cursor, OpenCode and Gemini CLI use the same command with their own target names, listed in the [supported agents file](https://github.com/vercel-labs/skills/blob/main/docs/agents.md); the installer supporting a client does not mean this skill has been verified there.

Maintenance: `npx skills update readme-skill -g` to update, `npx skills remove readme-skill -g` to uninstall; with several clients installed you are prompted to choose, or pass `-a`.

## Try one task

Select the skill in an existing project, point it at the repository or current README, then send:

```text
Use readme-skill to review and rewrite this repository's README.
Decide first whether it should be a router page or a manual, and propose a structure before writing.
Treat the current code and release artifacts as the only facts; omit anything you cannot verify.
Both languages, local edits only — do not commit or push.
```

The first response should be a form judgement and a structure, not a finished page. A delivery should name its primary evidence, what was moved off the front page, which directory each command runs in, and which facts remain unverified.

Add "review only, don't touch the files" to skip edits; scope a fix to one section when only that section is broken.

## What's in the repo

- [SKILL.md](SKILL.md): the main chain, eight sections from form to acceptance.
- [Structure, layout and editing patterns](references/patterns.md): skeletons for seven project types, first-screen composition, the evidence matrix, "one install path, branching parameters", and bilingual trade-offs.
- [Examples](references/examples.md): per-item triage across 14 real repository front pages, plus what those samples do not justify.
- [Acceptance method](references/acceptance.md): form gate, facts and limits, walking every branch, first-screen evidence, bilingual parity, rendering and sign-off criteria.
- [Rendering and sizes](references/rendering.md): measured column width, type-size conversion and image-width behaviour, with a check script. (Chinese only.)
- [How to draw the images](references/visual-craft.md): canvas and type-size tables, why only system fonts work, three ways to handle light/dark, and measured GIF encoding settings. (Chinese only.)
- [Maintenance and regression](references/maintenance.md): how to compare old and new versions when editing the skill itself, instead of trusting the change note.
- `scripts/`: `check-assets.py` flags images and file links that will break (including wrong case, `style="width:"`, `=WxH`, and the `<picture>` sources browsers actually load); `check-text.py` checks first-screen length, anchors, bilingual structure and terminology drift. Both ship with `--selftest`; column width is overridable with `--column-width`.
- `.github/workflows/check.yml`: on every push, runs both selftests and then points the scripts at these two READMEs, `SKILL.md` and `references/`. A green badge means the mechanical checks pass, nothing more.
- [`terms.txt`](terms.txt): this skill's own internal vocabulary, fed to `check-text.py --terms`. It governs how this repo names things, not what a user's README may say; hits in someone else's document are reported as hints only.

The scripts only decide the mechanical half, not whether the writing is any good. Inside this repository:

```sh
python3 scripts/check-assets.py README.md
python3 scripts/check-text.py README.md README.en.md --pair --terms terms.txt
```

Once installed as a skill, the working directory is someone else's repository while the scripts and word list stay in the skill directory, so they must be called by absolute path or they will not be found:

```sh
SKILL=~/.claude/skills/readme-skill
python3 "$SKILL/scripts/check-assets.py" README.md
python3 "$SKILL/scripts/check-text.py" README.md README.en.md --pair --terms "$SKILL/terms.txt"
```

Exit code 0 means nothing will break; 1 means something must be fixed. Every finding is labelled as measured here, a platform limit, or an engineering threshold.

## Limits

- It supplies judgement and a checklist; it does not guarantee any model produces a good front page on the first pass. Output still depends on the model, the repository facts you provide and whether you check the result item by item.
- It will not choose a license, a distribution channel or a push moment for you. Writing docs is not authorization to commit, push, deploy or install extensions.
- README rendering is constrained by the platform: GitHub strips scripts and inline CSS, cannot produce horizontal tabs, and gives Markdown no layout containers. Anything important must read at normal width and at roughly 390px.
- Facts are pinned to repository state. The samples here cite [UI Taste Skill](https://github.com/DreamOfXM/ui-taste-skill) commit history, and both links point at fixed commits, so they will not drift as that repository evolves.

## License

Released under the [MIT License](LICENSE): commercial and non-commercial use, modification and redistribution are permitted, provided the copyright and permission notices are kept in copies. Author: hnyxgxm.
