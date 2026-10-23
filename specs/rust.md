# Rust

How the Rust a campaign generates is built, linted and formatted: its toolchains, its
edition, the lints every crate inherits and how it is formatted. What the code is named and
where it sits is [`conventions.md`](conventions.md)'s; these are the rules the toolchain
enforces on it.

## 1. Toolchains

The workspace builds and tests on stable Rust, pinned in `rust-toolchain.toml` to the
stable release current when the repository is created, with the `clippy` and `rustfmt`
components. Miri, BorrowSanitizer's `bsan` toolchain aside, and the formatter's unstable
options need nightly: a nightly pinned by date, recorded in the workspace manifest as
`[workspace.metadata.crustify] nightly = "nightly-<date>"`, and named explicitly wherever it
runs, as `cargo +nightly-<date> …`. A toolchain is moved forward only between waves, in a
commit of its own.

## 2. Edition and manifests

Every crate uses Rust edition 2024, with the workspace's `rust-version` set to the pinned
stable release. The shared package fields (`edition`, `rust-version`, `license`,
`repository`) are declared once, in `[workspace.package]`, and inherited. Every crate but
the generated `-sys` crates inherits the workspace's lints with `[lints] workspace = true`.

## 3. Lints

The workspace declares its lints in `[workspace.lints.rust]` and `[workspace.lints.clippy]`.
Every gate runs with warnings denied, so a lint at `warn` fails a landing as surely as one
at `deny`; `deny` marks the lints no item may opt out of.

### 3.1 rustc

| lint | level | why |
|---|---|---|
| `nonstandard_style` (`non_snake_case`, `non_camel_case_types`, `non_upper_case_globals`) | `deny` | the naming the conventions' Naming section gives: `snake_case` functions, methods, modules and variables, `UpperCamelCase` types and traits, `SCREAMING_SNAKE_CASE` constants and statics |
| `unsafe_op_in_unsafe_fn` | `deny` | each unsafe operation in an `unsafe fn` sits in its own justified `unsafe` block |
| `missing_docs` | `warn` | every public item carries its anchor, which is a doc comment |
| `rust_2018_idioms` | `warn` | elided lifetimes in paths and other pre-2018 idioms |
| `unreachable_pub`, `unused_qualifications`, `unused_lifetimes`, `let_underscore_drop`, `trivial_casts`, `trivial_numeric_casts` | `warn` | visibility the crate does not need, and casts and drops that hide intent at the foreign boundary |

### 3.2 Clippy

| lints | level | why |
|---|---|---|
| `clippy::correctness` | `deny` | code that is outright wrong |
| `clippy::all` (`suspicious`, `style`, `complexity`, `perf`), `clippy::pedantic`, `clippy::cargo` | `warn` | as much of Clippy's stable guidance as applies; `nursery` is left out, its lints still being unsettled |
| `undocumented_unsafe_blocks`, `multiple_unsafe_ops_per_block`, `missing_safety_doc`, `unnecessary_safety_comment`, `unnecessary_safety_doc` | `deny` | every `unsafe` block is one justified operation, and every safety comment and `# Safety` section is where it belongs |
| `mem_forget`, `allow_attributes`, `allow_attributes_without_reason` | `deny` | no leak by `mem::forget`, and every exception an `#[expect]` with a reason |
| `module_inception` | `allow` | a C directory often holds a TU of its own name, so the mirrored tree nests a module in one of its name |
| `module_name_repetitions` | `allow` | items keep their C-derived names where their module, mirrored from the C path, repeats them |
| `multiple_crate_versions` | `allow` | the dependency graph is not the campaign's to dedupe |

An item that needs an exception takes it locally, as
`#[expect(<lint>, reason = "<why>")]`, never as a crate-wide `allow`: the expectation fails
once the exception is no longer needed.

### 3.3 Generated code

The `-sys` crates' bindgen output follows C's names and shapes, so those crates do not
inherit the workspace's lints: their `lib.rs` allows `nonstandard_style`, `missing_docs`,
`clippy::all` and `clippy::pedantic` over the generated module, and the formatter skips
it. Their hand-written parts, such as `build.rs` and macro shims, follow the rest of this
spec.

## 4. Formatting

Every crate is formatted by `rustfmt`, configured once in the workspace's `rustfmt.toml`:

| option | value |
|---|---|
| `edition`, `style_edition` | `"2024"` |
| `max_width`, `comment_width` | `100` |
| `newline_style` | `"Unix"` |
| `use_field_init_shorthand`, `use_try_shorthand` | `true` |
| `imports_granularity` | `"Module"` |
| `group_imports` | `"StdExternalCrate"` |
| `wrap_comments`, `normalize_comments`, `normalize_doc_attributes` | `true` |
| `format_code_in_doc_comments`, `format_macro_matchers` | `true` |
| `hex_literal_case` | `"Upper"` |
| `reorder_impl_items` | `true` |

The options from `imports_granularity` down are unstable, so the formatter runs on the
pinned nightly, as `cargo +nightly-<date> fmt --all`. A landing's tree is formatted; the
gate checks it with `--check`.

## 5. Unsafe code

Every unsafe block carries a specific, falsifiable `// SAFETY:` comment: the invariant the
operation relies on, and why it holds on every path that reaches it. Native Rust APIs are
safe unless their caller obligation cannot be expressed in the type system; an `unsafe fn`
documents that obligation in its `# Safety` section.
