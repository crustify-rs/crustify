---
name: ffibox
description: "ffibox, the Rust crate of primitives for sharing memory between Rust and C, and where its documentation covers each use. Read before holding C memory from Rust, handing Rust memory to C, writing an export or callback, or adding a primitive to ffibox."
---

# ffibox

ffibox provides the primitives for sharing memory between Rust and C that standard Rust
lacks: owners and borrows of C objects, callbacks and function tables, and the memory Rust
hands to C. Its checkout is beside the codebase. Start from its `README.md`, then read the
document for the use at hand:

| use | document |
|---|---|
| owning a C object, and choosing the owner for its shape | `docs/ownership.md` |
| borrowing an object C or a parent releases | `docs/borrows.md` |
| a C API's recurring patterns as Rust traits and idioms: iteration, status codes, … | `docs/patterns.md` |
| function pointers and tables C calls into | `docs/vtables.md` |
| memory Rust owns and C holds, calls or reads, such as exports | `docs/outbound.md` |
| what the primitives cannot express, written by hand | `docs/hand-written.md` |
| worked examples | `docs/examples.md` |
| what each primitive guarantees, and what a new one must meet | `docs/goals.md` |

The prompt's Grow ffibox section says when to add a primitive; `docs/goals.md` says what it
must meet before it is added.
