# Templates

Two kinds of campaign, one image, one directory of templates each.

| directory | campaign | task template | dashboard template |
|---|---|---|---|
| [`translate/`](translate) | translate C to Rust, or wrap it | [`CRUSTIFY.template.md`](translate/CRUSTIFY.template.md) | [`dashboard.template.md`](translate/dashboard.template.md) |
| [`audit/`](audit) | hunt UB in an existing Rust crate with reviewers | [`CRUSTIFY.template.md`](audit/CRUSTIFY.template.md) | [`dashboard.template.md`](audit/dashboard.template.md) |

Copy a task template to start a request.

[`gitignore`](gitignore) seeds a campaign's `crustify/.gitignore`. The files beside it
are examples of the campaign's artifacts, whose fields are described under
[`specs/artifacts/`](../specs/artifacts): [`build.json`](build.json),
[`modules.json`](modules.json), [`dependencies.json`](dependencies.json), the out-of-tree
libraries the target uses, and [`schedule.json`](schedule.json), the campaign's waves and
batches.

[`Dockerfile`](Dockerfile) builds the environment either campaign runs in. It
starts nothing: the container idles, and `crustify` is run inside it: the command
picks the campaign kind, and its options pick the model, billing and ablation.

## Running one

All commands from the repo root.

```sh
docker build -f templates/Dockerfile -t crustify .
```

The image clones wavefront, ffibox and ffimap from GitHub. To build with a local checkout
of one instead, such as a private or unpushed one, pass it as a build context named after
the tool:

```sh
docker build -f templates/Dockerfile -t crustify --build-context ffimap=../ffimap .
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
    -v /absolute/path/to/your/CRUSTIFY.md:/campaign/CRUSTIFY.md:ro \
    -v crustify-libgit2-work:/work \
    crustify
```

Open Crustify on the target:

```sh
docker exec -it crustify-libgit2 \
    crustify /target --settings /campaign/CRUSTIFY.md \
    --model anthropic/claude-opus-5 --billing api
```

The settings' `campaign` answer, `port`, `wrap` or `audit`, decides which campaign
Crustify runs; an audit runs in a container started the same way, with its own `/work`
volume. Crustify waits for your instructions; add `--start` to run the campaign right
away, which a session without a terminal (`docker exec` without `-it`) needs.

The first run copies the settings to the target's `crustify/CRUSTIFY.md`, which is tracked
on the working branch, `crustify/devel`. Edit that copy to change a campaign's settings
while it runs, such as its models or batch sizes: Crustify rereads it before each
module, or each review wave of an audit, and commits it whenever it applies a change, so
the branch's history records the settings each one ran under. `main` is the
shipping branch, which Crustify advances to `crustify/devel` only with your approval. To resume, omit `--settings`, or pass the same
file; a file that differs from the copy is refused, so a resume never overwrites your
edits.

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
| `/campaign/CRUSTIFY.md` | read-only, conventional | both | the campaign settings passed with `--settings` on the first run, which copies them to `/target/crustify/CRUSTIFY.md`; any path works |
| `/opt/crustify` | read-write, optional | both | baked into the image; mount a checkout to run live harness sources |
| `/opt/venv/share/wavefront` | read-write, optional | translate | replaces the build-time clone, which is installed editable |
| `/opt/venv/share/ffibox` | read-write, optional | translate | replaces the build-time clone used by generated Cargo manifests |
| `/opt/venv/share/ffimap` | read-write, optional | both | replaces the build-time clone, which is installed editable as the `ffimap` command |
| `/work` | named volume, optional | both | `HOME`: the agents' session transcripts, the C libraries they build, the cargo registry. Outlives `docker rm`, so a re-created container keeps them. Not the artifacts — those land in the target checkout |

## Dashboards

Campaign dashboards are written into the target checkout, at
`crustify/artifacts/dashboard.md` (`audit-dashboard.md` for an audit) unless the
settings name another path, filled from [`dashboard.template.md`](translate/dashboard.template.md).

The Dockerfile header documents the rest: what each mount buys and why the base
image is pinned by digest.
