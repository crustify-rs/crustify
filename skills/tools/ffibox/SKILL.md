---
name: ffibox
description: "ffibox, the Rust crate of primitives for sharing memory between Rust and C. You may use before holding C memory from Rust, handing Rust memory to C, writing an export or callback, or adding a primitive to ffibox. Extend it with the FFI primitives that recur in the work."
---

# ffibox

ffibox provides the primitives for sharing memory between Rust and C that standard Rust
lacks: owners and borrows of C objects, callbacks and function tables, and the memory Rust
hands to C. Its checkout is beside the codebase: read its `README.md`, and its `docs/`
wherever you need them, including `docs/goals.md` before you add a primitive.
