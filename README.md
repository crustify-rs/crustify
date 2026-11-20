<p align="center">
  <img src="docs/assets/crustify.svg" width="170" alt="Crustify's logo: a crab that is also a robot">
</p>

<h1 align="center">Crustify</h1>

<p align="center">
  <b>Your AI co-translator for automating C-to-Rust work.</b>
</p>

<p align="center">
  <a href="https://arxiv.org/abs/2611.10394"><img src="https://img.shields.io/badge/arXiv-2611.10394-B31B1B?style=flat-square&logo=arxiv&logoColor=white" alt="Paper on arXiv: 2611.10394"></a>
  <img src="https://img.shields.io/badge/Claude_Code-plugin-D97757?style=flat-square&logo=claude&logoColor=white" alt="Claude Code plugin">
  <img src="https://img.shields.io/badge/Codex-supported-555555?style=flat-square" alt="Codex supported">
  <img src="https://img.shields.io/badge/C_%E2%86%92_Rust-safe-CE422B?style=flat-square&logo=rust&logoColor=white" alt="C to safe Rust">
  <img src="https://img.shields.io/badge/Linux-x86--64-555555?style=flat-square&logo=linux&logoColor=white" alt="64-bit Linux">
  <img src="https://img.shields.io/badge/Python-3.13-555555?style=flat-square&logo=python&logoColor=white" alt="Python 3.13">
</p>

<p align="center">
  <a href="#why-crustify">Why</a> ·
  <a href="#installation">Install</a> ·
  <a href="#usage">Usage</a> ·
  <a href="#how-it-works">How it works</a> ·
  <a href="#results">Results</a> ·
  <a href="https://arxiv.org/abs/2611.10394">Paper</a>
</p>

---

Crustify is a plugin for Claude Code and Codex that turns LLMs into specialized
C-to-safe-Rust translators:

- **Migrations.** Port whole codebases or a few components that keep working with the
  remaining C, with an API suitable for both Rust and C consumers.
- **Wrappers.** A safe, ergonomic Rust API over C you keep.
- **Audits.** Undefined behavior, unsound contracts, divergences from the C and other bug
  classes in Rust that meets C, each with a reproducer.

## Why Crustify

- ✅ **Empirically verified in an agentic feedback loop.** Independent reviewers, tests
  that pass Miri and the sanitizers, lints and formatters. Every fix comes with a
  regression test.
- ⚡ **Fast Rust code, never at the cost of safety or correctness.**
- 🎯 **Equivalent to the C, without its defects.**
- 🔍 **Finds correctness gaps** against whatever spec is available: documentation,
  headers, tests, reference implementations.
- 🧩 **Customizable.** Add objectives in the prompt, such as matching the C's style or
  maximizing coverage-guided testing.
- 📈 **Gets better as it goes.** Recurring defect classes become checks that run on every
  later component and stay with your code.
- 🕹️ **Autonomous or supervised.** Let it run end to end, or step in at any point.

## Installation

Crustify runs on 64-bit Linux. It needs Claude Code or Codex, and Python 3.13. Clone the
components side by side and install the tools, each on its `devel` branch; `ffibox` is a
crate the port depends on, so it is only cloned.

```bash
git clone https://github.com/crustify-rs/crustify.git
git clone --branch devel https://github.com/crustify-rs/ffibox.git
git clone --branch devel https://github.com/crustify-rs/ffimap.git

python -m pip install -e ffimap
```

> [!TIP]
> To skip the setup, [`templates/docker/`](templates/docker/README.md) builds an image with
> everything a port needs: both agent CLIs, CodeQL, bindgen, Miri and the sanitizer
> toolchains.

## Usage

Open Crustify in the checkout of the C codebase, and name the task in your first message:
the components to port, the build configuration, and anything else the port must respect.

<details open>
<summary><b>Claude Code</b></summary>

```bash
claude --plugin-dir /path/to/crustify --agent crustify:crustify
```

</details>

<details>
<summary><b>Codex</b></summary>

Install the profile once, then open it:

```bash
python3 /path/to/crustify/providers/codex/install.py    # add --model-proxy openrouter --model <model> for OpenRouter
codex --profile crustify
```

