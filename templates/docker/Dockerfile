# The environment a crustify campaign runs in, for either kind of campaign.
# Nothing here is target-specific, and nothing here starts a campaign: the image
# is a machine, and `crustify` is run inside it.
#
# One image serves both kinds because they want the same machine. The translator
# needs the sanitizers to check what it emitted; an audit needs a C
# toolchain to build what it audits. Two images meant the translate side had
# no miri, no BorrowSanitizer and no MemorySanitizer -- the instruments its
# own prompt asks for -- while the audit side had no CodeQL and no bindgen.
#
#   docker build -t crustify -f templates/Dockerfile .
#
# Start the container idle, then run the orchestrator in it:
#
#   docker run -d --init --name crustify-libgit2 \
#       --security-opt seccomp=unconfined \
#       -e OPENROUTER_API_KEY \
#       -v /absolute/path/to/your/campaign-dir:/target \
#       -v "$(dirname "$PWD"):/crustify-rs" \
#       -v /absolute/path/to/your/CRUSTIFY.md:/campaign/CRUSTIFY.md:ro \
#       -v crustify-libgit2-work:/work \
#       crustify
#   docker exec -it crustify-libgit2 \
#       crustify /target --settings /campaign/CRUSTIFY.md \
#       --backend claude --billing api --model-proxy openrouter
#
# The settings' `campaign` answer picks a port, wrap or audit campaign;
# Crustify waits for instructions unless `--start` runs it right away, and
# `--task-only` makes the settings file the entire prompt (the ablation
# control). See `crustify --help`.
#
# `--security-opt seccomp=unconfined` lets the TSan and BSan runtimes call
# personality(ADDR_NO_RANDOMIZE) at startup; Docker's default profile rejects it
# and every instrumented binary dies before main. Lowering the host's
# vm.mmap_rnd_bits to 28 also works, but needs root on the host.
#
# Mounts:
#
#   /target            Required read-write bind mount: the directory the
#                      campaign works in. It holds the campaign repository --
#                      the Rust at its root, the C under `c/`, the campaign's
#                      own state under `crustify/` -- and the wrapper
#                      repositories of out-of-tree libraries beside it, which
#                      is why it is a directory and not the repository itself.
#                      It may be EMPTY: Crustify creates the repository in it
#                      and takes the C from the `source` its settings name, so
#                      the C does not have to exist on the host. When it
#                      already holds a campaign, that campaign is resumed in
#                      place: its revision, branches, artifacts, CodeQL data
#                      and logs are used where they are and stay on the host,
#                      and nothing there is reset or replaced. An audit creates
#                      no repository, so /target is the reviewed crate's own
#                      checkout.
#   /campaign/CRUSTIFY.md  The campaign settings, read-only, by convention:
#                      `--settings` takes any path, and copies it to
#                      /target/crustify/CRUSTIFY.md on the first run. Edit that
#                      copy on the host to change settings mid-campaign;
#                      Crustify rereads it before each module.
#   /crustify-rs       Optional read-write bind mount of the whole crustify-rs
#                      workspace: the toolchains the campaign uses -- wavefront,
#                      ffibox, ffimap -- beside the target forks and the
#                      reference crates, as they sit on the host. This is where
#                      the tool checkouts LIVE in the image, so one mount
#                      replaces all three at once and the agents browse one
#                      tree instead of three unrelated paths. The image carries
#                      a clone of each from build time, so the mount is
#                      optional; a workspace mounted here must carry a
#                      directory per tool AND a crustify checkout, since each
#                      is reached through a path inside it that otherwise
#                      dangles -- the harness included. An audit uses only
#                      ffimap.
#   /opt/crustify      A read alias for /crustify-rs/crustify, the harness, so
#                      that path still resolves. Not a mount point: mounting
#                      over it changes nothing, because the install and
#                      PYTHONPATH point into the workspace.
#   /work              Named volume, and `HOME`: the agents' session
#                      transcripts, the C libraries they build, the cargo
#                      registry. It outlives `docker rm`, so a container
#                      re-created to change its mounts keeps them. Not the
#                      artifacts -- those land in the campaign repository.
#
# The dashboard template rides the harness tree: the orchestrator reads
# templates/translate/dashboard.template.md from the checkout and writes the filled
# dashboard where the campaign settings say. Nothing is seeded into /target.
#
# One container name per campaign: `docker exec -it <name> bash` opens a shell
# beside the orchestrator, and `docker start <name>` brings a stopped container
# back with post-boot installs intact in its writable layer. Removing the
# container removes that state; bake generally useful packages into the image.
#
# `-it` on `docker exec` because both prompts are built around approval gates.
# Run tmux inside to detach from a long campaign.


