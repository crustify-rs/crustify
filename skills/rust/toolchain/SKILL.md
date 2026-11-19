---
name: toolchain
description: "The Rust edition and the lints of the port's workspace. Read before scaffolding the workspace or when a lint question comes up."
---

# Toolchain

Every crate uses the latest Rust edition, and is formatted by `rustfmt`.

The workspace enables these lints, and every gate runs with warnings denied:

- rustc:
  - `nonstandard_style`
  - `unsafe_code`
  - `unsafe_op_in_unsafe_fn`
  - `missing_docs`
  - `rust_2018_idioms`
  - `unreachable_pub`
  - `unused_qualifications`
  - `unused_lifetimes`
  - `let_underscore_drop`
  - `trivial_casts`
  - `trivial_numeric_casts`
- Clippy:
  - `clippy::correctness`
  - `clippy::all`
  - `clippy::pedantic`
  - `clippy::cargo`
  - `clippy::undocumented_unsafe_blocks`
  - `clippy::multiple_unsafe_ops_per_block`
  - `clippy::missing_safety_doc`
  - `clippy::unnecessary_safety_comment`
  - `clippy::unnecessary_safety_doc`
  - `clippy::mem_forget`
  - `clippy::allow_attributes`
  - `clippy::allow_attributes_without_reason`
