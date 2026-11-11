# Crustify

**Crustify is your AI co-translator for automating C-to-Rust work.** It is a plugin for Claude Code
and Codex that turns LLMs into specialized translators that plan, run and review
whole-repository campaigns. It can:

- **Generate safe Rust bindings over C.**
- **Migrate C to safe Rust.**
- **Audit Rust for UB and memory-safety bugs.**

You set the goals and a few settings; Crustify does the rest, on its own or with you in
the loop.

## Why Crustify

- Driven by a generic, human-reviewed specification, not only a prompt.
- Whole repositories, in parallel.
- Grounded in deterministic tools: [wavefront](https://github.com/crustify-rs/wavefront),
  [ffibox](https://github.com/crustify-rs/ffibox) and
  [ffimap](https://github.com/crustify-rs/ffimap).
- Validated before it lands, with coverage-guided tests and adversarial review.
- You choose the translator's autonomy.
- Any agent harness, any billing.
- Fine-grained cost tracking.

## Results

Crustify generated safe bindings for two libraries, with little guidance from one developer
overseeing it, as our [paper](https://arxiv.org/abs/2611.10394) details. Binder and reviewer
agents mainly ran Claude Opus 5.5; GPT-6.1 Sol and GPT-6 Astra wrapped a few modules, and
Claude Fable 5.1 ran the early reviews.

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

## Installation

Crustify runs on 64-bit Linux and translates targets built there, against glibc. It needs
Claude Code or Codex, and Python 3.13. Clone the components side by side and install the
tools, each on its `devel` branch, the line campaigns run; `ffibox` is a crate the
generated Rust depends on, so it is only cloned.

```bash
git clone https://github.com/crustify-rs/crustify.git
git clone --branch devel https://github.com/crustify-rs/wavefront.git
git clone --branch devel https://github.com/crustify-rs/ffibox.git
git clone --branch devel https://github.com/crustify-rs/ffimap.git

python -m pip install -e wavefront -e ffimap
```

To skip the setup, [`templates/docker/`](templates/docker/README.md) builds an image with
everything a campaign needs: both agent CLIs, CodeQL, bindgen, Miri and the sanitizer
toolchains.

## Usage

Open Crustify's assistant in the directory a campaign is to work in.

### Claude Code

```bash
claude --plugin-dir /path/to/crustify --agent crustify:assistant-translate   # wrap or port
claude --plugin-dir /path/to/crustify --agent crustify:assistant-audit       # audit
```

### Codex

Install the agent roles and the assistant's profiles once, then open a profile:

```bash
python3 /path/to/crustify/providers/codex/install.py    # add --model-proxy openrouter --model <model> for OpenRouter
codex --profile crustify-translate                      # or crustify-audit
```

Trust the plugin's hook once with `/hooks`, and rerun the installer after the checkout
changes. The installer warns when Codex's sandbox cannot start on the host; `--sandbox
full` is for a container.

### Other agent harnesses

[`providers/generic/compose.py`](providers/generic/compose.py) prints each agent's whole
prompt, with an index of the skills, for any harness that can run shell commands, edit
files and spawn sub-agents:

```bash
python3 /path/to/crustify/providers/generic/compose.py assistant translate   # or: assistant audit
python3 /path/to/crustify/providers/generic/compose.py binder                # planner, binder, translator, reviewer
```

Run the assistant's prompt as the main agent's, and register each stage's prompt as a
sub-agent it can spawn. Agents read the skills from the checkout, by the paths the
prompts name.

### Running a campaign

Tell the assistant what you want in plain language: wrap the public API, port the
parser, audit the crate. It asks what it needs, such as the revision, the models and how
much autonomy it has, and presents a campaign brief for your approval before it changes
anything. To answer up front, fill in a settings template,
[`templates/translate/`](templates/translate/CRUSTIFY.template.md) or
[`templates/audit/`](templates/audit/CRUSTIFY.template.md). The settings live in the
campaign's repository as `crustify/CRUSTIFY.md`, which you can edit while it runs.

## How it works

Every agent follows the same written specification, as skills: how the codebase is
decomposed, how each kind of C item becomes Rust, and how work is tested, reviewed and
landed. Runs are consistent across models and reproducible, and you don't reinvent the
workflow for each codebase.

Crustify's assistant talks to you and launches four kinds of agent:

| Agent | Role |
|---|---|
| **assistant** | Configures the campaign, prepares builds and test baselines, launches the other agents, lands and promotes their work, and keeps the dashboard. |
| planner | Decomposes the codebase into modules, one per translation unit, and schedules them into waves and batches by their dependencies. |
| binder | Wraps a batch: keeps its C and puts a safe Rust API in front of it. |
| translator | Ports a batch to safe Rust. |
| reviewer | Reviews what a wave landed for unsafety, undefined behavior and equivalence with the C, files a report and reproducer per finding, and fixes it. |

Agents run in parallel, each in its own Git worktree and seeing only its own batch. Every
batch gets coverage-guided tests for equivalence with the C and for undefined behavior
under ASan, UBSan, TSan, MSan, Miri and BorrowSanitizer, and passes the target's own test
suite before it lands; independent, adversarial reviewers then check each wave before its
dependents start. The assistant reconciles the results and repairs what fails. An audit
runs the reviewers alone over an existing crate.

Deterministic tools ground the agents' judgement:

- [wavefront](https://github.com/crustify-rs/wavefront) sorts the C codebase into
  dependency-ordered waves from CodeQL facts;
- [ffibox](https://github.com/crustify-rs/ffibox) provides the owners and handles the
  generated Rust holds C memory through; and
- [ffimap](https://github.com/crustify-rs/ffimap) measures the unsafe and FFI surface per
  batch, wave, module and campaign.

You choose how much control to keep: run a campaign end to end, or approve its brief, plan
one module and stop, and decide as questions come up; edit its settings mid-campaign to
change course. Each stage runs on Claude Code, Codex or any other agent harness, with its
own model, under a subscription or an API key, directly or through OpenRouter. A
dashboard tracks tokens, cost and time per batch, module and campaign, next to coverage
and the unsafe surface.

## Repository

- [`skills/`](skills/): the specification, one skill per part of a campaign, from its
  workflow and planning, through the generated Rust and its verification, to its
  operations, artifacts and tools
- [`agents/`](agents/): each agent's role, workflow and inputs
- [`providers/`](providers/): each host's composition of the agents:
  [`claude/`](providers/claude/), [`codex/`](providers/codex/), and
  [`generic/`](providers/generic/compose.py), which prints an agent's whole prompt for any
  other host
- [`templates/`](templates/README.md): the settings and dashboard templates, an example
  of each artifact, and the Dockerfile

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