# The four tool checkouts, one stage each, named after the tool. One rule
# covers all of them: a stage named `<tool>` produces that tool's tree, and
# `--build-context <tool>=<path>` replaces the stage of that name with a local
# checkout, so its default is never run:
#
#   docker build -t crustify -f templates/Dockerfile \
#       --build-context ffimap=../ffimap \
#       --build-context wavefront=../wavefront .
#
# That is how a private or unpushed tool gets into the image, and it is the
# same flag for every one of the four. What differs is only the default:
#
#   wavefront, ffibox, ffimap   a shallow clone of the default branch, from the
#                               crustify-rs organization
#   crustify                    the build context -- the checkout this
#                               Dockerfile ships in, which is the tree you are
#                               building from
#
# crustify defaults to the context because `docker build -f templates/Dockerfile .`
# is run from a crustify checkout, so the local tree is what one means by
# default.
#
# There is no flag for a branch, and none is needed: a build takes either a
# local checkout or the default branch, and a checkout is already on whatever
# branch you put it on. To build against one, check it out locally and pass the
# tree.
#
# Docker caches a `RUN git clone` by instruction text, which never changes, so
# bump DEPS_REFRESH to re-clone the default branch:
# `--build-arg DEPS_REFRESH=$(date +%s)`. Every clone stage uses the base image
# pinned below, which has git.
ARG DEPS_REFRESH=0
FROM ghcr.io/borrowsanitizer/bsan@sha256:56bbbfd19dec23ba518e9dc2221045b2869cc1f6aabdd8ea40174a41d860a5b2 AS wavefront-clone
ARG DEPS_REFRESH
RUN echo "DEPS_REFRESH=${DEPS_REFRESH}" \
    && git clone --depth 1 https://github.com/crustify-rs/wavefront.git /src
FROM scratch AS wavefront
COPY --from=wavefront-clone /src /
FROM ghcr.io/borrowsanitizer/bsan@sha256:56bbbfd19dec23ba518e9dc2221045b2869cc1f6aabdd8ea40174a41d860a5b2 AS ffibox-clone
ARG DEPS_REFRESH
RUN echo "DEPS_REFRESH=${DEPS_REFRESH}" \
    && git clone --depth 1 https://github.com/crustify-rs/ffibox.git /src
FROM scratch AS ffibox
COPY --from=ffibox-clone /src /
FROM ghcr.io/borrowsanitizer/bsan@sha256:56bbbfd19dec23ba518e9dc2221045b2869cc1f6aabdd8ea40174a41d860a5b2 AS ffimap-clone
ARG DEPS_REFRESH
RUN echo "DEPS_REFRESH=${DEPS_REFRESH}" \
    && git clone --depth 1 https://github.com/crustify-rs/ffimap.git /src
FROM scratch AS ffimap
COPY --from=ffimap-clone /src /
# crustify's default source is the build context, so it needs no clone stage --
# only the same `<tool>` name, so that one flag overrides any of the four. It
# lands in /crustify-rs beside them and is installed from there like the rest.
FROM scratch AS crustify
COPY . /

