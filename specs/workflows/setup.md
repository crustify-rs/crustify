# Setup workflow

Every campaign, translation or audit, starts from the same setup: the tools its workflow
needs are installed, its artifact tree exists, the target is built in the variants its
tests run against, and the target's own tests have a recorded baseline. Setup is
cumulative like the rest of a campaign: a step whose results already exist is resumed from
them rather than redone.

Setup starts only once the campaign's settings are complete and its brief is approved;
before that, nothing in the repository changes.

## 1. Provisioning

Every dependency the campaign's workflow, its enabled skills and its target need is
installed: the toolchains, the target's build system, the system dependencies of the C and
C++ libraries it builds, and the instruments its sanitizers need. BorrowSanitizer, when it
is not installed, is built from source as its repository describes
(<https://github.com/borrowSanitizer/bsan>). Each instrument is verified by invoking it.

A target whose default configuration detects optional system libraries compiles what the
host provides: an installed development package can move a component from the target's
bundled sources to a system library, and so out of the campaign's scope. The packages
installed for the configuration are therefore part of it, and are recorded with the
builds.

## 2. Repository

A translation campaign works in a repository of its own, laid out as
[`versioning.md`](../versioning.md)'s Repositories section describes, and its tree as
[`layout.md`](../layout.md)'s Tree section describes: `<repo>-bindings` for a wrap
campaign, `<repo>-rs` for a port campaign. It is initialized with the source added under
`c/` as a submodule, at the revision the settings' `source` answer names: of the source
itself for a wrap campaign, which never changes it, and of the campaign's fork of it,
`<repo>-fork`, for a port campaign, whose integrations change it. The fork is the source's
history with its `main` branch at that revision and the source's own `main` mirrored as
`upstream/main`; until the first integration, the submodule may point at the source
itself. The safe crate's name is chosen with it, and its Rust tree is scaffolded
once the plan is complete. The repository is created under the `crustify-rs`
organization, which publishes it, once the user approves.

An audit works in the repository of the crate it reviews, and creates none.

## 3. Artifact tree

The campaign's artifact dir is `crustify/artifacts/`, laid out as
[`layout.md`](../layout.md) describes. When it already holds artifacts, the campaign is
being resumed, and continues from them and from its existing branches.

A new campaign gets:

- `crustify/.gitignore`, from [`templates/gitignore`](../../templates/gitignore);
- the working branch, `crustify/devel`, whose first commit holds `c/` and
  `crustify/CRUSTIFY.md`, and the shipping branch, `main`, at the commit that adds `c/`; and
- its dashboard, from its template, as [`accounting.md`](../accounting.md) describes,
  with the settings it records filled.

## 4. Builds

The target is built in the variants [`testing.md`](../testing.md)'s Builds section lists:
`plain`, `coverage`, and one per sanitizer the campaign enables, by default every one the
toolchain supports. A sanitizer without a variant is one no batch tests for or runs under.

Each variant is configured as the settings' `target-config` asks, by default the target's
default configuration with its deprecated features disabled. A build compiles only what
its configuration selects, so the files it leaves out are listed with the reason; a part
left out that is worth covering gets a variant of its own.

The variants are recorded in `crustify/artifacts/build.json`, from
[`templates/build.json`](../../templates/build.json): each an out-of-tree `dir` and the
`configure` and `build` commands run from it, with the file's `version` raised whenever a
command changes. They are built in parallel, and each is smoke-tested once built. The
shared variants are rebuilt after a landing changes the compiled target.

## 5. Baseline

The target's tests run on `plain`. A test that is unstable, or that needs infrastructure
the host does not provide, such as a network service or a test server, is disabled with
its reason. The dashboard records the baseline: passed out of total, the tests the suite
skipped by itself, and every disabled test. The campaign's final results must match it.

## 6. Preflight

Once the plan exists and before the first wave launches:

1. each selected model is resolved to its provider and backend;
2. the backend's executable is on the `PATH` of the process that spawns agents, and
   answers `--version`;
3. the credential variables its billing needs are set, checked without printing their
   values;
4. an unsupported combination of provider and billing is rejected;
5. a dummy batch is dry-run through the spawn command it would use; and
6. the plan's unit, wave and batch counts match the approved plan.
