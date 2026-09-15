# crustify-audit

Audit Rust repositories—especially wrappers over C—for unsafe surface area and
undefined behavior reachable from safe code.

| command | kind | result |
|---|---|---|
| `unsafe` | deterministic rustc analysis | unsafe and raw-pointer metrics |
| `ub` | agentic audit | investigated leads and reproducible advisories |

## Quick start

Requires Python 3.13 or newer:

```sh
pip install -e .

crustify /path/to/repo audit unsafe
crustify /path/to/repo audit ub --model anthropic/claude-opus-5
```

Pass the repository root. The audited Cargo workspace is the root when it has a
`Cargo.toml`; otherwise it is `crustify/rust/` for a Crustify campaign.

`unsafe` requires a nightly toolchain with `rustc-dev` and `llvm-tools`, plus a
workspace that compiles. `ub` requires the selected Claude or Codex CLI and the
instrumentation appropriate to each finding. It warns when Miri or
BorrowSanitizer is unavailable.

## Output

Every run uses `<repo>/crustify/audit/`:

```text
unsafe.json        deterministic scan output
advisories/        confirmed bugs and their reproducers
leads/             every investigated candidate, including cleared ones
scratch/           disposable experiments
logs/              agent logs and usage records
```

An advisory requires a reproducer that depends on the audited crate and reaches
the behaviour through its public API. For every instrument but `equivalence`
the reproducer writes no `unsafe` at all and must trigger the instrument. An
`equivalence` reproducer needs `unsafe` to invoke the C reference it compares
against; confine it to that call, reach the Rust side only through the safe
API, and its verdict is the failing comparison rather than an instrument
diagnostic. Anything short of that is a lead — and a `revisit` run exists to
settle leads once an instrument that can decide them is available.

Runs accumulate. Auditors read existing advisories and leads before starting,
so later runs extend the record instead of repeating completed investigations.

## CLI

```text
crustify WORKDIR audit unsafe [--json] [--name NAME ...]
crustify WORKDIR audit ub [--objective audit|audit+patch|patch|revisit]
                       [--workset PATH ...]
                       [--instruments miri|asan/ubsan|bsan|msan|tsan|equivalence ...]
                       [--model PROVIDER/MODEL]
                       [--billing subscription|api]
                       [--timeout MINUTES]
```

- `unsafe --json` prints the document written to `unsafe.json`.
- `unsafe --name` adds source sites for selected C types or symbols.
- `ub --workset` confines an auditor to specified work items. For audit
  objectives these are source files; omit it for the whole crate. Under
  `--objective patch` it carries advisory directories under
  `crustify/audit/advisories/` instead of source files; omit it to repair every
  advisory. Under `--objective revisit` it carries lead notes under
  `crustify/audit/leads/` instead of source files.
- `ub --instruments` constrains the hunt and advisory evidence; omit it to
  select every one. Before spending, the command prints the exact selected
  instruments, their bug classes, and their reach limitations. `equivalence`
  is the odd one out: it decides by comparing against the C reference rather
  than by instrumentation, so it needs no sanitizer build and its advisories
  carry a failing assertion instead of a crash.
- `ub --timeout` is a wall-clock budget, not a kill deadline. The current agent
  finishes even when that overshoots the budget; `0` runs one agent.
- `audit` never edits target source. `audit+patch` and `patch` develop repairs
  in Git worktrees. `revisit` hunts nothing new: it re-investigates leads an
  earlier campaign left open, appends a dated verdict to each, and promotes one
  to an advisory if it now reproduces. Use it after adding an instrument that
  can settle a hypothesis the earlier run had to leave standing.

Run `crustify WORKDIR audit --help` or a subcommand's `--help` for complete flag
semantics.

### Instrument scopes

| selection | bug classes the auditor hunts |
|---|---|
| `miri` | Rust-side bounds and lifetime errors, uninitialized or invalid values, alignment and intrinsic violations, aliasing under Stacked/Tree Borrows, and data races |
| `asan/ubsan` | native bounds errors, use-after-free/return/scope and invalid frees, pointer/alignment UB, integer/division/shift UB, and invalid C/C++ runtime values |
| `bsan` | Tree Borrows aliasing across Rust and foreign code, including conflicting foreign-pointer writes and pointers invalidated by reborrows |
| `msan` | use of uninitialized memory: branches and addresses computed from it, uninitialized bytes crossing the FFI boundary, and struct tails or buffers a foreign initializer left partly unwritten |
| `equivalence` | functional drift from the bound C API: mapped or swallowed errors, differing out-parameters and buffers, state that diverges only across a multi-call sequence, boundary-input handling, option defaults, callback contracts, and lossy conversions. Its verdict is a failing assertion against the C reference, not an instrument, so it needs no sanitizer build and says nothing about UB |
| `tsan` | data races between Rust and foreign threads, unsynchronized access through `&T` where `Send`/`Sync` is hand-written, and use of an object being destroyed on another thread |

