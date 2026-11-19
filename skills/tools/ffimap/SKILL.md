---
name: ffimap
description: "ffimap, which counts a Rust crate's unsafe and FFI surface and measures its consumer-facing API, and where its documentation covers each use. Read before measuring the unsafe surface for .crustify/STATUS.md or the report, or when looking for unsafe code to review."
---

# ffimap

ffimap scans a Rust crate and reports deterministic counts, and their sites, of what it
leaves unsafe and how it meets C: unsafe blocks, lines and functions, raw pointers in its
API, its exports and its use of ffibox, crate-wide and per module. Start from its `--help`,
then read the document for the use at hand:

| use | document |
|---|---|
| what each counter holds, and how to read a scan | `docs/schema.md` |
| how each counter is decided | `docs/analysis.md` |
| the counters `--ffibox` adds | `docs/ffibox.md` |
| the consumer-facing API of each C item, with `ffimap api` | `docs/api.md` |
| what ffimap measures, and why | `docs/goals.md` |

Uses in a port: the unsafe surface for `.crustify/STATUS.md` and the report, with
`code.loc.unsafe` over `code.loc.total` for the share; `--sites` to locate unsafe code and
raw pointers for a review. Scan the library alone: a dev-dependency that enables
test-only features makes the crate's internals count as public.
