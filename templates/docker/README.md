# Docker

[`Dockerfile`](Dockerfile) builds the environment a port runs in. It starts
nothing: the container idles, and Crustify is opened inside it.

## Running one

All commands from the repo root.

```sh
docker build -f templates/docker/Dockerfile -t crustify .
```

The image carries four checkouts — crustify, wavefront, ffibox and ffimap — and one flag
chooses where any of them comes from. Each is a build stage named after the tool, and
`--build-context <tool>=<path>` replaces the stage of that name with a local checkout,
so its default is never run:

```sh
docker build -f templates/docker/Dockerfile -t crustify \
    --build-context ffimap=../ffimap \
    --build-context wavefront=../wavefront .
```

That covers a private or unpushed tool, and it is the same flag for all four. Only the
defaults differ:

| tool | default source |
|---|---|
| `wavefront`, `ffibox`, `ffimap` | a shallow clone of the `devel` branch, from the `crustify-rs` organization |
| `crustify` | the build context, the checkout this Dockerfile ships in |

crustify defaults to the context because the build is run from a crustify checkout, so
the local tree is what one means by default.

There is no flag for a branch. A build takes either a local checkout or `devel`, and a
checkout is already on whatever branch you put it on: to build against one, check it out
locally, switch to it, and pass the tree.

A `RUN git clone` is cached by its instruction text, which never changes, so bump
`DEPS_REFRESH` to re-clone the tools' branches.

Start a container per port, idle:

```sh
docker run -d --init --name crustify-libgit2 \
    --security-opt seccomp=unconfined \
    -e ANTHROPIC_API_KEY \
    -v /absolute/path/to/the/c-checkout:/target \
    -v "$(dirname "$PWD"):/crustify-rs" \
    -v crustify-libgit2-work:/work \
    crustify
```

Open Crustify in it, in the checkout of the C codebase:

```sh
docker exec -it -w /target crustify-libgit2 \
    claude --plugin-dir /opt/crustify --agent crustify:crustify
```

Its first message names the task: the components to port, the build configuration and
anything else the port must respect. Pass it with `-p` to run the port headless, which a
session without a terminal (`docker exec` without `-it`) needs. `claude --resume`
continues an earlier session; `crustify/STATUS.md` says where the port stands.

`--init` runs a small init process as the container's first process, so the
processes the agents leave behind are reaped instead of piling up as zombies
under `sleep infinity`.

`--security-opt seccomp=unconfined` is what lets the TSan and BSan builds run.
Both runtimes call `personality(ADDR_NO_RANDOMIZE)` at startup, which Docker's
default seccomp profile rejects, so every instrumented binary would die before
`main`. The alternative is lowering the host's `vm.mmap_rnd_bits` to 28, which
needs root on the host.

`/target` is the checkout of the C codebase, mounted read-write. The Rust tree and the
port's own files under `crustify/`, as the [`layout`](../../skills/operations/layout/SKILL.md)
skill lays them out, land in it. When it already holds a port, that port is resumed in
place.

`/crustify-rs` is optional, and is the whole workspace rather than one tool:
wavefront, ffibox and ffimap as siblings of the crustify checkout, beside the
target forks and the reference crates, exactly as they sit on the host. That is
where the three tool checkouts live in the image, so one mount replaces all
three at once, and the agents read the same trees you edit instead of three
paths unrelated to each other or to anything on your machine. The image carries
a build-time clone of each, so leaving the mount off is fine; a workspace
mounted here must carry a directory per tool and a crustify checkout, since each is
reached through a path inside it that otherwise dangles — Crustify included.

`/target` stays its own mount even when the target fork lives in the workspace:
Crustify works in `/target`, and a target that is also under `/crustify-rs` is
simply visible at both paths, the same tree through two mounts. Keeping them
separate is what lets a target sit elsewhere entirely — on a volume with room
for its builds and CodeQL data, say — while the toolchains stay in the
workspace.

`wavefront` and `ffimap` are installed editable from their workspace paths, so the
commands on `PATH` run the mounted code. A port's manifest names ffibox by its canonical
checkout, `/crustify-rs/ffibox`, never through a symlink, whose path compile-fail snapshots
would not normalize; `/opt/venv/share/<tool>` stays a symlink into the workspace. An editable install is a path
entry, not a copy, so a mount redirects it with no re-install. Re-run
`uv pip install -e /crustify-rs/<tool>` only when the mounted tree adds a console script,
adds a dependency, or moves its package out of `src/`.

Crustify itself is in the workspace with the other three, at `/crustify-rs/crustify`, and
`/opt/crustify`, the plugin directory Crustify is opened with, is a symlink to it. So
a mounted workspace supplies all four, and the plugin is the same tree you edit.
Bind-mounting over `/opt/crustify` replaces only the symlink; override Crustify with the
workspace mount, or at build time with `--build-context crustify=<path>`.

The container is started without `--rm`. Restart it with `docker start
crustify-libgit2`; its writable root filesystem preserves tools, caches,
source-built dependencies, and `apt` packages installed after boot. Removing the
container loses those, so generally useful packages belong in the Dockerfile.

## Run-time environment

Set with `-e` on `docker run`: only the credentials the chosen backends and billing
need (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY` or `OPENROUTER_API_KEY`). Every other choice
is the task message's.

## Build environment

Set with `--build-arg` on `docker build`.

| arg | default | effect |
|---|---|---|
| `CODEQL_VERSION` | `v2.26.3` | CodeQL CLI release; installed on x86-64 only, since GitHub publishes no native ARM64 bundle |
| `PYTHON_VERSION` | `3.13` | interpreter for `/opt/venv` |
| `INSTALL_CLAUDE` | `1` | install the claude backend |
| `INSTALL_CODEX` | `1` | install the codex backend |
| `CLI_REFRESH` | `0` | bump to refetch the claude and codex CLIs; claude also updates itself into `/work`, which `PATH` prefers |
| `DEPS_REFRESH` | `0` | bump to re-clone wavefront, ffibox and ffimap |

## Mounts

| path | mode | lifetime |
|---|---|---|
| `/target` | read-write, required | the checkout of the C codebase the port works in; the Rust tree and `crustify/` land in it. An existing port is resumed in place |
| `/crustify-rs` | read-write, optional | the whole workspace: the crustify checkout, the plugin itself, with wavefront, ffibox and ffimap beside it, the target forks and the reference crates. Replaces the build-time copy of all four, so one mount serves every tool |
| `/work` | named volume, optional | `HOME`: the agents' session transcripts, the C libraries they build, the cargo registry. Outlives `docker rm`, so a re-created container keeps them. Not the port's files — those land in `/target` |

The Dockerfile header documents the rest: what each mount buys and why the base
image is pinned by digest.
