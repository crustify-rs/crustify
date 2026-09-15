# Bootstraps a crustify ORCHESTRATOR, in either role. Nothing here is
# target-specific.
#
# One image serves both because they want the same machine. The translator
# needs the sanitizers to check what it emitted; the auditor needs a C
# toolchain to build what it audits. Two images meant the translate side had
# no miri, no BorrowSanitizer and no MemorySanitizer -- the instruments its
# own playbook asks for -- while the audit side had no CodeQL and no bindgen.
#
#   docker build -t crustify -f examples/Dockerfile .
#
# The two campaigns differ in one thing only -- which orchestrator prompt they
# load -- and CRUSTIFY_COMMAND selects it. It has NO default: a wrong guess
# starts the wrong agent and spends a budget before anyone reads the transcript.
#
#   # translate
#   docker run -it --name crustify-libgit2 \
#       -e CRUSTIFY_COMMAND=translate \
#       -e ANTHROPIC_API_KEY -e CRUSTIFY_BACKEND=claude \
#       -v "$(dirname "$PWD")/wavefront:/opt/wavefront" \
#       -v "$(dirname "$PWD")/ffibox:/opt/ffibox" \
#       -v /absolute/path/to/your/target-fork:/target \
#       -v "$PWD/examples/crustify/libgit2/src-port/TASK.md:/campaign/TASK.md:ro" \
#       crustify
#
#   # audit
#   docker run --rm -it --name audit-ippcp \
#       -e CRUSTIFY_COMMAND=audit \
#       -e ANTHROPIC_API_KEY \
#       -v /path/to/target-repo:/target \
#       -v /host/campaign/TASK.md:/campaign/TASK.md:ro \
#       -v audit-ippcp-work:/work \
#       crustify
#
# The deterministic scan needs no agent and no auth, so it bypasses the
# orchestrator entirely: `docker run ... crustify crustify /target audit unsafe`.
# CRUSTIFY_BARE=1 makes the mounted TASK.md the entire prompt, for either
# command -- the ablation control, and the only other way in.
#
# Mounts:
#
#   /target            Required read-write bind mount of an existing Git
#                      checkout. Its revision, branches, `crustify/` directory,
#                      CodeQL data, partial translation and logs are used in
#                      place and remain on the host. The orchestrator must not
#                      clone, reset or replace it.
#   /campaign/TASK.md  The campaign task, read-only. Edit on the host and the
#                      next run picks it up. Without it the orchestrator asks
#                      for unresolved details interactively.
#   /opt/crustify      The harness, baked into the image. Mount a checkout here
#                      to test live harness changes. Both packages live in one
#                      distribution, so this single tree serves both roles.
#   /opt/{wavefront,ffibox}
#                      Optional read-write host checkouts, used by a translate
#                      run and untouched by an audit. A mount always wins; when
#                      one is absent the entrypoint clones main into it and says
#                      so on stderr, because a silent clone is how a run comes
#                      to differ from the checkout it was believed to test.
#   /work              Named volume, and `HOME`: the C library the agent
#                      builds, the cargo registry. Not the artifacts -- those
#                      land in the target checkout.
#
# The results template rides the /opt/crustify mount: the orchestrator reads
# examples/crustify/results-template.md from the checkout and writes the filled
# table where the campaign task says. Nothing is seeded into /target.
#
# One container name per campaign: `docker attach` reaches a detached run,
# `docker exec -it <name> bash` opens a shell beside the orchestrator, and
# `docker start -ai <name>` resumes a stopped run with post-boot installs
# intact in the container's writable layer. Removing the container removes that
# state; bake generally useful packages into the image.
#
# `-it` because both prompts are built around approval gates. Detach with `-d`
# and attach later, or run tmux inside.


# Pinned by DIGEST, not `:latest`. This image's whole premise is that rustc,
# bsan and clang agree on one LLVM version; a moving base silently shifts
# bsan's LLVM out from under the matched clang compiler-rt below and there is
# no error, only instruments that quietly stop finding things. `:latest` moved
# once already mid-campaign. Bump this deliberately, and re-run the self-tests.
FROM ghcr.io/borrowsanitizer/bsan@sha256:69440e3b6359f3b51ae351998dc4d408777cde23d72a6adc05ed649570cfdce0

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
# uninitialized. The base image has clang 20 while both Rust toolchains are
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
https://apt.llvm.org/plucky/ llvm-toolchain-plucky-23 main" \
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
    && rustup default stable \
    && cargo +nightly miri --version

