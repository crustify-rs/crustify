# The environment a crustify campaign runs in, for either kind of campaign.
# Nothing here is target-specific, and nothing here starts a campaign: the image
# is a machine, and `crustify` is run inside it.
#
# One image serves both kinds because they want the same machine. The translator
# needs the sanitizers to check what it emitted; the auditor needs a C
# toolchain to build what it audits. Two images meant the translate side had
# no miri, no BorrowSanitizer and no MemorySanitizer -- the instruments its
# own prompt asks for -- while the audit side had no CodeQL and no bindgen.
#
#   docker build -t crustify -f examples/Dockerfile .
#
# Start the container idle, then run the orchestrator in it:
#
#   docker run -d --init --name crustify-libgit2 \
#       --security-opt seccomp=unconfined \
#       -e OPENROUTER_API_KEY \
#       -v "$(dirname "$PWD")/wavefront:/opt/venv/share/wavefront" \
#       -v "$(dirname "$PWD")/ffibox:/opt/venv/share/ffibox" \
#       -v /absolute/path/to/your/target-fork:/target \
#       -v "$PWD/examples/crustify/libgit2/src-port/TASK.md:/campaign/TASK.md:ro" \
#       -v crustify-libgit2-work:/work \
#       crustify
#   docker exec -it crustify-libgit2 \
#       crustify translate /target /campaign/TASK.md \
#       --model openrouter/anthropic/claude-opus-5 --billing api
#
# `crustify audit` starts an audit campaign instead, and `--task-only` makes
# the task file the entire prompt (the ablation control). The deterministic
# scan needs no agent and no auth: `docker exec <name> crustify scan-unsafe
# /target`. Every other choice is an option of the command; see
# `crustify <command> --help`.
#
# `--security-opt seccomp=unconfined` lets the TSan and BSan runtimes call
# personality(ADDR_NO_RANDOMIZE) at startup; Docker's default profile rejects it
# and every instrumented binary dies before main. Lowering the host's
# vm.mmap_rnd_bits to 28 also works, but needs root on the host.
#
# Mounts:
#
#   /target            Required read-write bind mount of an existing Git
#                      checkout. Its revision, branches, `crustify/` directory,
#                      CodeQL data, partial translation and logs are used in
#                      place and remain on the host. The orchestrator must not
#                      clone, reset or replace it.
#   /campaign/TASK.md  The campaign task, read-only, by convention: the
#                      orchestrate command takes any path. Edit on the host
#                      and the next run picks it up.
#   /opt/crustify      The harness, baked into the image. Mount a checkout here
#                      to test live harness changes. Both packages live in one
#                      distribution, so this single tree serves both roles.
#   /opt/venv/share/{wavefront,ffibox}
#                      Optional read-write host checkouts. This is where
#                      crustify LOOKS for them -- `<prefix>/share/<name>` for
#                      the environment it is installed in -- so nothing
#                      configures a path. The image carries a clone of each
#                      from build time; a mount replaces it, so a campaign runs
#                      against the trees under development. An audit touches
#                      neither.
#   /work              Named volume, and `HOME`: the agents' session
#                      transcripts, the C libraries they build, the cargo
#                      registry. It outlives `docker rm`, so a container
#                      re-created to change its mounts keeps them. Not the
#                      artifacts -- those land in the target checkout.
#
# The results template rides the /opt/crustify mount: the orchestrator reads
# examples/crustify/results-template.md from the checkout and writes the filled
# table where the campaign task says. Nothing is seeded into /target.
#
# One container name per campaign: `docker exec -it <name> bash` opens a shell
# beside the orchestrator, and `docker start <name>` brings a stopped container
# back with post-boot installs intact in its writable layer. Removing the
# container removes that state; bake generally useful packages into the image.
#
# `-it` on `docker exec` because both prompts are built around approval gates.
# Run tmux inside to detach from a long campaign.


# Pinned by DIGEST, not `:latest`. This image's whole premise is that rustc,
# bsan and clang agree on one LLVM version; a moving base silently shifts
# bsan's LLVM out from under the matched clang compiler-rt below and there is
# no error, only instruments that quietly stop finding things. `:latest` moved
# once already mid-campaign. Bump this deliberately.
# The previous pin (sha256:69440e3b...) was garbage-collected from ghcr.io; this is
# `sha-de6ede0`, verified as Ubuntu noble, clang 18, and nightly/bsan on LLVM 23.1.3.
FROM ghcr.io/borrowsanitizer/bsan@sha256:56bbbfd19dec23ba518e9dc2221045b2869cc1f6aabdd8ea40174a41d860a5b2

ARG CODEQL_VERSION=v2.26.3
ARG PYTHON_VERSION=3.13
# Both backends by default; either can be dropped from the image.
ARG INSTALL_CLAUDE=1
ARG INSTALL_CODEX=1

# /opt/bsan-shim precedes /root/.cargo/bin so `cargo bsan` resolves to the
# toolchain-pinning shim, and /opt/codeql is last because it only exists on
# x86-64 builds.
ENV DEBIAN_FRONTEND=noninteractive \
    PATH=/opt/bsan-shim:/opt/venv/bin:/root/.cargo/bin:/root/.local/bin:/opt/codeql:$PATH \
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

# bindgen for the `-sys` crates. It dlopens libclang at run time and clang-sys
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

# Both installers fetch whatever the vendor currently ships, so this layer IS
# the version pin. Docker caches it by instruction text, which never changes,
# so a rebuild silently keeps the CLIs the first build happened to get. Bump
# CLI_REFRESH to refetch: `--build-arg CLI_REFRESH=$(date +%s)`. The versions
# are echoed into the build log because otherwise the only record of which CLI
# ran a campaign is the banner in each agent's transcript.
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

# The two capability checkouts a translate campaign uses, cloned where crustify
# looks for them: `<prefix>/share/<name>`. wavefront is a Python distribution
# and is installed editable, so a checkout mounted over the clone is what runs;
# ffibox is a path dependency the emitted crates point at, so a checkout is all
# it needs. Docker caches this layer by instruction text, so bump DEPS_REFRESH
# to re-clone `main`: `--build-arg DEPS_REFRESH=$(date +%s)`.
ARG DEPS_REFRESH=0
RUN echo "DEPS_REFRESH=${DEPS_REFRESH}" \
    && git clone --depth 1 https://github.com/crustify-rs/wavefront.git /opt/venv/share/wavefront \
    && git clone --depth 1 https://github.com/crustify-rs/ffibox.git /opt/venv/share/ffibox \
    && uv pip install --python /opt/venv/bin/python -e /opt/venv/share/wavefront

# Bake in a runnable harness -- the WHOLE repository, not just `src`. One
# distribution ships both packages, and the orchestrators are told to read
# templates out of `examples/`, so a partial copy works only until something
# reaches past it. Nothing expensive follows this layer, so a cache miss here
# costs seconds.
#
# A bind mount at this path replaces these sources. The install is editable and
# PYTHONPATH points at the same tree, so a mounted checkout wins twice over.
COPY . /opt/crustify
RUN uv pip install --python /opt/venv/bin/python -e /opt/crustify
ENV PYTHONPATH=/opt/crustify/src

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
# in it makes the existing checkout -- and any partial campaign -- the
# orchestrator's unambiguous working repository.
WORKDIR /target
# Run it with `--init`, so the processes a campaign leaves behind are reaped
# rather than collecting as zombies under this idle process.
# Idle by default so the container is an environment, not one run: a campaign
# started with `docker exec <name> crustify translate ...`
# survives its own crash, and a shell beside it can read the worktrees and caches
# it left.
CMD ["sleep", "infinity"]
