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

[`Dockerfile`](Dockerfile) builds the environment either campaign runs in. It
starts nothing: the container idles, and `crustify` is run inside it, with every
choice (campaign kind, model, billing, ablation) a `crustify` flag.

## Running one

All commands from the repo root.

```sh
docker build -f examples/Dockerfile -t crustify .
```

Start a container per campaign, idle:

```sh
docker run -d --name crustify-libgit2 \
    -e ANTHROPIC_API_KEY \
    -v "$(dirname "$PWD")/wavefront:/opt/venv/share/wavefront" \
    -v "$(dirname "$PWD")/ffibox:/opt/venv/share/ffibox" \
    -v /absolute/path/to/your/target-fork:/target \
    -v "$PWD/examples/crustify/libgit2/src-port/TASK.md:/campaign/TASK.md:ro" \
    crustify
```

Translate:

```sh
docker exec -it crustify-libgit2 \
    crustify --model anthropic/claude-opus-5 --billing api \
    /target orchestrate translate --task /campaign/TASK.md
```

Audit, in a container started the same way with an audit task and a `/work`
volume:

```sh
docker exec -it audit-zstd \
    crustify --model anthropic/claude-opus-5 --billing api \
    /target orchestrate audit --task /campaign/TASK.md
```

Add `--task-only` to either for the ablation control: the task file becomes the
entire prompt. See [`crustify_audit/BARE.md`](crustify_audit/BARE.md).

The deterministic scan needs no agent and no authentication, so it bypasses the
orchestrator entirely and is just another command:

```sh
docker exec crustify-libgit2 crustify /target audit unsafe
```

`/target` must be an existing Git checkout mounted read-write. The orchestrator
uses its checked-out revision and existing `crustify/` state directly, which is
what makes resuming a partial campaign on a personal fork work. It does not
clone or replace the target checkout.

`/opt/venv/share/wavefront` and `/opt/venv/share/ffibox` are optional and used
only by a translate run. The image carries a build-time clone of each; a mount
replaces it, so a campaign runs against the trees being developed. An audit run
touches neither.

The harness is baked into the image, so `/opt/crustify` is a mount only when
testing live harness changes.

The container is started without `--rm`. Restart it with `docker start
crustify-libgit2`; its writable root filesystem preserves tools, caches,
source-built dependencies, and `apt` packages installed after boot. Removing the
container loses those, so generally useful packages belong in the Dockerfile.

## Run-time environment

Set with `-e` on `docker run`: only the credentials the chosen provider and
billing need (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY` or `OPENROUTER_API_KEY`).
Everything else is a `crustify` flag; see `crustify --help`.

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
| `/campaign/TASK.md` | read-only, conventional | both | the campaign task passed to `--task`; any path works |
| `/opt/crustify` | read-write, optional | both | baked into the image; mount a checkout to run live harness sources |
| `/opt/venv/share/wavefront` | read-write, optional | translate | replaces the build-time clone, which is installed editable |
| `/opt/venv/share/ffibox` | read-write, optional | translate | replaces the build-time clone used by generated Cargo manifests |
| `/work` | named volume, optional | both | `HOME`: the C library the agent builds, the cargo registry. Not the artifacts — those land in the target checkout |

## Results

Campaign reports are written into the target checkout, at the path the task
names. Historical aggregate measurements for the libgit2 and OpenSSL campaigns
are preserved in
[`crustify/libgit2-openssl-results.md`](crustify/libgit2-openssl-results.md).

The Dockerfile header documents the rest: what each mount buys and why the base
image is pinned by digest.