Rerun the installer after the checkout changes. It warns when Codex's sandbox cannot start
on the host; `--sandbox full` is for a container.

</details>

<details>
<summary><b>Other agent harnesses</b></summary>

[`providers/generic/compose.py`](providers/generic/compose.py) prints the whole prompt,
with an index of the skills, for any harness that can run shell commands, edit files and
spawn sub-agents:

```bash
python3 /path/to/crustify/providers/generic/compose.py
```

</details>

## How it works

One agent runs the port. It builds the C, decides the scope and the order, spawns
subagents to port independent components in parallel and others to review them, and
merges their work. The system prompt,
[`agents/crustify.md`](agents/crustify.md), gives the requirements of the ported code,
functional and non-functional, and the process: work in parallel, review every component
against every requirement, learn from earlier findings, and keep `STATUS.md` current. Everything else is a skill:

| group | skills |
|---|---|
| [`conventions/`](skills/conventions/SKILL.md) | the port's files under `.crustify/`, the anchors that name the C item each Rust item stands in for, the lints, and the language of its texts |
| [`tools/`](skills/tools) | `bindgen`, `ffibox`, `ffimap` |

The port ends with `.crustify/REPORT.md`: the configuration, the boundary between Rust and
C, the defects found in the C, the performance numbers and what was verified how.

## Results

Crustify's earlier, multi-agent version generated safe bindings for two libraries, with
little guidance from one developer overseeing it, as our
[paper](https://arxiv.org/abs/2611.10394) details. Binder and reviewer
agents mainly ran Claude Opus 5.5; GPT-6.1 Sol and GPT-6 Astra wrapped a few modules, and
Claude Fable 5.1 ran the early reviews.

<table align="center">
  <tr>
    <td align="center"><h3>1,053</h3>public API items wrapped</td>
    <td align="center"><h3>≥ 98.9%</h3>Rust line coverage</td>
    <td align="center"><h3>≤ 1.6%</h3><code>unsafe</code> public API</td>
    <td align="center"><h3>21</h3>UB defects fixed in review</td>
  </tr>
</table>

| | [libgit2](https://github.com/crustify-rs/libgit2-crustify) | [FFmpeg](https://github.com/crustify-rs/ffmpeg-crustify) |
|---|---:|---:|
| Public API wrapped | 480 of 1,146 items (41.9%) | 573 of 1,338 items (42.8%) |
| Wall-clock time | 51.9 h | 58.9 h |
| Cost | $2,308 | $2,120 |
| `unsafe` public API (consumer-facing) | 42 of 2,663 functions (1.6%) | 11 of 2,637 functions (0.4%) |
| Raw pointers in public API (consumer-facing) | 2 functions (0.1%) | 16 functions (0.6%) |
| Tests: unit / equivalence / UB | 787 / 489 / 788 | 968 / 723 / 1,003 |
| Line coverage, Rust / C | 98.9% / 46.0% | 99.1% / 67.2% (`libavutil`) |
| UB defects the reviewers fixed | 8 | 13 |
| Rust LoC | ~18K | ~19K |

Each repository holds the code, the campaign's plan, its review reports and its
dashboard.

## Repository

- [`agents/crustify.md`](agents/crustify.md): the system prompt
- [`skills/`](skills/): the skills
- [`rsi/`](rsi/README.md): the patterns ports learn that hold beyond their codebase, and the harness changes they propose
- [`providers/`](providers/): the prompt composed for each host:
  [`claude/`](providers/claude/), [`codex/`](providers/codex/), and
  [`generic/`](providers/generic/compose.py) for any other
- [`templates/`](templates/README.md): the format of `STATUS.md`, and the
  Dockerfile

## Maintainers

- Marius Momeu, University of California, Berkeley

## Citation

```bibtex
@misc{momeu2026crustify,
  title         = {Crustify: Repository-Level Generation of Safe Rust Bindings with {LLM} Agents and Coverage-Guided Testing},
  author        = {Momeu, Marius and Arvinte, Marius and Cornelius, Cory and Sen, Koushik},
  year          = {2026},
  eprint        = {2611.10394},
  archivePrefix = {arXiv},
  primaryClass  = {cs.PL},
  url           = {https://arxiv.org/abs/2611.10394}
}
```
