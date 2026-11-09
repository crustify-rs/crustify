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

Crustify runs on 64-bit Linux and translates targets built there, against glibc. It requires
Python 3.13 and a Claude Code or Codex CLI. Clone the components side
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

Crustify can also run in a Docker container. [`templates/docker/Dockerfile`](templates/docker/Dockerfile)
builds an image with everything a campaign needs: both agent CLIs, CodeQL, bindgen, Miri,
and the sanitizer toolchains, including BorrowSanitizer and MemorySanitizer.

```bash
docker build -t crustify -f templates/docker/Dockerfile .
```

Start one container per campaign, with the directory the campaign is to work in mounted
at `/target` — empty for a new campaign, or holding one to resume — then open Crustify
inside it:

```bash
docker run -d --init --name crustify-libgit2 \
    --security-opt seccomp=unconfined \
    -e ANTHROPIC_API_KEY \
    -v /absolute/path/to/campaign-dir:/target \
    -v crustify-libgit2-work:/work \
    crustify

docker exec -it crustify-libgit2 crustify /target --backend claude --billing api
```

[`templates/docker/README.md`](templates/docker/README.md) documents the mounts, build arguments and
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
| `--backend claude\|codex` | Run the assistant on Claude Code (the default) or Codex. |
| `--billing subscription\|api` | Use the CLI's logged-in account or an API key from the environment. |
| `--model-proxy openrouter` | Send the CLI's requests through OpenRouter, with `OPENROUTER_API_KEY`. Needs `--billing api`. |
| `-- <args>` | Pass the rest to the CLI unchanged, e.g. `-- --model opus --effort high`. Without a model there, the CLI runs its default. |

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
billing, directly or through OpenRouter. Each agentic stage can use its own backend, and
its own model and settings through the CLI's own arguments; without them, each CLI runs
its default model.

## Results

Crustify is wrapping the public API of FFmpeg, starting with `libavutil`, excluding
deprecated items. Claude Opus 5.5 wrote most of the bindings and reviewed them
independently for undefined behavior; Claude Fable 5.1 ran some of the reviews, and
GPT-6.1-Sol some of the wrapping.

| Measure | Result |
|---|---:|
| C target | `29,909` LoC (`libavutil`), of `80,180` LoC in scope |
| Rust implementation | `18,375` LoC |
| Rust tests | `91,162` LoC |
| Wrapped public API | `82` types (`51.6`%); `516` symbols (`77.0`%) of `libavutil` |
| Remaining API | `77` types and `154` symbols in `libavutil`; `765` items over all 7 libraries |
| Tests | `964` unit; `718` C/Rust equivalence; `997` UB |
| Combined line coverage | `75.12`% C; `99.68`% Rust |
| Recorded cost | `$2,066.47` for translation, review, planning, and orchestration |
| Aggregate agent wall time | `100h27m` |

The campaign results and code are available at
[crustify-rs/ffmpeg-bindings](https://github.com/crustify-rs/ffmpeg-bindings).

## Skills and agents

Crustify's specifications are skills, under [`skills/`](skills/), one per part of a port,
wrap or audit campaign: from the campaign's layout and the decomposition of the codebase,
through its scheduling, to the safety and soundness of the bindings and ports it
generates. They describe the work rather than who does it, and each agent reads the ones it
follows before the step they serve.

- [`skills/workflows/`](skills/workflows/): how each kind of campaign proceeds: its shared
  setup, and the binding, porting and audit workflows
- [`skills/planning/`](skills/planning/): how the codebase is decomposed into modules, one
  per translation unit, with their objectives and dependencies; how the modules are
  ordered and scheduled into waves and batches; and how the libraries the target uses
  from outside its tree are wrapped, and their wrappers reused across campaigns
- [`skills/rust/`](skills/rust/): the generated Rust: its conventions and tree layout, the
  toolchains, edition, lints and formatting it is held to, the raw bindings, and how an
  item is wrapped or ported
- [`skills/verification/`](skills/verification/): how the work is tested, and how landed
  work and plans are reviewed
- [`skills/operations/`](skills/operations/): a campaign's repositories, branches and
  worktrees, and how batches land and work is promoted and shipped; the repository's tree
  and artifact directories; how its work shares the host; and the dashboard, the session
  records and rates, and how cost is derived
- [`skills/artifacts/`](skills/artifacts/): the fields of `modules.json`,
  `dependencies.json`, the campaign's `schedule.json`, and `task.json`
- [`skills/tools/`](skills/tools/): how wavefront, ffimap and ffibox serve each stage
- [`skills/crustify/`](skills/crustify/): how Crustify itself is organized
- [`templates/`](templates/README.md): an example of each artifact, the settings and
  dashboard templates, and the Dockerfile

Each agent's authoritative procedure is its file under [`agents/`](agents/): the
assistant, and the planner, binder, translator and reviewer stages.

### Claude Code

Crustify's checkout is a Claude Code plugin, through its provider under
[`providers/claude/`](providers/claude/): the skills, one agent per stage, and the
assistant as an agent per campaign kind. To try it from a checkout, in a campaign's
repository:

```bash
claude --plugin-dir <crustify checkout> --agent crustify:assistant-translate
```
