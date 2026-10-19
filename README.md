**Crustify** is your co-translator for C-to-Rust work. You describe the task, and
Crustify plans it with you, runs it, and reports back. It can:

- port an implementation to native Rust, fully or partially;
- generate safe Rust wrappers over an unsafe C API; or
- find undefined behavior and memory-safety bugs in safe Rust code.

For a large task, Crustify orchestrates an end-to-end workflow. It splits the codebase
into subsystems, schedules them in dependency order, and hands each batch to a focused
sub-agent. Sub-agents run in parallel, each in its own worktree with only its own
worklist in context, so none of them carries the whole codebase. Crustify keeps the
campaign's state, lands their work behind build, test and safety gates, and asks you
whenever a decision is yours.

Deterministic tools ground the agents' judgement:

- [wavefront](https://github.com/crustify-rs/wavefront) orders the C codebase into
  dependency-sorted waves, from CodeQL facts;
- [ffibox](https://github.com/crustify-rs/ffibox) provides the smart pointers and
  lifetime traits the generated Rust builds on;
- [ffimap](https://github.com/crustify-rs/ffimap) measures the resulting unsafe and FFI
  surface; and
- the target's own tests run under sanitizers.

## Agents

| Agent | Role |
|---|---|
| **Crustify**, the assistant | Talks to you, configures the campaign, prepares builds and baselines, launches the other agents, lands and promotes their work, and keeps the dashboard. |
| planner | Splits the codebase into subsystems and schedules each one's waves and batches. |
| binder | Wraps a batch: keeps its C implementation and puts a safe Rust API in front of it. |
| translator | Ports a batch to safe Rust. |
| reviewer | Reviews what a wave landed, for unsafety, undefined behavior and equivalence with the C, files a report and reproducer per finding, and fixes them. |

The assistant also repairs: it diagnoses failed agents, merge conflicts and regressions,
then retries or reschedules the affected work. The reviewers test adversarially: they are
independent of the agents whose work they review.

The [audit campaign](docs/audit/audit.md) runs the reviewers alone over any Rust crate
that wraps C.

## Components

| Component | Responsibility |
|---|---|
| `crustify` | Agent execution, isolated worktrees, crate placement, logging, and campaign artifacts |
| [`wavefront`](https://github.com/crustify-rs/wavefront) | CodeQL-backed dependency analysis, scope selection, and deterministic scheduling |
| [audit campaigns](docs/audit/audit.md) | UB review of any Rust crate that wraps C, by the same reviewers a translation uses |
| [`ffibox`](https://github.com/crustify-rs/ffibox) | Safe FFI smart pointers and lifetime traits used by generated wrappers |
| [`ffimap`](https://github.com/crustify-rs/ffimap) | Deterministic unsafe and FFI surface counts, recorded per batch, wave, subsystem and campaign |

Claude Code and OpenAI Codex are supported as agent backends with access to latest
closed- and open-weight models. Campaigns can use
API or subscription billing and can select a model independently for each
agentic stage. The recommended baseline is `claude-opus-5` for the
assistant, `gpt-5.6-sol` for translators, and `claude-opus-5` again for the
review and UB passes.

## Quick start

Crustify requires Python 3.13. Clone the three components side by side and
install the two Python packages; `ffibox` is a Rust crate that generated
wrappers depend on, so it is cloned but not installed:

```bash
git clone https://github.com/crustify-rs/crustify.git
git clone https://github.com/crustify-rs/wavefront.git
git clone https://github.com/crustify-rs/ffibox.git

python -m pip install -e crustify
python -m pip install -e wavefront
```

Optionally copy and pre-fill the campaign questionnaire before starting
Crustify:

```bash
cp crustify/templates/translate/CRUSTIFY.template.md campaign-CRUSTIFY.md
# Edit campaign-CRUSTIFY.md and answer as many questions as you want.
```

Open Crustify on the repository:

```bash
crustify /path/to/repo --settings ./campaign-CRUSTIFY.md
```

Crustify opens with its workflow and the campaign's settings loaded, and waits for your
instructions: ask it about the target, have it plan one subsystem, or tell it to run the
campaign. `--start` runs the campaign right away, as the settings configure it; a
headless session needs it. Without `--settings`, Crustify creates the settings from the
template of the campaign you name with `--campaign port | wrap | audit`, or asks which.

The settings are copied to the repository's `crustify/CRUSTIFY.md`, which Crustify
reads and the campaign tracks. Edit that copy to change settings mid-campaign; Crustify
rereads it before each subsystem. Questions left unanswered are asked live: which
repository and revision to use, whether to port or wrap it, where the campaign should
start, which models to use, and how much autonomy Crustify has. It presents a
consolidated campaign brief for approval before it changes the target repository.

Campaign dashboards follow the
[`templates/translate/dashboard.template.md`](templates/translate/dashboard.template.md)
template.

For a reproducible container environment and the campaign templates, see
[`templates/`](templates/README.md).

## Campaign lifecycle

1. **Scope:** choose a target and objective, then define subsystems now or
   brainstorm them with Crustify.
2. **Setup:** establish the build and test baseline, extract CodeQL data,
   configure the campaign-wide oracle target, decompose its targeted and
   imported translation units into `subsystems.json`, and scaffold compiling
   Rust crates.
3. **Plan:** each subsystem of `subsystems.json` is planned on its own, plus the
   synthetic raw `void` and raw `string` lifetime subsystems. Each gets a narrow
   `wavefront-config.json`; Wavefront computes its exact imported-producer
   closure, waves and batches. Wrap campaigns select the public API graph with
   `--api-headers-only`.
4. **Translate and review:** Crustify launches one isolated binder or translator
   per scheduled batch. After all translation batches in a wave land, an
   adversarial review wave runs before any consumer wave starts.
5. **Promote and audit:** Crustify reconciles parallel landings, runs
   regression and deterministic safety gates, then promotes the reviewed wave.

Each role's authoritative procedure is its own prompt:
[`translate-assistant`](src/crustify/prompts/translate-assistant.md),
[`audit-assistant`](src/crustify/prompts/audit-assistant.md),
[`binder`](src/crustify/prompts/binder.md),
[`translator`](src/crustify/prompts/translator.md) and
[`reviewer`](src/crustify/prompts/reviewer.md).

## CLI

This repository installs one command:

```text
crustify           one entry point for every stage:
                     translate         start Crustify on a translation campaign
                     audit             start Crustify on an audit campaign
                     spawn-planner     run one planner over its task.json
                     spawn-binder      run one binder over its task.json
                     spawn-translator  run one translator over its task.json
                     spawn-reviewer    run one reviewer over its task.json
                     cost              price per-agent usage.json records
```

The oracle interface is owned by its own repository. Use `<command> --help` for
current commands, defaults, and flags; the README does not duplicate those
interfaces.

## Results

Crustify generated safe bindings for the whole API of `libgit2` (excluding deprecated
items) using Codex GPT-5.6-Sol and followed by independent Claude Opus 5 review and UB
audit.

Below is an overview of the campaign's stats:

| Measure | Result |
|---|---:|
| C target | `171,084` LoC |
| Rust implementation | `28,432` LoC |
| Rust tests | `42,903` LoC |
| Wrapped public API | `259` types (`99.6`%); `1,014` symbols (`95.8`%) |
| Remaining API | `1` type and `44` symbols, all deprecated |
| Tests | `965` unit; `191` C/Rust equivalence |
| Combined line coverage | `69.71`% C; `92.46`% Rust |
| Recorded cost | `$1,904.64` for translation, review, and orchestration |
| Aggregate agent wall time | `24h49m20s` |

 The full campaign results and code are available [here](https://github.com/crustify-rs/libgit2-wrap).

## Documentation

- [`docs/translate/conventions.md`](docs/translate/conventions.md): generated Rust
  conventions, including the Rust tree layout
- [`docs/translate/schemas/`](docs/translate/schemas/): crate-placement and wave schemas
- [`docs/translate/schemas/subsystems.md`](docs/translate/schemas/subsystems.md): link-unit and
  subsystem decomposition artifact
- [`templates/translate/CRUSTIFY.template.md`](templates/translate/CRUSTIFY.template.md): optional pre-filled
  campaign questionnaire
- [`templates/translate/dashboard.template.md`](templates/translate/dashboard.template.md): campaign
  dashboard template

## Acknowledgements

This material is based upon work supported by the Defense Advanced Research
Projects Agency (DARPA) Translating All C To Rust (TRACTOR) program under
Agreement No. HR00112590134.