These are execution-based scopes, not promises of exhaustive detection. Miri
usually cannot execute foreign code; ASan/UBSan require the relevant native
code and final executable to be instrumented; BorrowSanitizer specifically
checks Rust aliasing rules. The same definitions are injected into each auditor
prompt, so CLI selection, displayed plan, and hunt scope cannot drift.

MemorySanitizer and ThreadSanitizer each need a build of their own and cannot
share a binary with ASan/UBSan, so selecting them costs an extra build per
auditor. MemorySanitizer additionally needs every component instrumented — the
standard library via `-Zbuild-std` and the foreign code it links — because
memory written by uninstrumented code reads as uninitialized; a partial build
reports falsely rather than cleanly. They cover the two classes the other three
cannot reach at all: ASan/UBSan does not model uninitialized memory, and no
other instrument can decide a hand-written `unsafe impl Sync`.

## Container

The container starts an orchestrator that resolves the run plan and launches
auditors against the checkout mounted at `/target`.

```sh
docker build -t crustify -f examples/Dockerfile .

docker run --rm -it --name audit-target \
  -e ANTHROPIC_API_KEY \
  -e CRUSTIFY_BACKEND=claude \
  -e CRUSTIFY_MODEL=claude-opus-5 \
  -v /path/to/target-repo:/target \
  -v /host/campaign/TASK.md:/campaign/TASK.md:ro \
  -e CRUSTIFY_COMMAND=audit \
  -v audit-target-work:/work \
  crustify
```

One image serves the auditor and the translator; they differ in one thing only,
which orchestrator prompt they load, and `CRUSTIFY_COMMAND` selects it. It has
no default. The harness is installed in the image.
During harness development, mount this checkout at `/opt/crustify` to run its
live sources instead.

For Codex against OpenAI, use `CRUSTIFY_BACKEND=codex`, pass the model ID
exactly as Codex expects it, and provide `OPENAI_API_KEY`. To drive an
Anthropic model through OpenRouter instead, add:

```sh
-e OPENROUTER_API_KEY \
-e CRUSTIFY_BACKEND=codex \
-e CRUSTIFY_PROVIDER=openrouter \
-e CRUSTIFY_MODEL=anthropic/claude-sonnet-5
```

OpenRouter must support the Responses API for the selected model. Model IDs are
passed verbatim to both CLIs.

Before running, complete [`examples/crustify_audit/TASK.md.template`](examples/crustify_audit/TASK.md.template) and place it at
the host path mounted as `/campaign/TASK.md` above. Without that mount, the
orchestrator asks for mandatory decisions. A headless run therefore needs a
complete task.

| variable | values | default |
|---|---|---|
| `CRUSTIFY_BACKEND` | `claude`, `codex` | `claude` |
| `CRUSTIFY_PROVIDER` | `anthropic`, `openai`, `openrouter` | derived from backend |
| `CRUSTIFY_MODEL` | backend-specific model ID | `claude-opus-5` |
| `CRUSTIFY_BILLING` | `api`, `subscription` | `api` |
| `CRUSTIFY_HEADLESS` | `0`, `1` | `0` |
| `CRUSTIFY_TIMEOUT` | minutes per auditor; `0` runs one | `60` |
| `CRUSTIFY_EFFORT` | Codex orchestrator and auditor reasoning effort | `high` |
| `CRUSTIFY_COMMAND` | `translate`, `audit` | none; required |

`api` uses `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `OPENROUTER_API_KEY` for
the selected provider. OpenRouter requires `api`; `subscription` uses Claude or
Codex credentials saved under `/work`, which is also the persistent Cargo/build
cache. An `openrouter/anthropic/<model>` route uses Claude Code with
`OPENROUTER_API_KEY`; other OpenRouter model IDs use Codex. The deterministic
scan needs no agent and no authentication, so it is
just another command: `docker run ... crustify crustify /target audit unsafe`.

`CRUSTIFY_BARE=1` still makes the mounted `TASK.md` the entire prompt, for
either command.

## Reference

- [Deterministic output and named-site semantics](docs/unsafe-output.md)
- [Task questionnaire](examples/crustify_audit/TASK.md.template)
- [Example results and report format](examples/crustify_audit/results.md)
- [`ub` auditor prompt](src/crustify_audit/prompts/ub.md)
- [Orchestrator prompt](src/crustify_audit/prompts/orchestrator.md)