# MemorySanitizer and ThreadSanitizer are `-Zsanitizer=` builds, not separate
# toolchains, so nothing extra is installed for them -- but they are only usable
# if two things hold, and both fail late and confusingly when they do not.
# First, the target must support them: check the target spec rather than
# discovering it from a failed link at the end of a long build. Second, MSan
# needs the standard library rebuilt with instrumentation, which is `-Zbuild-std`
# over the `rust-src` component installed above; without it every std allocation
# reads as uninitialized and the run drowns in false positives.
RUN set -eu; \
    spec=$(rustc +nightly -Z unstable-options --print target-spec-json \
             --target "$(rustc -vV | sed -n 's/^host: //p')"); \
    for s in memory thread; do \
        echo "$spec" | grep -q "\"$s\"" \
          || { echo "target does not support -Zsanitizer=$s" >&2; exit 1; }; \
    done; \
    test -d "$(rustc +nightly --print sysroot)/lib/rustlib/src/rust/library/std" \
      || { echo "rust-src missing: -Zbuild-std cannot instrument std" >&2; exit 1; }

# Prove the C half of an MSan build links and REPORTS, the same way the bsan
# self-test does. A version string cannot distinguish a clang that merely exists
# from one whose compiler-rt is actually present, and that difference only
# surfaces at the final link of a long instrumented build -- or worse, as a
# campaign that records msan as "found nothing".
RUN set -eu; \
    printf '%s\n' '#include <stdlib.h>' 'int main(void) {' \
        '    int *a = malloc(sizeof(int) * 10);' \
        '    a[5] = 0;' \
        '    if (a[0]) return 1;' \
        '    return 0; }' > /tmp/msan-selftest.c; \
    "$CRUSTIFY_MSAN_CC" -fsanitize=memory -fno-omit-frame-pointer -O1 \
        /tmp/msan-selftest.c -o /tmp/msan-selftest \
      || { echo "msan: C link failed -- compiler-rt missing" >&2; exit 1; }; \
    /tmp/msan-selftest 2>&1 | grep -q "use-of-uninitialized-value" \
      || { echo "msan: built but did not report a known uninit read" >&2; exit 1; }; \
    rm -f /tmp/msan-selftest /tmp/msan-selftest.c

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

# Verify BorrowSanitizer by INVOCATION, not by version string. `cargo bsan
# --version` answers from the binary alone: it exits 0 on an image whose
# toolchain cannot instrument anything, so it cannot tell a working image from a
# broken one. Build and RUN a known Tree Borrows violation instead, and require
# the diagnostic. A silently inert bsan is worse than an absent one -- an
# auditor that cannot run it records its entire bug class as UNTESTED, and a
# whole campaign's aliasing coverage is lost without a single failed command.
RUN set -eu; \
    mkdir -p /tmp/bsan-selftest/src; \
    printf '%s\n' '[package]' 'name = "bsan_selftest"' 'version = "0.0.0"' \
        'edition = "2021"' > /tmp/bsan-selftest/Cargo.toml; \
    printf '%s\n' 'fn main() {' \
        '    let mut x = 42u8;' \
        '    let p = &mut x as *mut u8;' \
        '    let r = &mut x;' \
        '    *r = 1;' \
        '    unsafe { *p = 7; }' \
        '    println!("{}", x);' \
        '}' > /tmp/bsan-selftest/src/main.rs; \
    cd /tmp/bsan-selftest; \
    cargo bsan run > /tmp/bsan-selftest.log 2>&1 || true; \
    grep -q 'Undefined Behavior' /tmp/bsan-selftest.log \
      || { echo "BSan did not fire on a known Tree Borrows violation:" >&2; \
           cat /tmp/bsan-selftest.log >&2; exit 1; }; \
    cd /; rm -rf /tmp/bsan-selftest /tmp/bsan-selftest.log

