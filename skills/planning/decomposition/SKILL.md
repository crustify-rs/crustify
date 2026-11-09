---
name: decomposition
description: "How the target's build becomes modules.json: planner runs, modules, bundling of headers and tests, dependencies, objectives, foundational modules. Read before decomposing or re-deriving a plan."
---

# Decomposition

Decomposition turns the target's build into the campaign's modules, recorded in
`crustify/artifacts/modules.json`: what each module holds, its tests, its objective, the
Rust that could replace it, and what it depends on. The waves and batches that execute
them are [scheduling](../scheduling/SKILL.md)'s; together they are the campaign's plan, with the
planning artifacts of the tools it uses.

A plan is bounded by the campaign's settings in `crustify/CRUSTIFY.md`: its `campaign`
(port or wrap), `scope` and `target-config` answers. A feature the target is configured
without is out of scope. The plan derives from the builds recorded in
`crustify/artifacts/build.json` and the linker outputs of those builds; planning changes
neither the build nor the Rust tree.

## 1. Runs

A campaign is planned by one or more planner runs, one after another, each in one commit
on its own branch, `crustify/planner/run-<n>`, forked from the working branch's tip and
checked out in the repository's base dir. Once the run has committed, the working branch
is fast-forwarded to it, and the next run forks from there. Each run brings the committed
plan up to date, so a later run checks what the earlier ones decided, and re-derives under
the current rules what a rule that has changed since decided, and the branch history
records every planning decision and its revisions.

A campaign may be planned in several sessions, each for part of its scope: a few modules,
a few of their waves, or a few named items. Each session's runs add what its scope adds to
the same plan: modules and link units with the next free indices, and the `todo` waves
numbered after the highest index of a started wave. What is frozen, or has started, is kept as
[`modules-schema`](../../artifacts/modules-schema/SKILL.md) and
[`schedule-schema`](../../artifacts/schedule-schema/SKILL.md) describe. A run that corrects an earlier decision files a report on it, as
[`reviewing`](../../verification/reviewing/SKILL.md#9-plan-corrections) describes.

## 2. Modules

`modules.json` follows [`modules-schema`](../../artifacts/modules-schema/SKILL.md); its layout example
is [`templates/modules.json`](../../../templates/modules.json).

The C codebase is the decomposition's spec. A module is one translation unit with the
headers it defines its items in, so that the plan follows how the codebase is organized
rather than a judgement of how it should be, and the Rust tree mirrors it, as the
[conventions](../../rust/conventions/SKILL.md)' Crates, modules, and TUs section describes. Dependencies
between modules are what the C has: the decomposition does not group files to hide them.

Link units are identified from the actual linker outputs. The decomposition covers the
selected target and its complete imported producer closure: every translation unit the
build compiles in scope is a module's, or is listed as configured out.

## 3. Bundling

Each translation unit is bundled with the headers that carry its name, internal or
installed: `src/libgit2/repository.c` with `src/libgit2/repository.h`,
`include/git2/repository.h` and `include/git2/sys/repository.h`. An item of such a header
that belongs to another TU, in the rare case one does, is homed with that TU.

A shared header, one that carries no single TU's name, is split item by item:

- a type goes to the TU that implements its lifecycle and its functionality, an enum to
  the TU whose functions produce or consume its values;
- a global goes to the TU that implements its logic;
- a function pointer a typedef declares goes to the TU whose functions call it or take it,
  one written inline with the item whose declaration holds it, and a typedef of its own to
  the TU whose functions use it; and
- a `static inline` function or a macro goes to the module whose logic it implements, as
  the functions it calls and the types it accesses show.

A header that implements what no TU does, and so has no TU to go to, is a header module of
its own. Each split is recorded with the file entries' `items` lists, which stay empty for
a file a module owns whole. A macro is an entity of the module that owns the file defining
it when it is API: a constant, a symbol alias, a type generator or logic. Include guards,
configuration and feature-test macros and attribute macros are not: they are neither
homed nor translated.

A module also lists its tests: the test files tied to it, those whose subject it is. A
test's subject is each module whose internals it uses, the fields or the layout of the
types it owns and its static functions and static globals, and each module whose own
results or effects its assertions check. A test's uses are what its own code does, macro
expansions included. A module the test only calls to set up or tear down its fixtures, or
whose enums it only uses, their constants and values alike, is no subject of it: the test
is not tied to that module, and keeps running after the module's integration, through its
exports. A test file whose subject is several modules is listed by each of them. A test
file whose tests divide between modules is split with its entries' `items` lists, by test
function.

## 4. Dependencies

Each module's dependency edges are found from the files it holds and the items it owns. The edges from a module to another are one record
of its `depends_on`, with its `outgoing_edges`, its `incoming_edges` and the item kinds
consumed across them, and each out-of-tree library it uses is one record of its own, which
names the library and counts what the module consumes from it. What holds for the library
as a whole, the release the target links, its source and the crates that port or bind it
with their feature parity, is recorded once, in `dependencies.json`, as
[`dependencies-schema`](../../artifacts/dependencies-schema/SKILL.md) describes. The records keep the
graph as it is,
cycles included, split as [scheduling](../scheduling/SKILL.md)'s Order section describes.

## 5. Objectives

Each module carries one objective, which the settings' `campaign` answer sets:

- in a port campaign, every module is `port`: it is reimplemented in safe Rust. The
  foundational modules are the exception, `wrap` in every campaign, as
  [Foundational modules](#6-foundational-modules) describes; and
- in a wrap campaign, every module is `wrap`: its C is kept behind a safe Rust API.

A TU is not split for its objective.

A module's `rust_equivalent`, and a link unit's, record what Rust already provides in its
place, taken as a whole: the closest the Rust standard library comes to it, and the
established crates that could replace it outright, in descending order of feature parity.
Each carries its feature parity and notes on what is missing or differs, and each crate is
checked for its semantics, platform support, performance and licensing. A port builds on
them where they serve: a standard-library operation that is equivalent is used directly, as
[`porting`](../../rust/porting/SKILL.md)'s FFI boundary section describes.

## 6. Foundational modules

The foundational modules are those whose items every other module may depend on: the
TUs that define the allocators, releasers, disposers and cloners of type-erased memory,
and those whose text pointers, the pointers that refer to NUL-terminated strings, depend
on nothing but the type-erased ones. A codebase may have several of each, wherever its
lifecycle routines are defined.

Their members are selected from the dependency graph with each type-erased value resolved
to the types it is read as, so that a `void *` read as a named type is a dependency on that
type, not an erased value. What stays erased is a candidate, admitted only once its body
has been read. A foundational module depends only on other foundational modules, apart
from a few dependencies such as logging or assertions on its failure paths, which the
order cuts. The order then runs them first, and among them the type-erased ones before the
string ones that call them.

A TU whose items all meet that test is foundational whole. One that also holds items that
depend on other modules is split in two: its foundational module lists the TU with the
lifecycle routines and what they need within it as `included`, and the other module
lists the same items as `excluded`. The two share the TU's path as their name, and are
told apart by their `index` and `foundational`. Both home in the TU's Rust file.

Each member's lifecycle role (allocator or constructor, releaser, disposer, cloner) is
established while planning, so that the foundational modules' members are bound as
strategies, as [Lifecycle strategies](../../rust/binding/SKILL.md#35-lifecycle-strategies) describes. The
foundational modules are planned and scheduled like any other: waves of batches of units.
They are `wrap` in every campaign: their members become the lifecycle strategies that the
other modules' bindings release through, and while any C remains it allocates and frees
through them.
