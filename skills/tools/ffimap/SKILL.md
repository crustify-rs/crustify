---
name: ffimap
description: "ffimap, which counts a Rust crate's unsafe and FFI surface and measures its consumer-facing API. Read before measuring the unsafe surface for .crustify/STATUS.md or the report, or when looking for unsafe code to review."
---

# ffimap

ffimap scans a Rust crate and reports deterministic counts, and their sites, of what it
leaves unsafe and how it meets C: unsafe blocks, lines and functions, raw pointers in its
API, its exports and its use of ffibox, crate-wide and per module. Read its `--help`, and
its `docs/` wherever you need them. Scan the library alone: a dev-dependency that enables
test-only features makes the crate's internals count as public.
