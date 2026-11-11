---
name: porting-workflow
description: "The principles a port campaign follows and where it differs from binding: Rust consumers, tests tied to modules, one language per module, integration builds. Read before porting a module or integrating one."
---

# Porting workflow

How a `port` campaign proceeds. It follows the [binding workflow](../binding-workflow/SKILL.md) throughout;
this document gives the principles a port follows and where it differs. How each item is
ported is [`porting`](../../rust/porting/SKILL.md).

## 1. Principles

### 1.1 Rust consumers

A port produces a Rust library for Rust-native applications. Its public API is the safe
Rust one; the installed C headers and the C ABI they describe are not kept for C
applications outside the target. The crate bundles the C that remains, as
[`bindgen`](../../rust/bindgen/SKILL.md) describes, so that a consumer has the whole
library and reaches what is not ported yet through its raw bindings.

A ported module's C-facing surface is only what the target's own remaining C still
consumes, its translation units, tests and executables alike: its `extern "C"` exports,
under their bare C names, through which that C calls the Rust that replaced the module. The
remaining C depends on the Rust, never the Rust on a C copy of a ported module, so that
each function has one implementation and each global one copy. The surface shrinks as that
C is ported.

A type, public or internal, therefore keeps its C layout, and its `wrap`, only while
unported C of the target accesses that layout. The target's tests do not count, as
[Tests follow their modules](#12-tests-follow-their-modules) describes, and neither does a
definition in an installed header: the C consumers it would serve are outside the target.

### 1.2 Tests follow their modules

Each module carries the C tests tied to it, those whose subject it is, as
[`decomposition`](../../planning/decomposition/SKILL.md)'s Bundling section describes.
They assert the C contract, which a safe Rust implementation may change. Those that reach
the module's internals run while it is C and leave with it at its integration. Those that
use only its public API stay, and check its exports, which keep that contract for the C
that calls them, until their `port/unexport`, which they do not hold back, as the
[conventions](../../rust/conventions/SKILL.md)' Exports section describes. The tests its
port batches write mirror their regression cases, as
[`testing`](../../verification/testing/SKILL.md)'s C tests carried over section describes. A
test's access to a module's internals is a use within that module, so it never keeps a type
wrapped.

A C test that only calls a module, to set up or tear down its fixtures, is not tied to it:
once the module is integrated, the test reaches it through its exports, so that it checks
its own subject with the ported Rust under it, as part of the integration regression gate.

A test whose subject is several modules is tied to each of them, and leaves at the first
point at which it would leave as a test of one of them alone. Each ported module's own
tests cover it from then on.

### 1.3 One language per module

A module is in one language at a time. The campaign maintains C and Rust side by side, but
on disjoint modules, never the same code in both.

While a module's waves run, its C is the reference its ports are tested against, and the
target is built and linked from C alone. Once its last wave has landed, the module is
integrated, as [Builds](#3-builds) describes: the Rust module replaces the TU in the
target's link, its C is removed from the build and from the tree, and its tests switch
with it. The removal is made on the working branch; the shipping branch keeps the C until
the user approves shipping the module.

The headers bundled with the module stay while remaining C includes them, declaring the
module's exports, its `static inline` functions included, as
[`porting-symbols`](../../rust/porting/symbols/SKILL.md)'s Static inline functions section describes, and go with the last C
file that includes them.

The module's equivalence tests, which need the C, are retired with it, and the behaviour
they established is kept by its unit tests. The raw bindings of its
exported functions and globals then reach its exports, so that a consumer's raw calls keep
working, and an allowlist entry goes with the export it reaches. Those of its functions and
globals that have no export, which only its own C referenced, are removed with their
allowlist entries at the integration.

A ported module's items therefore reach the rest of its module natively from the start:
an edge within a module needs neither a `wrap` binding nor an export, only the edges that
leave it.

## 2. Batches

A port campaign's schedule mixes both kinds of batch, as [`scheduling`](../../planning/scheduling/SKILL.md)'s
Waves and batches section describes: a selected symbol is `port` from the start, a
selected type is `wrap` while another module's unported C depends on its layout and `port`
once none does, and a dependency outside the selected migration set stays `wrap`. A type
whose layout only its own module and tests use is `port` from the start. Each batch runs
the agent its objective names, in the same waves.

## 3. Builds

A module's waves do not change the compiled target. Its `port` batches add Rust that is
built and tested on its own, against the target's C build, which still compiles the
module's C and links no Rust: there is no build switch, and no batch flips one. The
module's `ffi_export` gateway is written with its items but compiled only under its export
feature, as the [conventions](../../rust/conventions/SKILL.md)' Exports and Export features sections
describe, which stays off, so its bare-named exports never collide with the C the tests
link. Native Rust items carry mangled names and cannot collide with it.

The C stays until integration: the target's other C still calls the module's symbols, which
only the exports could define, and the module's equivalence tests and its cut cycles still
run through it.

Once the module's last wave has landed, it is integrated in one step, with concurrent
modules as part of its branch's integration into the working branch, as
[`versioning`](../../operations/versioning/SKILL.md)'s Integration section
describes: its export feature is deleted, so that its gateway compiles from then on, its TU
and the C tests tied to it that reach its internals are removed from `c/`, and the
remaining C reaches the module through its exports. The C side of the
step is a commit on the fork's `main`, as
[`versioning`](../../operations/versioning/SKILL.md)'s Repositories section
describes, and the campaign's commit records the submodule at it: integrations run one at a
time, so the two repositories move together. The shared variants are rebuilt from the C
that remains once the integration lands.

From then on, the C that remains is linked in two ways, and no process holds a module both
as C and as Rust, nor its Rust twice:

- a Rust consumer, the campaign's own tests included, links the safe crate and the C that
  remains, which the crate bundles, statically or as shared libraries, as the raw bindings'
  Build modes describe; and
- the target's remaining C consumers, its C tests and executables, link the C that remains
  and the safe crate's Rust static library, built in campaign mode so that it carries no C
  of its own, through the target's actual build system.

The C tests that remain run over that second link as the integration regression gate, as
[`testing-gates`](../../verification/testing/gates/SKILL.md)'s Regressions section describes.

## 4. Scope

The unit of a port is a module: its scope is whole modules, the foundational ones
included, which stay `wrap`, as
[`decomposition`](../../planning/decomposition/SKILL.md)'s Foundational modules section
describes. Porting a few named items without their module is not described.