# bindgen for the `-sys` crates. It dlopens libclang at run time and clang-sys
# looks for the unversioned soname, so the search has to be pinned: this system
# carries libclang 20 (the base) AND libclang 23 (installed above for MSan's
# compiler-rt), and an unpinned bindgen may bind either. 20 is the base image's
# own clang, so it matches the headers everything else here is built against.
# bindgen only parses declarations, so it does not need to agree with the LLVM
# rustc or bsan codegen against.
#
# Installed before CARGO_HOME moves to the /work volume, so the binary lives in
# the image layer at /root/.cargo/bin and survives a fresh volume.
ENV LIBCLANG_PATH=/usr/lib/llvm-20/lib
RUN cargo install bindgen-cli --locked \
    && bindgen --version

# CodeQL CLI, for wavefront's extraction queries. GitHub publishes this bundle
# for x86-64 Linux but not native Linux ARM64, so an ARM image ships without it
# and an ARM campaign consumes T1/T2 tables extracted on an x86-64 machine.
# Whether either is usable is the orchestrator's call, not the entrypoint's: it
# reads the target's existing tables during Bootstrap and installs the cpp pack
# from wavefront's qlpack itself when the CLI is here.
RUN arch="$(dpkg --print-architecture)"; \
    if [ "$arch" = amd64 ]; then \
        curl -fsSL -o /tmp/codeql.zip \
          "https://github.com/github/codeql-cli-binaries/releases/download/${CODEQL_VERSION}/codeql-linux64.zip" \
        && unzip -q /tmp/codeql.zip -d /opt \
        && rm /tmp/codeql.zip \
        && codeql version --format=terse; \
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

# Bake in a runnable harness -- the WHOLE repository, not just `src`. One
# distribution ships both packages (`crustify-audit` is a console script of
# `crustify`), and the orchestrators are told to read templates out of
# `examples/`, so a partial copy works only until something reaches past it.
# Nothing expensive follows this layer, so a cache miss here costs seconds.
#
# A bind mount at this path replaces these sources. The install is editable and
# PYTHONPATH points at the same tree, so a mounted checkout wins twice over.
# `dependencies = []`, so this needs no network and the entrypoint can refresh
# it offline against whatever is mounted.
COPY . /opt/crustify
RUN uv pip install --python /opt/venv/bin/python -e /opt/crustify \
    && crustify --help >/dev/null \
    && crustify . . audit --help >/dev/null \
    && crustify . . orchestrate --help >/dev/null
ENV PYTHONPATH=/opt/crustify/src

# Which campaign the container starts. The two differ in one thing only --
# which orchestrator prompt they load -- but that one thing decides the whole
# run, so there is NO default: a wrong guess starts the wrong agent and spends
# a budget before anyone reads the transcript.
ENV CRUSTIFY_COMMAND=
# Absolute paths for a target's cli-config.json, which is machine-local and
# cannot come from any clone. The orchestrator playbook's "Bootstrap
# crustify/" reads these by name: set here, copied verbatim into `deps` and
# `bins`. CRUSTIFY_DEP_CRUSTIFY doubles as the "this environment is already
# provisioned" flag that tells it not to re-clone the checkouts above.
ENV CRUSTIFY_DEP_CRUSTIFY=/opt/crustify \
    CRUSTIFY_DEP_FFIBOX=/opt/ffibox \
    CRUSTIFY_DEP_WAVEFRONT=/opt/wavefront \
    CRUSTIFY_DEP_AUDIT=/opt/crustify \
    CRUSTIFY_BIN_CLI=/opt/venv/bin/crustify \
    CRUSTIFY_BIN_WAVEFRONT=/opt/venv/bin/wavefront \
    CRUSTIFY_BIN_AUDIT=/opt/venv/bin/crustify-audit

# The CLI, model and gateway used by the ORCHESTRATOR, whichever role runs.
# The agents an orchestrator spawns get theirs per wave from `crustify --model`
# or per auditor from the orchestrator's own `--model`.
ENV CRUSTIFY_BACKEND=claude
ENV CRUSTIFY_MODEL=claude-opus-5
ENV CRUSTIFY_PROVIDER=

# Interactive by default: translate asks what to port before Phase 1 and
# reports a wave's --dry-run plan before spending on it; audit asks for
# mandatory TASK answers still missing. Headless answers neither, so set 1 only
# when the task description pre-answers everything.
ENV CRUSTIFY_HEADLESS=0

# ABLATION SWITCH, audit only. With CRUSTIFY_BARE=1 the harness contributes
# NOTHING to the prompt -- the TASK file is the whole prompt.
ENV CRUSTIFY_BARE=0

