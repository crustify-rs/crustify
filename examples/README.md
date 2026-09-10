# Examples

Two kinds of campaign, one image, one directory each.

| directory | campaign | task template | report template |
|---|---|---|---|
| [`crustify/`](crustify) | translate C to Rust, or wrap it | [`TASK-template.md`](crustify/TASK-template.md) | [`results-template.md`](crustify/results-template.md) |
| [`crustify_audit/`](crustify_audit) | hunt UB in an existing Rust crate | [`TASK.md.template`](crustify_audit/TASK.md.template) | [`results.md`](crustify_audit/results.md) |

Below each are one subdirectory per campaign, holding the `TASK.md` a run was
given plus whatever inputs were authored ahead of time. Derived artifacts such
as `subsystems.json` are emitted against the live wavefront inventory, not
committed by hand. Copy a task template to start a request; the campaign
directories hold filled instances.

[`Dockerfile`](Dockerfile) bootstraps the orchestrator for either. The two
campaigns differ in one thing only — which orchestrator prompt they load — and
`CRUSTIFY_COMMAND` selects it. It has no default, because a wrong guess starts
the wrong agent and spends a budget before anyone reads the transcript.

## Running one

All commands from the repo root.

```sh
docker build -f examples/Dockerfile -t crustify .
```

Translate:

```sh
docker run -it --name crustify-libgit2 \
    -e CRUSTIFY_COMMAND=translate \
    -e ANTHROPIC_API_KEY -e CRUSTIFY_BACKEND=claude \
    -v "$(dirname "$PWD")/wavefront:/opt/wavefront" \
    -v "$(dirname "$PWD")/ffibox:/opt/ffibox" \
    -v /absolute/path/to/your/target-fork:/target \
    -v "$PWD/examples/crustify/libgit2/src-port/TASK.md:/campaign/TASK.md:ro" \
    crustify
```

Audit:

```sh
docker run --rm -it --name audit-zstd \
    -e CRUSTIFY_COMMAND=audit \
    -e ANTHROPIC_API_KEY -e CRUSTIFY_BACKEND=claude \
    -e CRUSTIFY_MODEL=claude-opus-5 \
    -v /path/to/target-repo:/target \
    -v "$PWD/examples/crustify_audit/TASK.md.template:/campaign/TASK.md:ro" \
    -v audit-zstd-work:/work \
    crustify
```

The deterministic scan needs no agent and no authentication, so it bypasses the
orchestrator entirely and is just another command:

```sh
docker run --rm -v /path/to/target-repo:/target crustify crustify-audit /target unsafe
```

`/target` must be an existing Git checkout mounted read-write. The orchestrator
uses its checked-out revision and existing `crustify/` state directly, which is
what makes resuming a partial campaign on a personal fork work. It does not
clone or replace the target checkout.

`/opt/wavefront` and `/opt/ffibox` are optional and used only by a translate
run. A mount always wins, so a campaign runs against the trees being developed;
when one is absent the entrypoint clones `main` into it and says so on stderr.
An audit run touches neither.

The harness is baked into the image, so `/opt/crustify` is a mount only when
testing live harness changes.

The translate example deliberately omits `--rm`. Restart its stopped container
with `docker start -ai crustify-libgit2`; its writable root filesystem preserves
tools, caches, source-built dependencies, and `apt` packages installed after
boot. Removing the container loses those, so generally useful packages belong in
the Dockerfile. An audit run keeps the equivalent state on the `/work` volume
instead, which is why it can use `--rm`.

## Run-time environment

Set with `-e` on `docker run`.

| var | values | default | effect |
|---|---|---|---|
| `CRUSTIFY_COMMAND` | `translate`, `audit` | none, required | selects the orchestrator prompt; anything else → exit 2 |
| `ANTHROPIC_API_KEY` | key | — | required for `CRUSTIFY_BACKEND=claude` on the `anthropic` provider |
| `OPENAI_API_KEY` | key | — | required for `CRUSTIFY_BACKEND=codex` on `openai` |
| `OPENROUTER_API_KEY` | key | — | required for either backend on `openrouter` |
| `CRUSTIFY_BACKEND` | `claude`, `codex` | `claude` | orchestrator only; the agents it spawns come from `crustify --model` per wave, or the orchestrator's own `--model` per auditor |
| `CRUSTIFY_PROVIDER` | `anthropic`, `openai`, `openrouter` | derived from backend | `openrouter` routes claude through `ANTHROPIC_BASE_URL` and requires `CRUSTIFY_BILLING=api` |
| `CRUSTIFY_MODEL` | backend-specific model ID | `claude-opus-5` | orchestrator only; empty → exit 2 |
| `CRUSTIFY_BILLING` | `api`, `subscription` | `api` | `api` adds `--bare` (claude) or an env-key provider block (codex) — neither CLI uses a key in the environment without it; key missing → exit 2 |
| `CRUSTIFY_HEADLESS` | `0`, `1` | `0` | `1` answers no approval gate — use only where `TASK.md` pre-answers them |
| `CRUSTIFY_EFFORT` | `low`, `medium`, `high`, `xhigh`, `max`, `ultra`, empty | `high` | codex orchestrator only, ignored by claude; empty leaves codex its default; anything else → exit 2 |
| `CRUSTIFY_TIMEOUT` | minutes per auditor | `60` | audit only; a wall budget, not a kill switch |
| `CRUSTIFY_BARE` | `0`, `1` | `0` | ablation control: `1` makes the mounted `TASK.md` the entire prompt, for either command. See [`crustify_audit/BARE.md`](crustify_audit/BARE.md) |

## Build environment

Set with `--build-arg` on `docker build`.

| arg | default | effect |
|---|---|---|
| `CODEQL_VERSION` | `v2.26.3` | CodeQL CLI release; installed on x86-64 only, since GitHub publishes no native ARM64 bundle |
| `PYTHON_VERSION` | `3.13` | interpreter for `/opt/venv` |
| `INSTALL_CLAUDE` | `1` | install the claude backend |
| `INSTALL_CODEX` | `1` | install the codex backend |

## Mounts

| path | mode | used by | lifetime |
|---|---|---|---|
| `/target` | read-write, required | both | existing target checkout; its partial campaign, CodeQL data, branches and logs stay on the host |
| `/campaign/TASK.md` | read-only, optional | both | pre-filled task; without it the orchestrator asks for unresolved details interactively |
| `/opt/crustify` | read-write, optional | both | baked into the image; mount a checkout to run live harness sources |
| `/opt/wavefront` | read-write, optional | translate | mounted checkout wins; otherwise cloned from GitHub, then installed editable |
| `/opt/ffibox` | read-write, optional | translate | mounted checkout wins; otherwise cloned from GitHub and used by generated Cargo manifests |
| `/work` | named volume, optional | audit | `HOME`: the C library the agent builds, the cargo registry. Not the artifacts — those land in the target checkout |

## Results

Campaign reports are written into the target checkout, at the path the task
names. Historical aggregate measurements for the libgit2 and OpenSSL campaigns
are preserved in
[`crustify/libgit2-openssl-results.md`](crustify/libgit2-openssl-results.md).

The Dockerfile header documents the rest: what each mount buys, why the base
image is pinned by digest, and why the sanitizer self-tests fail the build
rather than warn.
