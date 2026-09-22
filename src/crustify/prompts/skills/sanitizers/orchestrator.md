---
name: sanitizers
description: >-
  Which instrumented C builds a campaign prepares, and why they are separate.
  ASan+UBSan is the general FFI and lifecycle build; TSan is a second build for
  race tests and must never be combined with ASan; BSan is a third when
  BorrowSanitizer is available; Miri needs no C build at all. Read before
  preparing the campaign's reusable builds.
---

# Sanitizer builds

One build per instrument, prepared once for the campaign, immutable and shared
so agents neither rebuild nor diverge.

- **ASan + UBSan** — the general build. FFI and lifecycle tests use it.
- **TSan** — a separate build, for race tests. Do not combine it with ASan:
  the two instrument the same memory operations and their runtimes conflict.
- **BSan** — a third build, when BorrowSanitizer is available.
- **Miri** — needs no C build, and cannot call the foreign library. It is not
  part of the build matrix; nothing is prepared for it.

Record each build's compiler and instrumentation alongside the `build.json`
version, because a translator reuses a build only when all of those match its
batch — and privately rebuilds when they do not, at campaign expense.