# Reasoning effort for a codex orchestrator. codex infers none and falls back
# to low, which suits neither planning a wave nor reading a build system. Empty
# leaves codex its default. Ignored by the claude backend.
ENV CRUSTIFY_EFFORT=high

# How the ORCHESTRATOR authenticates, the container's echo of crustify's
# `--billing`. Neither CLI switches to API-key auth on the key alone -- claude
# keeps sending its stored OAuth token unless `--bare`, and codex's built-in
# openai provider reads auth.json and 401s on OPENAI_API_KEY unless the
# provider is redeclared with an env_key -- so a key in the environment does
# nothing until this says to use it. `api` (the default, since a fresh image
# holds no login) or `subscription` for a run with credentials mounted in.
ENV CRUSTIFY_BILLING=api

# Minutes per auditor. Audit only.
ENV CRUSTIFY_TIMEOUT=60

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
# audited revision and every worktree the patch objective creates. --system,
# not --global: HOME is the named volume, and a gitconfig written under it at
# build time is masked whenever that volume already exists.
RUN git config --system --add safe.directory '*'



# One resolver and one exec, shared by both orchestrators. The two roles differ
# only in what they check before starting and how they build the prompt; the
# backend, gateway, billing and effort handling below is the same job, and was
# previously duplicated -- which is how the translate path came to have no
# --model and no openrouter support.
RUN mkdir -p /usr/local/lib/crustify
RUN printf '%s\n' \
      '# Shared agent invocation for both orchestrators. Sourced rather than exec-ed' \
      '# so a prompt can reference the resolved provider before the agent starts.' \
      '' \
      '# Sets: backend, provider, auth[], effort[]. Exits on any bad combination.' \
      'crustify_resolve_agent() {' \
      '    case "${CRUSTIFY_BACKEND:-}" in' \
      '        claude) backend=claude ;;' \
      '        codex)  backend=codex ;;' \
      '        *) echo "bad CRUSTIFY_BACKEND: ${CRUSTIFY_BACKEND:-<empty>} (claude|codex)" >&2' \
      '           exit 2 ;;' \
      '    esac' \
      '    case "$backend/${CRUSTIFY_PROVIDER:-}" in' \
      '        claude/|claude/anthropic) provider=anthropic ;;' \
      '        claude/openrouter)        provider=openrouter ;;' \
      '        codex/|codex/openai)      provider=openai ;;' \
      '        codex/openrouter)         provider=openrouter ;;' \
      '        *) echo "bad CRUSTIFY_PROVIDER for $backend: ${CRUSTIFY_PROVIDER:-<empty>}" >&2' \
      '           exit 2 ;;' \
      '    esac' \
      '    [ -n "${CRUSTIFY_MODEL:-}" ] || {' \
      '        echo "CRUSTIFY_MODEL must name the orchestrator model" >&2; exit 2; }' \
      '    # Checked here: an agent with no usable auth issues no request and exits' \
      '    # 0, which reads as a hunt that found nothing.' \
      '    auth=()' \
      '    case "${CRUSTIFY_BILLING:-}" in' \
      '        subscription)' \
      '            [ "$provider" != openrouter ] || {' \
      '                echo "openrouter requires CRUSTIFY_BILLING=api" >&2; exit 2; } ;;' \
      '        api|"")' \
      '            case "$backend/$provider" in' \
      '            # Claude Code speaks to any Anthropic-compatible gateway through' \
      '            # ANTHROPIC_BASE_URL. The key must be blanked explicitly or the' \
      '            # CLI keeps preferring it over the gateway token. No --bare here:' \
      '            # that switch forces ANTHROPIC_API_KEY auth, which is empty.' \
      '            claude/openrouter) [ -n "${OPENROUTER_API_KEY:-}" ] || {' \
      '                echo "CRUSTIFY_BILLING=api needs OPENROUTER_API_KEY" >&2; exit 2; }' \
      '                export ANTHROPIC_BASE_URL="https://openrouter.ai/api"' \
      '                export ANTHROPIC_AUTH_TOKEN="$OPENROUTER_API_KEY"' \
      '                export ANTHROPIC_API_KEY="" ;;' \
      '            claude/anthropic) [ -n "${ANTHROPIC_API_KEY:-}" ] || {' \
      '                echo "CRUSTIFY_BILLING=api needs ANTHROPIC_API_KEY" >&2; exit 2; }' \
      '                auth=(--bare) ;;' \
      '            codex/openai) [ -n "${OPENAI_API_KEY:-}" ] || {' \
      '                echo "CRUSTIFY_BILLING=api needs OPENAI_API_KEY" >&2; exit 2; }' \
      '                auth=(-c "model_provider=openai_apikey"' \
      '                      -c "model_providers.openai_apikey.name=\"OpenAI\""' \
      '                      -c "model_providers.openai_apikey.base_url=\"https://api.openai.com/v1\""' \
      '                      -c "model_providers.openai_apikey.env_key=\"OPENAI_API_KEY\""' \
      '                      -c "model_providers.openai_apikey.wire_api=\"responses\"") ;;' \
      '            codex/openrouter) [ -n "${OPENROUTER_API_KEY:-}" ] || {' \
      '                echo "CRUSTIFY_BILLING=api needs OPENROUTER_API_KEY" >&2; exit 2; }' \
      '                auth=(-c "model_provider=openrouter_apikey"' \
      '                      -c "model_providers.openrouter_apikey.name=\"OpenRouter\""' \
      '                      -c "model_providers.openrouter_apikey.base_url=\"https://openrouter.ai/api/v1\""' \
      '                      -c "model_providers.openrouter_apikey.env_key=\"OPENROUTER_API_KEY\""' \
      '                      -c "model_providers.openrouter_apikey.wire_api=\"responses\"") ;;' \
      '            esac ;;' \
      '        *) echo "bad CRUSTIFY_BILLING: ${CRUSTIFY_BILLING}" >&2; exit 2 ;;' \
      '    esac' \
      '    effort=()' \
      '    case "${CRUSTIFY_EFFORT:-}" in' \
      '        "") ;;' \
      '        low|medium|high|xhigh|max|ultra)' \
      '            effort=(-c "model_reasoning_effort=\"${CRUSTIFY_EFFORT}\"") ;;' \
      '        *) echo "bad CRUSTIFY_EFFORT: ${CRUSTIFY_EFFORT}" >&2; exit 2 ;;' \
      '    esac' \
      '}' \
      '' \
      'crustify_exec_agent() {' \
      '    text="$1"; shift' \
      '    skip=--dangerously-skip-permissions' \
      '    bypass=--dangerously-bypass-approvals-and-sandbox' \
      '    case "${backend}:${CRUSTIFY_HEADLESS}" in' \
      '        claude:0) exec claude "$skip" "${auth[@]}" --model "$CRUSTIFY_MODEL" "$text" "$@" ;;' \
      '        claude:1) exec claude "$skip" "${auth[@]}" --model "$CRUSTIFY_MODEL" -p "$text" "$@" ;;' \
      '        codex:0)  exec codex "$bypass" "${auth[@]}" "${effort[@]}" --model "$CRUSTIFY_MODEL" "$text" "$@" ;;' \
      '        codex:1)  exec codex exec "$bypass" "${auth[@]}" "${effort[@]}" --model "$CRUSTIFY_MODEL" "$text" "$@" ;;' \
      '        *) echo "bad CRUSTIFY_BACKEND/CRUSTIFY_HEADLESS:" \' \
      '                "${CRUSTIFY_BACKEND}/${CRUSTIFY_HEADLESS}" >&2; exit 2 ;;' \
      '    esac' \
      '}' \
      > /usr/local/lib/crustify/agent.sh

