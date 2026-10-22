# Crustify

**Crustify is your AI-based co-translator and assistant for automating C-to-Rust tasks.**
Point it at a C repository or a Rust crate and Crustify helps you define the end objective,
plans the work for you, runs it, and reports back. It handles three kinds of tasks:

- **Wrap public APIs.** Keep the C implementation and generate a safe, idiomatic Rust API
  in front of it.
- **Audit a crate.** Hunt for undefined behavior and memory-safety bugs in any Rust crate
  that wraps C, and file a report and a reproducer for each finding.
- **Port a codebase.** Reimplement C code in safe Rust, one module at a time or all
  of it.

Crustify works at the level of a whole repository. It splits the codebase into
modules, one per C translation unit, orders them by their dependencies, and hands each
batch of work to a focused sub-agent in its own Git worktree. Sub-agents run in parallel,
and each one sees only its own worklist. Crustify keeps the campaign's state, lands their work behind build, test
and safety gates, and repairs what fails.

You choose how much control to keep. Crustify can run a campaign fully autonomously, or
you can stay in the loop: ask it about the target, have it plan one module and stop,
approve the campaign brief before it touches the repository, and take decisions as they
come up. You can change course mid-campaign by editing its settings file.

## Installation

Crustify requires Python 3.13 and a Claude Code or Codex CLI. Clone the components side
by side and install the Python packages. `ffibox` is a Rust crate that the generated
wrappers depend on, so you only clone it.

```bash
git clone https://github.com/crustify-rs/crustify.git
git clone https://github.com/crustify-rs/wavefront.git
git clone https://github.com/crustify-rs/ffibox.git
git clone https://github.com/crustify-rs/ffimap.git

python -m pip install -e crustify -e wavefront -e ffimap
```

### Docker

Crustify can also run in a Docker container. [`templates/Dockerfile`](templates/Dockerfile)
builds an image with everything a campaign needs: both agent CLIs, CodeQL, bindgen, Miri,
and the sanitizer toolchains, including BorrowSanitizer and MemorySanitizer.

```bash
docker build -t crustify -f templates/Dockerfile .
```

Start one container per campaign, with the target checkout mounted at `/target`, then
open Crustify inside it:

```bash
docker run -d --init --name crustify-libgit2 \
    --security-opt seccomp=unconfined \
    -e ANTHROPIC_API_KEY \
    -v /absolute/path/to/target:/target \
    -v crustify-libgit2-work:/work \
    crustify

docker exec -it crustify-libgit2 crustify /target --model anthropic/claude-opus-5 --billing api
```

[`templates/README.md`](templates/README.md) documents the mounts, build arguments and
environment variables.

## Usage

Open Crustify on a repository:

```bash
crustify /path/to/repo
```

Crustify loads its workflow and waits for your instructions. Tell it what you want in
plain language: wrap the public API, audit the crate, port the parser. Questions it
needs answered, such as the revision to start from, the models to use and how much
autonomy it has, are asked live, and Crustify presents a campaign brief for your
approval before it changes the repository.

To answer those questions up front, copy and fill in a settings template:

```bash
cp crustify/templates/translate/CRUSTIFY.template.md my-campaign.md   # port or wrap
cp crustify/templates/audit/CRUSTIFY.template.md my-campaign.md       # audit
crustify /path/to/repo --settings my-campaign.md
```

Crustify copies the settings to `crustify/CRUSTIFY.md` in the repository and rereads
that copy before each module, so you can edit it while a campaign runs.

Common options:

| Option | Effect |
|---|---|
| `--campaign port\|wrap\|audit` | Pick the campaign when the settings don't name one. |
| `--start` | Run the campaign right away, as the settings configure it. A headless session needs it. |
| `--resume [SESSION_ID]` | Continue an earlier session, from any directory. Without an id, the most recent one. |
| `--model PROVIDER/MODEL` | Pick the assistant's model, e.g. `anthropic/claude-opus-5` or `openrouter/openai/gpt-5.6-sol`. |
| `--billing subscription\|api` | Use the CLI's logged-in account or an API key from the environment. |

`crustify usage <transcripts>` reports the tokens and cost of agent sessions. Crustify
runs the `spawn-planner`, `spawn-binder`, `spawn-translator` and `spawn-reviewer`
commands itself; you rarely need them. Run `crustify --help` or
`crustify <command> --help` for the full reference.

