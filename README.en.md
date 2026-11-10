# README Skill

[![check](https://github.com/hnyxgxm/github-readme-skill/actions/workflows/check.yml/badge.svg)](https://github.com/hnyxgxm/github-readme-skill/actions/workflows/check.yml) [![license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) [![node](https://img.shields.io/badge/node-22.20%2B-339933)](https://nodejs.org/)

[简体中文](README.md) · English

An Agent Skill that writes or rewrites a GitHub README. It reads the project, works out who will read it, and only then starts writing. The result uses short subject-verb-object sentences, covers features and usage only, and leaves implementation details out. Section headings come from what the reader does in that section, not from a fixed template.

![This README before and after a rewrite: on the left the first screen is a wall of text with install buried mid-document; on the right it holds only a positioning line, badges and one install command](assets/before-after.en.svg)

This README's first screen, before and after. On the left you cannot tell what to do next; on the right install sits directly below.

## What it does

- Reads project files and lists facts you can check.
- Works out what kind of project this is, who reads it, and what they do first.
- Sets the section order from that first action, then decides on images and video.
- Runs checks on links, anchors, images and the first screen when the draft is done.

Before writing a line, the skill shows a six-line conclusion so you can agree on the plan.

## Install

This is an instruction and reference package for coding assistants, not standalone software. The README exists in Chinese and English; the skill instructions and reference files are currently Chinese only. To see what it will tell an assistant to do, read [SKILL.md](SKILL.md) and `references/` directly.

All three clients share one `skills` CLI command and install the same complete package. It needs Node.js 22.20+ and the client itself. Run this in any directory:

```sh
npx skills add hnyxgxm/github-readme-skill -g
```

Pick clients when prompted, or specify them with `-a`. `-g` installs at user level. Without Node.js, copy the whole directory (including `references/`) into a skills directory such as `~/.claude/skills/`, then restart the client.

Python 3.8 or newer is required, standard library only. The optional GIF and video checks need `ffmpeg` and `gifsicle`; everything else works without them.

## Use

Select the skill in an existing project, give it the repository path or current README, then type:

> Use github-readme-skill to review and rewrite this repository's README. Show me the six-line conclusion first and wait for my confirmation. Stick to the code and release artifacts in the repository, and leave out anything you cannot verify.

Add "do not modify files yet" to get a review only. Name the section you want changed instead of asking for a full rewrite.

The probe script also runs on its own:

```bash
python3 scripts/detect_project.py /path/to/repo
python3 scripts/detect_project.py --selftest
```

## Repository layout

| Path | What it is |
| --- | --- |
| `SKILL.md` | Main file: four analysis steps, section order, sentence rules, constraints, checks |
| `references/project-analysis.md` | Project categories and reader analysis |
| `references/section-templates.md` | Six positions and skeletons; headings are placeholders |
| `references/media-decisions.md` | Image and video decisions, platform limits |
| `references/eval-plan.md` | How to check whether a change helped |
| `references/rendering.md`, `visual-craft.md`, `terms.txt` | Render measurements, drawing guide, word list |
| `scripts/detect_project.py` | Reads project facts, prints JSON, has a selftest |
| `scripts/check-text.py`, `check-assets.py` | Text structure and image asset checks |

## Development

The scripts all have `--selftest`. After changing a rule, run the selftests, then try a real repository or two.

```bash
python3 scripts/detect_project.py --selftest
python3 scripts/check-text.py --selftest
python3 scripts/check-assets.py --selftest
```

Check a finished README with:

```bash
python3 scripts/check-text.py README.md --terms references/terms.txt
python3 scripts/check-assets.py README.md
```

## License

[MIT](LICENSE). Author: hnyxgxm.