# The one orchestrator. CRUSTIFY_COMMAND selects the prompt; everything else
# below is shared.
RUN printf '%s\n' \
      '#!/usr/bin/env bash' \
      'set -euo pipefail' \
      '. /usr/local/lib/crustify/agent.sh' \
      '# The two campaigns differ in one thing only: which orchestrator prompt they' \
      '# load. Everything else -- preflight, agent settings, task handling, exec -- is' \
      '# the same job, and was two scripts long enough for the translate path to lose' \
      '# --model and openrouter support without anyone noticing.' \
      'case "${CRUSTIFY_COMMAND:-}" in' \
      '    translate|audit) ;;' \
      '    "") echo "CRUSTIFY_COMMAND is unset: pass -e CRUSTIFY_COMMAND=translate or =audit" >&2' \
      '        exit 2 ;;' \
      '    *)  echo "bad CRUSTIFY_COMMAND: ${CRUSTIFY_COMMAND} (translate|audit)" >&2' \
      '        exit 2 ;;' \
      'esac' \
      '# The harness is baked into the image, so /opt/crustify is a mount only when' \
      '# testing live harness changes.' \
      '[ -f /opt/crustify/pyproject.toml ] || {' \
      '    echo "no crustify harness at /opt/crustify" >&2; exit 2; }' \
      '[ -e /target/.git ] || {' \
      '    echo "missing target checkout mount: bind an existing Git checkout at /target" >&2; exit 2; }' \
      'uv pip install --python /opt/venv -e /opt/crustify' \
      'if [ "$CRUSTIFY_COMMAND" = translate ]; then' \
      '    # The capability checkouts a translate run needs, and only it: an audit' \
      '    # touches neither. A mounted tree always wins, so a campaign runs against' \
      '    # whatever is under development; main is cloned only to fill a gap, and the' \
      '    # line says so, because a silent clone is how a run comes to differ from' \
      '    # the checkout it was believed to be testing.' \
      '    ensure_checkout() {' \
      '        path="$1"; marker="$2"; url="$3"' \
      '        if [ ! -f "$path/$marker" ]; then' \
      '            echo "no checkout at $path; cloning $url" >&2' \
      '            git clone --depth 1 "$url" "$path"' \
      '        fi' \
      '        [ -f "$path/$marker" ] || {' \
      '            echo "invalid checkout at $path: missing $marker" >&2; exit 2; }' \
      '    }' \
      '    ensure_checkout /opt/wavefront pyproject.toml https://github.com/crustify-rs/wavefront.git' \
      '    ensure_checkout /opt/ffibox Cargo.toml https://github.com/crustify-rs/ffibox.git' \
      '    # wavefront is a Python distribution and has to be installed to put its CLI' \
      '    # on PATH; ffibox is a path dependency the emitted crates point at, so a' \
      '    # checkout is all it needs.' \
      '    uv pip install --python /opt/venv -e /opt/wavefront' \
      'fi' \
      'crustify_resolve_agent' \
      '# Append a task only when the conventional external mount is present.' \
      'task=' \
      'if [ -f /campaign/TASK.md ]; then' \
      '    task=/campaign/TASK.md' \
      'fi' \
      '# ABLATION SWITCH. With CRUSTIFY_BARE=1 the harness contributes NOTHING to the' \
      '# prompt: no orchestrator role, no container context, no workset or instrument' \
      '# guidance, no artifact layout. The TASK file IS the whole prompt. That is the' \
      '# point -- it measures what the bare model finds on its own, against a full' \
      '# crustify run on the same target and budget.' \
      'if [ "${CRUSTIFY_BARE:-0}" = 1 ]; then' \
      '    [ -n "$task" ] || {' \
      '        echo "CRUSTIFY_BARE=1 needs a task at /campaign/TASK.md" >&2' \
      '        exit 2; }' \
      '    echo "[crustify] BARE: /campaign/TASK.md is the entire prompt"' \
      '    text="$(cat "$task")"' \
      '    crustify_exec_agent "$text" "$@"' \
      'fi' \
      '# The prompt is composed by the CLI now, not here: it reads its own prompt' \
      '# file, skill index, conventions and the campaign task, and puts them in a' \
      '# system slot this shell had no way to reach. What is left is the one thing' \
      '# only the container knows -- where the checkout is mounted.' \
      '[ -n "$task" ] || {' \
      '    echo "no /campaign/TASK.md: mount one, it is the campaign input" >&2' \
      '    exit 2; }' \
      'echo "[crustify] task $task"' \
      'exec crustify --model "$provider/$CRUSTIFY_MODEL" --billing "$CRUSTIFY_BILLING" \' \
      '    /target . orchestrate "$CRUSTIFY_COMMAND" --task "$task" "$@"' \
      > /usr/local/bin/crustify-orchestrator \
    && chmod +x /usr/local/bin/crustify-orchestrator

# The required target bind mount shadows this empty image directory. Starting
# in it makes the existing checkout -- and any partial campaign -- the
# orchestrator's unambiguous working repository.
WORKDIR /target
CMD ["crustify-orchestrator"]
