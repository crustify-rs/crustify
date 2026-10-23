# TODO

Deferred decisions and follow-up work on the crustify contracts and prompts.

## 1. Side campaigns for out-of-tree dependencies

[`dependencies.md`](dependencies.md) now describes a side campaign: a wrap campaign of an
out-of-tree library's source in its own `<source>-bindings` repository, cloned beside the
parent's, continued by every campaign that uses the library, and advancing at the
parent's pace. The assistant's translate prompt runs them.

Open questions:

- **Concurrent parents.** How two campaigns that extend the same wrapper at once order
  their additions to its plan.

## 2. Ship `specs/` so a non-editable install keeps its conventions

The conventions and the how-tos (`specs/conventions.md`,
`specs/*.md`) resolve under `deps.CHECKOUT`, which is the source checkout.
A wheel install has no `specs/` there, so every agent runs without its conventions and
how-tos. Only the editable install the Dockerfile performs hides this.

Ship `specs/` as data-files to `share/crustify/`, the way Wavefront ships its schemas to
`share/wavefront/artifacts`, and resolve crustify's own skills there before the checkout.
`deps.share_dir()` already resolves that prefix.

This is also the prerequisite for moving `src/crustify/prompts/` into `specs/`: prompts
package correctly today only because they sit inside the package, and moving them before
the fix would lose them the same way.

## 3. Add an idiomaticity and ergonomics guide

Create `specs/idiomaticity.md` for Rust API-shaping hints and good practices. Keep
mandatory mechanical rules in `conventions.md`. Make the guide available through an
optional prompt skill so experiments can ablate it without changing the prompts.

## 4. Emit type-implementing symbols as inherent methods

A symbol whose first parameter is the type it operates on is currently emitted as a free
function (`conventions.md`, "Naming › Functions"). Emitting it as an inherent
method on that type instead would read better at call sites — `commit.message()` over
`git_commit_message(commit)` — and needs no restructuring, since inherent impls are
crate-scoped and the handle types are generated in the same module as their functions.

Measured over the 860 anchored free functions in `libgit2-wrap`, 629 take a wrapped handle
first and could convert:

| first parameter | count | method receiver | lifetime cost |
|---|---:|---|---|
| owned handle (`Foo`, `FooOwned`, `CBox<Foo>`) | 8 | `&self` / `&mut self` | none, elision applies |
| borrowed handle, returns no reference | 441 | `self` or `&mut self` | none |
| borrowed handle, returns a reference | 180 | `self` | must name `'a` |

Two findings decide whether this is worth doing:

- The elision win barely exists here. Rule 3 needs `&self`/`&mut self`, and only 8 of 629
  take an owned handle. The other 621 take copyable `FooRef`/`FooMut`, where a by-value
  `self` receiver does not elide at all (`E0106`).
- Taking `&self` on a borrowed handle to obtain elision is wrong: the returned reference
  binds to the handle's own storage rather than the C object, so it cannot outlive the
  caller's local (`E0515`). The 10 functions that take `&mut FooMut<'_>` *and* return a
  reference are the trap — as `&mut self` methods they compile at the definition and fail
  at the call site.

So the case rests on ergonomics, not on lifetime elision. If adopted, the rule belongs in
the translator prompt under "Functions and globals", with the `&self`-on-a-borrowed-handle
hazard stated explicitly, and the free-function clause in `conventions.md` relaxed
to defer the shape to the translator prompt.

Also open: whether existing waves get retrofitted, or the crate carries two generations of
shape side by side.

## 5. Enforce FFI lending windows with ARM MTE

`FooRef<'a>` and `FooMut<'a>` assert that foreign code will not retain the pointer past
`'a`. Nothing checks that today: it is an assumption the translator records in the
ownership store and no instrument validates. ARM's Memory Tagging Extension (v8.5) could
enforce it in hardware, tagging each lending window and faulting when C touches the object
outside it.

