# Porting workflow

How a `port` campaign proceeds. It follows the [binding workflow](binding.md) throughout;
this document gives the principles a port follows and where it differs. How each item is
ported is [`../porting.md`](../porting.md).

## 1. Principles

### 1.1 Rust consumers

A port produces a Rust library for Rust-native applications. Its public API is the safe
Rust one; the installed C headers and the C ABI they describe are not kept for C
applications outside the target. A ported module's C-facing surface is only what the
target's own unported C still consumes, its `extern "C"` exports, and it shrinks as that C
is ported.

A type, public or internal, therefore keeps its C layout, and its `wrap`, only while
unported C of the target accesses that layout. The target's tests do not count, as
[Tests follow their modules](#12-tests-follow-their-modules) describes, and neither does a
definition in an installed header: the C consumers it would serve are outside the target.

### 1.2 Tests follow their modules

Each module carries the test files that exercise it, and they are ported and gated with
it: a module's C tests are built and run while the module is C, and disabled once it is
Rust, when their Rust ports run in their place. A test's access to a module's internals is
a use within that module, so it never keeps a type wrapped.

A test that exercises the internals of several modules is gated with each of them: it runs
while all of them are C, and its port runs once all of them are Rust. In between, each
ported module's own tests cover it.

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
module's exports, and go with the last C file that includes them. A `static inline`
function a header defines is internal API like any other function of its module: once the
module is ported, the header declares it, and the Rust module exports it under its bare
name.

The module's equivalence tests, which need the C, are retired with it; the behaviour they
established is kept by the module's unit tests and ported tests.

A ported module's items therefore reach the rest of its module natively from the start:
an edge within a module needs neither a `wrap` binding nor an export, only the edges that
leave it.

## 2. Batches

A port campaign's schedule mixes both kinds of batch, as [`../planning.md`](../planning.md)'s
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
feature, as the [conventions](../conventions.md)' Exports and Export features sections
describe, which stays off, so its bare-named exports never collide with the C the tests
link. Native Rust items carry mangled names and cannot collide with it.

The C stays until integration: the target's other C still calls the module's symbols, which
only the exports could define, and the module's equivalence tests and its cut cycles still
run through it.

Once the module's last wave has landed, it is integrated in one step: its export feature is
turned on, its Rust is linked into the target in place of its TU, through the target's
actual build system, the TU and the C tests gated with it are removed, and the target's
test suite runs over the hybrid as the integration regression gate. The shared variants are rebuilt once the integration
lands.

## 4. Scope

The unit of a port is a module: its scope is whole modules, the foundational ones
included. Porting a few named items without their module is not described.
