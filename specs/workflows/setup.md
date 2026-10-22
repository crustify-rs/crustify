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

## 2. Artifact tree

The campaign's artifact dir is `crustify/artifacts/`, laid out as
[`layout.md`](../layout.md) describes. When it already holds artifacts, the campaign is
being resumed, and continues from them and from its existing branches.

A new campaign gets:

- `crustify/.gitignore`, from [`templates/gitignore`](../../templates/gitignore);
- the working branch, `crustify/devel`, whose first commit holds `crustify/CRUSTIFY.md`,
  and the shipping branch, `crustify/main`, at the repository's revision; and
- its dashboard, from its template, as [`accounting.md`](../accounting.md) describes,
  with the settings it records filled.

## 3. Builds

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

## 4. Baseline

The target's tests run on `plain`. A test that is unstable, or that needs infrastructure
the host does not provide, such as a network service or a test server, is disabled with
its reason. The dashboard records the baseline: passed out of total, the tests the suite
skipped by itself, and every disabled test. The campaign's final results must match it.

## 5. Preflight

Once the plan exists and before the first wave launches:

1. each selected model is resolved to its provider and backend;
2. the backend's executable is on the `PATH` of the process that spawns agents, and
   answers `--version`;
3. the credential variables its billing needs are set, checked without printing their
   values;
4. an unsupported combination of provider and billing is rejected;
5. a dummy batch is dry-run through the spawn command it would use; and
6. the plan's unit, wave and batch counts match the approved plan.