# The four trees are collected and cleaned in one stage before they ship.
# `--build-context <tool>=<path>` does NOT honour this repository's
# .dockerignore -- that file applies to the default context only -- so a local
# checkout arrives with whatever is in it, and a Rust checkout carries its
# Cargo `target/`: ffibox alone brought 484 MB of build artifacts, 75% of
# everything the four trees weighed. A clone has no `target/`, so the strip is
# a no-op there and costs one cheap layer. `.git` is kept: it is small, and it
# is how one tells which revision a campaign actually ran.
FROM ghcr.io/borrowsanitizer/bsan@sha256:56bbbfd19dec23ba518e9dc2221045b2869cc1f6aabdd8ea40174a41d860a5b2 AS tools
COPY --from=crustify / /tools/crustify
COPY --from=wavefront / /tools/wavefront
COPY --from=ffibox / /tools/ffibox
COPY --from=ffimap / /tools/ffimap
RUN find /tools -type d -name target -prune -exec rm -rf {} + \
    && du -sh /tools/*

# Pinned by DIGEST, not `:latest`. This image's whole premise is that rustc,
# bsan and clang agree on one LLVM version; a moving base silently shifts
# bsan's LLVM out from under the matched clang compiler-rt below and there is
# no error, only instruments that quietly stop finding things. `:latest` moved
# once already mid-campaign. Bump this deliberately.
# The previous pin (sha256:69440e3b...) was garbage-collected from ghcr.io; this is
# `sha-de6ede0`, verified as Ubuntu noble, clang 18, and nightly/bsan on LLVM 23.1.3.
# Named `image`, not `crustify`: `crustify` is the tool stage above, and a
# `--build-context crustify=...` would otherwise shadow this one.
FROM ghcr.io/borrowsanitizer/bsan@sha256:56bbbfd19dec23ba518e9dc2221045b2869cc1f6aabdd8ea40174a41d860a5b2 AS image

ARG CODEQL_VERSION=v2.26.3
ARG PYTHON_VERSION=3.13
# Both backends by default; either can be dropped from the image.
ARG INSTALL_CLAUDE=1
ARG INSTALL_CODEX=1

# /opt/bsan-shim precedes /root/.cargo/bin so `cargo bsan` resolves to the
# toolchain-pinning shim, and /opt/codeql is last because it only exists on
# x86-64 builds. /work/.local/bin precedes /root/.local/bin: Claude Code's
# updater installs under HOME, the /work volume, and its copy there must win
# over the one this image installed, or every update lands unused.
ENV DEBIAN_FRONTEND=noninteractive \
    PATH=/opt/bsan-shim:/opt/venv/bin:/root/.cargo/bin:/work/.local/bin:/root/.local/bin:/opt/codeql:$PATH \
    CARGO_TERM_COLOR=never \
    # Claude Code refuses --dangerously-skip-permissions as root without this.
    IS_SANDBOX=1
# BorrowSanitizer supplies its matched Rust/Clang/LLVM toolchain. Add the
# remaining generic build tools; `nasm`/`yasm` avoid a source build before a
# crypto audit can start. libclang-dev supports ordinary bindgen builds; bsan
# selects its own matched libclang when it instruments a build.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates unzip xz-utils file lld libclang-dev \
        jq ripgrep \
        nasm yasm autoconf automake libtool m4 python3 \
    && rm -rf /var/lib/apt/lists/*

# MSan needs a C compiler whose compiler-rt MATCHES rustc's LLVM, because it is
# the one sanitizer that tolerates no uninstrumented code: anything built
# without it leaves shadow memory poisoned and correct reads report as
# uninitialized. The base image has clang 18 while both Rust toolchains are
# LLVM 23, and the bsan toolchain's own clang-23 is a rust-lang/llvm-project
# build carrying NO compiler-rt at all -- `-fsanitize=memory` there dies on a
# missing libclang_rt.msan.a. So install a stock LLVM 23 for its runtimes.
# The /usr/bin/clang-23 symlink is deliberately removed: cargo-bsan resolves
# clang by the active rustc's LLVM version, and a second clang-23 on PATH is
# exactly how bsan ends up silently instrumenting with the wrong compiler.
# Reach this one by its absolute path only.
RUN install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://apt.llvm.org/llvm-snapshot.gpg.key \
         -o /etc/apt/keyrings/llvm.asc \
    && echo "deb [signed-by=/etc/apt/keyrings/llvm.asc] \
https://apt.llvm.org/noble/ llvm-toolchain-noble-23 main" \
       > /etc/apt/sources.list.d/llvm-23.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends clang-23 libclang-rt-23-dev \
    && rm -f /usr/bin/clang-23 \
    && rm -rf /var/lib/apt/lists/*
ENV CRUSTIFY_MSAN_CC=/usr/lib/llvm-23/bin/clang

# Keep the harness Python independent of whichever Python the base image uses.
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && uv python install "${PYTHON_VERSION}" \
    && uv venv --python "${PYTHON_VERSION}" /opt/venv

# Preserve the base image's `bsan` toolchain, and install our ordinary Rust
# toolchains alongside it. Stable remains the default so unqualified Cargo
# commands do not accidentally compile targets with the custom bsan compiler;
# BorrowSanitizer is invoked explicitly as `cargo +bsan bsan ...`.
# `rustup toolchain install nightly` would SYNC the channel: once upstream
# nightly moves past the base image's, it replaces the base's toolchain, and
# that rename crosses overlayfs layers and dies with EXDEV. It is also
# redundant -- the base ships every component below already. Add them instead,
# which is a no-op that still fails loudly if a future base drops one, and
# leaves rustc on the LLVM the bsan toolchain and clang-23 are matched to.
RUN rustup toolchain install stable --component clippy \
    && rustup component add --toolchain nightly \
         rustc-dev llvm-tools rust-src miri \
    && rustup default stable

# MemorySanitizer and ThreadSanitizer are `-Zsanitizer=` builds, not separate
# toolchains, so nothing extra is installed for them. MSan also needs the standard
# library rebuilt with instrumentation: `-Zbuild-std` over the `rust-src` component
# installed above.

# `cargo bsan` (no `+bsan`) is the form anyone writes by reflex, and it fails in
# the most misleading way available. cargo-bsan picks its clang from the ACTIVE
# rustc's LLVM version, so under the default stable toolchain (LLVM 22) it hunts
# for `clang-22` -- which nobody ships -- and dies with `failed to find
# clang-22`. That reads as "BorrowSanitizer is not installed", and the version
# probe still exits 0, so nothing warns you earlier. Only the bsan toolchain
# carries the matching clang. Cargo also exports `CARGO` as its resolved stable
# binary to subcommands, so override both that path and the toolchain in a shim
# placed ahead of the rustup binary on PATH. Then both `cargo bsan` and
# `cargo +bsan bsan` work.
# The real binary is in the image layer at /root/.cargo/bin -- NOT under
# CARGO_HOME, which is redirected to the /work volume further down.
RUN mkdir -p /opt/bsan-shim \
    && printf '%s\n' '#!/usr/bin/env bash' \
         'exec env RUSTUP_TOOLCHAIN=bsan CARGO=/root/.cargo/bin/cargo /root/.cargo/bin/cargo-bsan "$@"' \
       > /opt/bsan-shim/cargo-bsan \
    && chmod +x /opt/bsan-shim/cargo-bsan

# bindgen for the raw bindings. It dlopens libclang at run time and clang-sys
# looks for the unversioned soname, so the search has to be pinned: this system
# carries libclang 18 (the base) AND libclang 23 (installed above for MSan's
# compiler-rt), and an unpinned bindgen may bind either. 18 is the base image's
# own clang, so it matches the headers everything else here is built against.
# bindgen only parses declarations, so it does not need to agree with the LLVM
# rustc or bsan codegen against.
#
# Installed before CARGO_HOME moves to the /work volume, so the binary lives in
# the image layer at /root/.cargo/bin and survives a fresh volume.
ENV LIBCLANG_PATH=/usr/lib/llvm-18/lib
RUN cargo install bindgen-cli --locked

# CodeQL CLI, for wavefront's extraction queries. GitHub publishes this bundle
# for x86-64 Linux but not native Linux ARM64, so an ARM image ships without it
# and an ARM campaign consumes T1/T2 tables extracted on an x86-64 machine.
# Whether either is usable is the orchestrator's call, not the image's: it
# reads the target's existing tables during setup and installs the cpp pack
# from wavefront's qlpack itself when the CLI is here.
RUN arch="$(dpkg --print-architecture)"; \
    if [ "$arch" = amd64 ]; then \
        curl -fsSL -o /tmp/codeql.zip \
          "https://github.com/github/codeql-cli-binaries/releases/download/${CODEQL_VERSION}/codeql-linux64.zip" \
        && unzip -q /tmp/codeql.zip -d /opt \
        && rm /tmp/codeql.zip; \
    else \
        echo "CodeQL is unavailable natively on $arch; a campaign here needs T1/T2 tables extracted elsewhere"; \
    fi

# Both installers fetch whatever the vendor currently ships. Claude Code then
# updates itself into the /work volume, whose copy PATH prefers, so the one
# installed here only runs until a volume's first update. Codex does not update
# itself, so this layer is its version pin. Docker caches it by instruction
# text, which never changes, so a rebuild silently keeps the CLIs the first
# build happened to get. Bump CLI_REFRESH to refetch:
# `--build-arg CLI_REFRESH=$(date +%s)`. The versions are echoed into the build
# log, but which CLI ran a campaign is recorded only in the banner of each
# agent's transcript.
ARG CLI_REFRESH=0
RUN if [ "${INSTALL_CLAUDE}" = "1" ]; then \
        curl -fsSL https://claude.ai/install.sh | bash; \
    fi \
    && if [ "${INSTALL_CODEX}" = "1" ]; then \
        curl -fsSL https://chatgpt.com/codex/install.sh | sh; \
    fi \
    && echo "CLI_REFRESH=${CLI_REFRESH}" \
    && { [ "${INSTALL_CLAUDE}" = "1" ] && claude --version || true; } \
    && { [ "${INSTALL_CODEX}" = "1" ] && codex --version || true; }

# The three tool checkouts, from their stages above, into /crustify-rs -- the
# workspace layout they have on a developer's machine, where they are siblings
# of the crustify checkout rather than three unrelated paths. One bind mount
# there replaces all three, and the agents read the same tree the user edits.
#
# `<prefix>/share/<name>` is where crustify LOOKS for wavefront and ffibox --
# the data prefix of the environment it is installed in, derived rather than
# configured -- so each lookup path is a symlink into the workspace. Both
# routes therefore land in the mount when there is one: the symlink for the
# documents crustify renders into a prompt, and the editable installs below,
# which record /crustify-rs paths, for the commands.
#
# wavefront and ffimap are Python distributions installed editable, so their
# commands (`wavefront`, `ffimap`) land in /opt/venv/bin, on PATH, and run
# whatever checkout is mounted over the copy; ffibox is a path dependency the
# emitted crates point at, so a checkout is all it needs. ffimap's rustc
# driver is pinned to a dated nightly of its own, installed here; the driver
# itself is built on first scan. A mounted ffimap that pins a different
# nightly needs `rustup toolchain install` run in its driver directory.
# `ln -sT` rather than plain `ln -s`: if a lookup path ever exists as a real
# directory, plain `ln -s` puts the link INSIDE it and the build still
# succeeds, leaving a tree that resolves to nothing. -T makes that an error.
COPY --from=tools /tools /crustify-rs
RUN mkdir -p /opt/venv/share \
    && for tool in wavefront ffibox ffimap; do \
         ln -sT "/crustify-rs/$tool" "/opt/venv/share/$tool"; \
       done \
    && uv pip install --python /opt/venv/bin/python \
         -e /crustify-rs/wavefront -e /crustify-rs/ffimap \
    && (cd /crustify-rs/ffimap/src/ffimap/driver && rustup toolchain install) \
    && ffimap --help > /dev/null

# Bake in a runnable harness -- the WHOLE repository, not just `src`. One
# distribution ships both packages, and the orchestrators are told to read
# templates out of `templates/`, so a partial copy works only until something
# reaches past it. Nothing expensive follows this layer, so a cache miss here
# costs seconds.
#
# A bind mount at this path replaces these sources. The install is editable and
# PYTHONPATH points at the same tree, so a mounted checkout wins twice over.
#
# The harness goes in the workspace with the other three, installed from the
# same path shape and overridden the same way, so the four are consistent: a
# workspace mounted over /crustify-rs supplies all four, and the harness that
# renders the prompts is then the same tree the agents read. An editable
# install is a path entry, not a copy, so the mount redirects it with no
# re-install.
#
# /opt/crustify stays as a read alias, so a path written down anywhere still
# resolves -- but it is NOT an override any more. Bind-mounting over it would
# replace the alias while PYTHONPATH and the install still pointed into
# /crustify-rs, which is the split the move removes. Override the harness with
# the workspace mount, or at build time with `--build-context crustify=`.
COPY --from=crustify / /crustify-rs/crustify
RUN uv pip install --python /opt/venv/bin/python -e /crustify-rs/crustify \
    && ln -sT /crustify-rs/crustify /opt/crustify
ENV PYTHONPATH=/crustify-rs/crustify/src

# HOME is the volume, so what the agent fetches or builds survives `--rm`.
# RUSTUP_HOME is pinned back out of it: rustup resolves from HOME, and against
# an empty volume `cargo +nightly` finds no toolchain and silently downloads a
# fresh nightly WITHOUT this image's components — losing miri unannounced.
# CARGO_HOME does belong on the volume, for the registry cache.
ENV HOME=/work \
    RUSTUP_HOME=/root/.rustup \
    CARGO_HOME=/work/.cargo
RUN mkdir -p /work /target

# /target is a bind mount owned by the HOST user while the container runs as
# root, so git rejects it for "dubious ownership" -- which breaks recording the
# audited revision and every worktree a campaign creates. --system,
# not --global: HOME is the named volume, and a gitconfig written under it at
# build time is masked whenever that volume already exists.
RUN git config --system --add safe.directory '*'


# The required target bind mount shadows this empty image directory. Starting
# in it makes that directory the campaign's unambiguous home: a campaign
# already there is resumed in place, and an empty one is where the campaign
# repository gets created.
WORKDIR /target
# Run it with `--init`, so the processes a campaign leaves behind are reaped
# rather than collecting as zombies under this idle process.
# Idle by default so the container is an environment, not one run: a campaign
# started with `docker exec <name> crustify /target ...`
# survives its own crash, and a shell beside it can read the worktrees and caches
# it left.
CMD ["sleep", "infinity"]