## How it works

Crustify talks to you and launches four kinds of sub-agent:

| Agent | Role |
|---|---|
| **Crustify**, the assistant | Talks to you, configures the campaign, prepares builds and baselines, launches the other agents, lands and promotes their work, and keeps the dashboard. |
| planner | Decomposes the codebase into modules, one per translation unit, and schedules their waves and batches. |
| binder | Wraps a batch: keeps its C implementation and puts a safe Rust API in front of it. |
| translator | Ports a batch to safe Rust. |
| reviewer | Reviews the work a wave landed for unsafety, undefined behavior and equivalence with the C, files a report and reproducer per finding, and fixes them. |

Reviewers are independent of the agents whose work they review, and they test
adversarially. An audit runs the reviewers alone over an existing crate.

Deterministic tools ground the agents' judgement:

- [wavefront](https://github.com/crustify-rs/wavefront) sorts the C codebase into
  dependency-ordered waves from CodeQL facts;
- [ffibox](https://github.com/crustify-rs/ffibox) provides the smart pointers and
  lifetime traits the generated Rust builds on;
- [ffimap](https://github.com/crustify-rs/ffimap) measures the resulting unsafe and FFI
  surface per batch, wave, module and campaign; and
- the target's own tests run under sanitizers.

Claude Code and OpenAI Codex are supported as agent backends, with API or subscription
billing, directly or through OpenRouter. Each agentic stage can use its own model. We
recommend `claude-opus-5` for the assistant and reviewers and `gpt-5.6-sol` for
translators.

## Results

Crustify generated safe bindings for the whole public API of `libgit2`, excluding
deprecated items. Codex GPT-5.6-Sol wrote the bindings, and Claude Opus 5 reviewed them
independently and audited them for undefined behavior.

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

The full campaign results and code are available at
[crustify-rs/libgit2-wrap](https://github.com/crustify-rs/libgit2-wrap).

## Specifications

Crustify comes with a set of specifications, under [`specs/`](specs/), for how each step
of a port, wrap or audit campaign is done: from the campaign's layout and the
decomposition of the codebase, through its scheduling, to the safety and soundness of the
bindings and ports it generates. They describe the work rather than who does it, and
every agent's prompt includes the ones it follows.

- [`specs/decomposition.md`](specs/decomposition.md): how the codebase is decomposed into
  modules, one per translation unit, with their objectives and dependencies
- [`specs/scheduling.md`](specs/scheduling.md): how the modules are ordered and scheduled
  into waves and batches
- [`specs/items/binding.md`](specs/items/binding.md),
  [`specs/items/porting.md`](specs/items/porting.md): the per-item principles, how an item
  is wrapped or ported
- [`specs/reviewing.md`](specs/reviewing.md): how landed work and plans are reviewed
- [`specs/workflows/`](specs/workflows/): how each kind of campaign proceeds: its shared
  setup, and the binding, porting and audit workflows
- [`specs/accounting.md`](specs/accounting.md): the dashboard, session and usage records,
  and how cost is derived
- [`specs/testing.md`](specs/testing.md), [`specs/landing.md`](specs/landing.md),
  [`specs/layout.md`](specs/layout.md): tests, landing, and a campaign's branches and
  artifact directories
- [`specs/conventions.md`](specs/conventions.md): conventions for the generated Rust,
  including the tree layout
- [`specs/artifacts/`](specs/artifacts/): the fields of `modules.json`, the campaign's
  `schedule.json`, and `task.json`
- [`specs/prompting.md`](specs/prompting.md): how the agents' prompts, specs and skills
  are composed
- [`templates/`](templates/README.md): an example of each artifact, the settings and
  dashboard templates, and the Dockerfile

Each agent's authoritative procedure is its prompt, under
[`src/crustify/prompts/`](src/crustify/prompts/).

## Maintainers

- Marius Momeu ([marius.momeu@berkeley.edu](mailto:marius.momeu@berkeley.edu))

## Acknowledgements

This material is based upon work supported by the Defense Advanced Research
Projects Agency (DARPA) Translating All C To Rust (TRACTOR) program under
Agreement No. HR00112590134.