The appeal over BorrowSanitizer is reach. BSan's scope is "executed Rust and
LLVM-supported foreign code" — it needs IR for the C. MTE checks in the core, so prebuilt
shared objects, hand-written assembly and anything else that issues a load is covered with
no instrumentation of the foreign side.

### 5.1 What it cannot do

MTE compares a pointer's tag against the granule's tag and faults on mismatch. The check
is **symmetric across loads and stores**, so it expresses *identity*, not *permission*.
Tree Borrows is a permission discipline, so the canonical BSan finding — C writes through
a pointer while a Rust `&T` is live — is invisible: matching tags, passing write.
Instrumenting the C's stores to fix that would require exactly the IR access MTE was
chosen to avoid.

Three further limits: 4 bits of tag cannot hold a tree, so nested reborrows (`f(&mut *x)`,
pervasive and legal) are indistinguishable from conflicting ones; the 16-byte granule
cannot separate two fields of a C-allocated struct, and padding is unavailable because the
layout is the ABI contract; and retagging per borrow — rather than per allocation as
HWASan does — gives borrows observable memory side effects on a very hot path, on every
unwind path included.

So MTE is a candidate to replace ASan for FFI-crossing memory-safety classes, not BSan for
aliasing classes.

### 5.2 The part worth building

Retention: foreign code using a pointer after its lending window closed. No current
instrument covers it well — the memory is still live, so ASan sees nothing — and it is
exactly what the borrowed-handle lifetimes claim.

Use a **fresh random tag per lending window**, not a fixed Rust/C tag pair. Two tag values
is the degenerate case: a stale foreign pointer then matches every subsequent open window,
so the most likely moment of misuse is never caught. With a fresh tag per window, a
pointer stashed during window `i` aliases window `i+1` with p = 1/16.

Object granularity, not field granularity — which suits opaque handle types like
`git_commit`, where the whole object is lent anyway.

### 5.3 Why it is worth a paper paragraph

The miss rate is **computable**: a violation occurring `n` times is detected with
probability at least `1 - 16^-n`. That makes MTE the only dynamic instrument here with a
quantified soundness gap. "The sanitizers ran clean at 37.2% branch coverage" carries no
false-negative bound at all; this does.

It remains a falsifier — sound for positives, unsound for absence — so it cannot support a
verification claim, only a sharper falsification one.

### 5.4 Blockers

No MTE on the current machine: `/proc/cpuinfo` lists `bti paca pacg` but no `mte`. Needs
v8.5 silicon or a model. Use synchronous tag-check mode for testing; async batches faults
and loses the faulting site. HWASan is the software fallback at 1/256 rather than 1/16,
but it needs the C instrumented, which forfeits the reach advantage.

## 6. Port individual items without their module

A port campaign's scope is whole modules
([`workflows/porting.md`](workflows/porting.md)'s Scope section). A campaign that ports
only a few named types or symbols, and leaves the rest of their module in C, has no
workflow yet.

Open questions:

- how such a scope maps to a plan: whether its items are scheduled inside the module
  that owns them, or as a module of their own;
- how the module's remaining C reaches them, and for how long; and
- whether the module's tests that reach those items are migrated, as a ported
  module's are, or only added.

## 7. Module parallelization

Modules run one at a time, in the order `modules.json` computes
([`artifacts/modules.md`](artifacts/modules.md)'s Execution order section), although a
module is one translation unit and many hold only a few items: most of their waves are
small, and modules that do not depend on one another could run at once. Module
parallelization would run independent modules' waves concurrently, with the user's
approval.

Open questions:

- whether parallel modules share one wave, its batches drawn from several modules, or keep
  their own waves running side by side, and so whether `module` stays a wave field or moves
  to the batch;
- how the user approves it: once per campaign as a setting, or per group of modules; and
- how each module's base, the settings it ran under and its accounting are recorded when
  its waves no longer start from a commit of their own.
