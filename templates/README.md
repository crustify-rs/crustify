# Templates

Two kinds of campaign, one image, one directory of templates each.

| directory | campaign | task template | dashboard template |
|---|---|---|---|
| [`translate/`](translate) | translate C to Rust, or wrap it | [`TASK.template.md`](translate/TASK.template.md) | [`dashboard.template.md`](translate/dashboard.template.md) |
| [`audit/`](audit) | hunt UB in an existing Rust crate with reviewers | [`TASK.template.md`](audit/TASK.template.md) | [`dashboard.template.md`](audit/dashboard.template.md) |

Copy a task template to start a request.

The files beside them seed a translate campaign's `crustify/` dir, which the
orchestrator creates from them: [`gitignore`](gitignore),
[`build.json`](build.json), [`subsystems.json`](subsystems.json) and
[`schedule.json`](schedule.json). Derived artifacts such as `subsystems.json`
are emitted against the live wavefront inventory, not committed by hand.

[`Dockerfile`](Dockerfile) builds the environment either campaign runs in. It
starts nothing: the container idles, and `crustify` is run inside it: the command
picks the campaign kind, and its options pick the model, billing and ablation.

## Running one

All commands from the repo root.

```sh
docker build -f templates/Dockerfile -t crustify .
```

Start a container per campaign, idle:

```sh
docker run -d --init --name crustify-libgit2 \
    --security-opt seccomp=unconfined \
    -e ANTHROPIC_API_KEY \
    -v "$(dirname "$PWD")/wavefront:/opt/venv/share/wavefront" \
    -v "$(dirname "$PWD")/ffibox:/opt/venv/share/ffibox" \
    -v "$(dirname "$PWD")/ffimap:/opt/venv/share/ffimap" \
    -v /absolute/path/to/your/target-fork:/target \
    -v /absolute/path/to/your/TASK.md:/campaign/TASK.md:ro \
    -v crustify-libgit2-work:/work \
    crustify
```

Translate:

```sh
docker exec -it crustify-libgit2 \
    crustify translate /target /campaign/TASK.md \
    --model anthropic/claude-opus-5 --billing api
```

Audit, in a container started the same way with an audit task and its own `/work`
volume:

```sh
docker exec -it audit-zstd \
    crustify audit /target /campaign/TASK.md \
    --model anthropic/claude-opus-5 --billing api
```

The first run copies the task to the target's `crustify/TASK.md`, which is tracked on the
campaign branch. Edit that copy to change a campaign's settings while it runs, such as its
models or batch sizes: the orchestrator rereads it before each subsystem, or each review
wave of an audit, and keeps a copy of the settings each one ran under in its artifact dir.
To resume, omit the task, or pass the same one; a task that differs from the copy is
refused, so a resume never overwrites your edits.

Add `--task-only` to either for the ablation control: the task file becomes the
entire prompt. See [`audit/BARE.md`](audit/BARE.md).

`--init` runs a small init process as the container's first process, so the
processes the agents leave behind are reaped instead of piling up as zombies
under `sleep infinity`.

`--security-opt seccomp=unconfined` is what lets the TSan and BSan builds run.
Both runtimes call `personality(ADDR_NO_RANDOMIZE)` at startup, which Docker's
default seccomp profile rejects, so every instrumented binary would die before
`main`. The alternative is lowering the host's `vm.mmap_rnd_bits` to 28, which
needs root on the host.

`/target` must be an existing Git checkout mounted read-write. The orchestrator
uses its checked-out revision and existing `crustify/` state directly, which is
what makes resuming a partial campaign on a personal fork work. It does not
clone or replace the target checkout.

`/opt/venv/share/wavefront`, `/opt/venv/share/ffibox` and `/opt/venv/share/ffimap`
are optional. The image carries a build-time clone of each; a mount replaces it,
so a campaign runs against the trees being developed. ffimap is installed
editable, so the `ffimap` command on `PATH` runs the mounted tree. An audit run
uses only ffimap.

The harness is baked into the image, so `/opt/crustify` is a mount only when
testing live harness changes.

The container is started without `--rm`. Restart it with `docker start
crustify-libgit2`; its writable root filesystem preserves tools, caches,
source-built dependencies, and `apt` packages installed after boot. Removing the
container loses those, so generally useful packages belong in the Dockerfile.

## Run-time environment

Set with `-e` on `docker run`: only the credentials the chosen provider and
billing need (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY` or `OPENROUTER_API_KEY`).
Everything else is an option of the `crustify` command; see `crustify <command> --help`.

## Build environment

Set with `--build-arg` on `docker build`.

| arg | default | effect |
|---|---|---|
| `CODEQL_VERSION` | `v2.26.3` | CodeQL CLI release; installed on x86-64 only, since GitHub publishes no native ARM64 bundle |
| `PYTHON_VERSION` | `3.13` | interpreter for `/opt/venv` |
| `INSTALL_CLAUDE` | `1` | install the claude backend |
| `INSTALL_CODEX` | `1` | install the codex backend |
| `CLI_REFRESH` | `0` | bump to refetch the claude and codex CLIs |
| `DEPS_REFRESH` | `0` | bump to re-clone wavefront and ffibox `main` |

## Mounts

| path | mode | used by | lifetime |
|---|---|---|---|
| `/target` | read-write, required | both | existing target checkout; its partial campaign, CodeQL data, branches and logs stay on the host |
| `/campaign/TASK.md` | read-only, conventional | both | the campaign task passed to the orchestrate command on the first run, which copies it to `/target/crustify/TASK.md`; any path works |
| `/opt/crustify` | read-write, optional | both | baked into the image; mount a checkout to run live harness sources |
| `/opt/venv/share/wavefront` | read-write, optional | translate | replaces the build-time clone, which is installed editable |
| `/opt/venv/share/ffibox` | read-write, optional | translate | replaces the build-time clone used by generated Cargo manifests |
| `/opt/venv/share/ffimap` | read-write, optional | both | replaces the build-time clone, which is installed editable as the `ffimap` command |
| `/work` | named volume, optional | both | `HOME`: the agents' session transcripts, the C libraries they build, the cargo registry. Outlives `docker rm`, so a re-created container keeps them. Not the artifacts — those land in the target checkout |

## Dashboards

Campaign dashboards are written into the target checkout, at the path the task
names, filled from [`dashboard.template.md`](translate/dashboard.template.md).

The Dockerfile header documents the rest: what each mount buys and why the base
image is pinned by digest.
