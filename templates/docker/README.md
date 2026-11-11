# Docker

[`Dockerfile`](Dockerfile) builds the environment either campaign runs in. It starts
nothing: the container idles, and Crustify's assistant is opened inside it.

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
| `wavefront`, `ffibox`, `ffimap` | a shallow clone of the `devel` branch, from the `crustify-rs` organization: the line campaigns run and the skills follow |
| `crustify` | the build context, the checkout this Dockerfile ships in |

crustify defaults to the context because the build is run from a crustify checkout, so
the local tree is what one means by default.

There is no flag for a branch. A build takes either a local checkout or `devel`, and a
checkout is already on whatever branch you put it on: to build against one, check it out
locally, switch to it, and pass the tree.

A `RUN git clone` is cached by its instruction text, which never changes, so bump
`DEPS_REFRESH` to re-clone the tools' branches.

Start a container per campaign, idle:

```sh
docker run -d --init --name crustify-libgit2 \
    --security-opt seccomp=unconfined \
    -e ANTHROPIC_API_KEY \
    -v /absolute/path/to/your/campaign-dir:/target \
    -v "$(dirname "$PWD"):/crustify-rs" \
    -v crustify-libgit2-work:/work \
    crustify
```

Open Crustify's assistant in it, in the directory the campaign works in:

```sh
docker exec -it -w /target crustify-libgit2 \
    claude --plugin-dir /opt/crustify --agent crustify:assistant-translate
```

`crustify:assistant-audit` opens an audit's, in a container started the same way, with its
own `/work` volume. The assistant waits for your instructions; ask it to start the campaign,
or pass that as the first prompt with `-p` to run it headless, which a session without a
terminal (`docker exec` without `-it`) needs.

The settings live in the campaign's repository as `crustify/CRUSTIFY.md`, tracked on the
working branch, `crustify/devel`. The assistant asks for them live, or reads a filled
settings template you give it, and writes them there. Edit that file to change a
campaign's settings while it runs, such as its models or batch sizes: Crustify rereads it
before each module, or each review wave of an audit, and commits it whenever it applies a
change, so the branch's history records the settings each one ran under. `main` is the
shipping branch, which Crustify advances to `crustify/devel` only with your approval. A
later session opened in the repository resumes the campaign, and `claude --resume`
continues an earlier session.

The ablation control, one bare agent given only the task, is
[`audit/BARE.md`](../audit/BARE.md)'s.

`--init` runs a small init process as the container's first process, so the
processes the agents leave behind are reaped instead of piling up as zombies
under `sleep infinity`.

`--security-opt seccomp=unconfined` is what lets the TSan and BSan builds run.
Both runtimes call `personality(ADDR_NO_RANDOMIZE)` at startup, which Docker's
default seccomp profile rejects, so every instrumented binary would die before
`main`. The alternative is lowering the host's `vm.mmap_rnd_bits` to 28, which
needs root on the host.

`/target` is the directory the campaign works in, mounted read-write. The
campaign repository goes in it — the Rust at its root, the C under `c/`, the
campaign's own state under `crustify/`, as the [`layout`](../../skills/operations/layout/SKILL.md) skill
lays it out — and the wrapper repositories of out-of-tree libraries are cloned
beside it there. That is why the mount is a directory rather than the
repository itself.

It may be empty. Crustify creates the repository in it and takes the C from the
`source` its settings name, so the C target does not have to be on the host at
all; a checkout already there can be named as the source instead. When
`/target` already holds a campaign, that campaign is resumed in place: its
revision, branches, artifacts, CodeQL data and logs are used where they are and
stay on the host, and nothing there is reset or replaced.

An audit creates no repository: it reviews a crate in the crate's own, so
`/target` is that checkout.

`/crustify-rs` is optional, and is the whole workspace rather than one tool:
wavefront, ffibox and ffimap as siblings of the crustify checkout, beside the
target forks and the reference crates, exactly as they sit on the host. That is
where the three tool checkouts live in the image, so one mount replaces all
three at once, and the agents read the same trees you edit instead of three
paths unrelated to each other or to anything on your machine. The image carries
a build-time clone of each, so leaving the mount off is fine; a workspace
mounted here must carry a directory per tool and a crustify checkout, since each is
reached through a path inside it that otherwise dangles — Crustify included.
An audit run uses only ffimap.

`/target` stays its own mount even when the target fork lives in the workspace:
Crustify works in `/target`, and a target that is also under `/crustify-rs` is
simply visible at both paths, the same tree through two mounts. Keeping them
separate is what lets a target sit elsewhere entirely — on a volume with room
for its builds and CodeQL data, say — while the toolchains stay in the
workspace.

`wavefront` and `ffimap` are installed editable from their workspace paths, so the
commands on `PATH` run the mounted code. `/opt/venv/share/<tool>`, the path a campaign's
manifest names ffibox by, is a symlink into the workspace. An editable install is a path
entry, not a copy, so a mount redirects it with no re-install. Re-run
`uv pip install -e /crustify-rs/<tool>` only when the mounted tree adds a console script,
adds a dependency, or moves its package out of `src/`.

Crustify itself is in the workspace with the other three, at `/crustify-rs/crustify`, and
`/opt/crustify`, the plugin directory the assistant is opened with, is a symlink to it. So
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
is a settings answer.

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

| path | mode | used by | lifetime |
|---|---|---|---|
| `/target` | read-write, required | both | the directory the campaign works in, or, for an audit, the reviewed crate's own checkout: the campaign repository, with the C under `c/`, and the wrapper repositories beside it. May be empty — Crustify creates the repository and fetches the C. An existing campaign is resumed in place, and its branches, artifacts, CodeQL data and logs stay on the host |
| `/crustify-rs` | read-write, optional | both | the whole workspace: the crustify checkout, the plugin itself, with wavefront, ffibox and ffimap beside it, the target forks and the reference crates. Replaces the build-time copy of all four, so one mount serves every tool |
| `/work` | named volume, optional | both | `HOME`: the agents' session transcripts, the C libraries they build, the cargo registry. Outlives `docker rm`, so a re-created container keeps them. Not the artifacts — those land in the campaign repository |

## Dashboards

Campaign dashboards are written into the campaign repository, at
`crustify/artifacts/dashboard.md` (`audit-dashboard.md` for an audit) unless the
settings name another path, filled from [`dashboard.template.md`](../translate/dashboard.template.md).

The Dockerfile header documents the rest: what each mount buys and why the base
image is pinned by digest.
