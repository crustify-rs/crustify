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
C-to-safe-Rust translators. It automates:

- **Migrations.** Port whole codebases or a few components that keep working with the
  remaining C, and offer an API compatible with both Rust and C consumers.
- **Wrappers.** A safe, ergonomic Rust API over C you keep.
- **Audits.** Undefined behavior, unsound contracts, divergences from the C and other bug
  classes in Rust that meets C, each with a reproducer.

## Why Crustify

- ✅ **Verified** empirically in an agentic feedback loop: independent reviewers, tests
  that pass Miri and the sanitizers, lints and formatters. Every fix comes with a
  regression test.
- ⚡ **Fast** Rust code, never at the cost of safety or correctness.
- 🎯 **Equivalent** to the C, without its defects.
- 🔍 **Correctness gaps** found against whatever spec is available: documentation,
  headers, tests, reference implementations.
- 🧩 **Customizable** with further objectives in the prompt, such as matching the C's
  style or maximizing coverage-guided testing.
- 📈 **Improves** as it goes: recurring defect classes become checks that run on every
  later component and stay with your code.
- 🕹️ **Autonomous** or supervised: let it run end to end, or step in at any point.

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

To audit a crate, open the auditor in the crate's checkout instead, and see
[`docs/audit.md`](docs/audit.md) for what to put in the request:

```bash
claude --plugin-dir /path/to/crustify --agent crustify:audit
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

The auditor, [`agents/audit.md`](agents/audit.md), checks a crate against the same
objectives. It files each defect that the project does not know about yet as a finding,
with a reproducer, a witness or a review, and keeps going until it has 25 findings of
unknown defects or the budget is spent. It posts nothing; with `disclose` on, it drafts
the report that you send. [`docs/audit.md`](docs/audit.md) describes how to run it on
your own crate.

## Results

### Bindings

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

### Audits

Crustify's auditor audited 16 widely used crates that wrap C and C++ libraries or system
calls, at a median cost of $44 per audit.

<table align="center">
  <tr>
    <td align="center"><h3>225</h3>undefined-behavior bugs</td>
    <td align="center"><h3>36</h3>incomplete <code>unsafe</code> contracts</td>
    <td align="center"><h3>23</h3>divergences from the C</td>
    <td align="center"><h3>26 of 83</h3>reported findings fixed</td>
  </tr>
</table>

The crates and what they wrap: `aws-lc-rs` (AWS-LC), `curl` (libcurl), `ffmpeg-next`
(FFmpeg), `flate2` (zlib backends), `git2` (libgit2), `mio` (system calls), `mlua` (Lua),
`nix` (system calls), `openssl` (OpenSSL), `rocksdb` (RocksDB), `rusqlite` (SQLite),
`socket2` (system calls), `ssh2` (libssh2), `tree-sitter` (the tree-sitter runtime), `v8`
(V8) and `zstd` (Zstandard).

## Repository

- [`agents/crustify.md`](agents/crustify.md): the system prompt
- [`agents/audit.md`](agents/audit.md): the auditor's system prompt, and
  [`docs/audit.md`](docs/audit.md), how to audit a crate with it
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
