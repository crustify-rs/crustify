---
name: bindings
description: >-
  How Crustify generates safe Rust over C: analysing each item's ownership,
  access and lifetimes, macros, the safe boundary, and the type and symbol
  routes (layouts, lifecycles, field accessors, functions, globals,
  callbacks, raw lifetime strategies, and porting) for the wrap and port
  objectives.
---

# Generating safe bindings

How to turn a scheduled C item into safe Rust. The conventions say what the result looks
like; this says how to arrive at it. `wrap` keeps the C implementation behind a safe Rust
API; `port` reimplements it in safe Rust.

## Item analysis

For each item, read its source code declarations and definitions, dependency closure,
callers, field touchers, and existing Rust consumers. For every pointer field, argument,
and return, inspect all code paths that store, transfer, clone, retain, or free it.

Establish:

- ownership and transfer direction;
- shared or mutable access;
- nullability;
- scalar, array, or other cardinality;
- type erasure and known element types;
- borrow and keepalive relationships; and
- construction, clone, and destruction paths.

Observed behaviour overrides names and comments. Preserve known distinctions in Rust
instead of copying an ambiguous C signature. Leverage these findings later when emitting
safe bindings.

## Macros

Do not publish a C macro as an independent Rust API.

- Symbol alias: bind and call the underlying symbol's safe wrapper.
- Function-like macro: use an existing shim or add the smallest required shim, then bind
  and wrap it.
- Constant macro: use the generated binding.
- Type-generating macro: follow the type route.

## Safe boundary

Preserve any ABI or layout still observed by C. Imported entities remain C-owned. Ported
storage becomes Rust-owned only after no C path accesses, allocates, or frees it.

Rust consumers use safe APIs. Restrict raw operations to:

- wrapped-layout projection;
- wrapped FFI calls;
- operations whose caller obligation cannot be represented in Rust types.

Keep SCC cuts and unavailable higher-layer dependencies as narrow documented raw seams.
Replace them when a safe dependency becomes available. Every unsafe block requires the
safety comment the conventions specifies.

---

## Type route

### Surface

For `wrap`, only include fields and lifecycle primitives published by the public API. For
`port`, include fields touched by targeted symbols and every lifecycle primitive. Identify
releasers, field disposers, cloners, constructors, casts, and pointer-field semantics
before selecting a representation.

### Safe layout

For `objective: wrap`, emit a safe layout over the raw type and its handles according to
the conventions.

For a synthetic type generator:

- use a generic wrapper for a homogeneous family converging on the generator;
- alias a dominant concrete instance to the generator with its element wrapper; and
- specialize only behaviour that differs from the generic surface.

### Lifecycle

Implement every ownership variant supported by the analysis findings. Prefer stateless,
layout-compatible, statically selected lifecycle and clone strategies when state is recoverable
from the object. Carry runtime state only when construction, destruction or cloning needs external
data.

Bind a type's constructor and init routines with its lifecycle policy so that it can be
exported as a safe function that returns the fully-formed object, where possible. Keep an
argument whose type is not yet wrapped as a narrow documented raw seam, which the run
wrapping that type replaces.

Keep C lifecycle primitives while C can allocate or free the storage. If Rust fully owns
allocation and destruction, use native Rust lifecycle operations.

Promoting construction-phase storage into an owner is unsafe; aim to encapsulate it in the
type's safe constructor, so consumers of the public API don't have to call `assume_init`
in unsafe blocks.

Lifecycle routines are also scheduled as free symbols; the symbol route skips those a type
run already emitted.

### Field accessors

Derive each accessor from ownership, mutability, nullability, cardinality, and lifetime
findings. Tie every pointer-derived result to the state that keeps it alive.

Project fields with `addr_of!`, `addr_of_mut!`, `&raw const`, or `&raw mut`. Never use
`&(*p).field` or `&mut (*p).field`. Follow the conventions for access.

Accessor requirements:

- Owned-reference field: replacement setter that drops the old owner, owning getter that
  leaves the field valid, and shared borrowed getter.
- By-value wrapped field: shared or mutable handle over the projected place.
- Stored borrow without an expressible lifetime: unsafe setter with the referent-lifetime
  obligation in its caller contract.
- Statically known owned and borrowed cases: distinct wrapper forms with a shared trait
  where useful.
- Runtime ownership flag: separately checked owned and borrowed operations.
- Union and discriminator: tagged Rust enum when the mapping is valid.
- Scalar and array variants: separate typed forms.
- Type-erased field: generic element type when known; otherwise the discovered untyped
  lifetime strategy.
- `Send` or `Sync`: add only with a specific synchronization or immutability proof.

Use safe wrappers for translated dependent types and callbacks. Find real release
strategies for strings, arrays, and erased owners. Replace lower-layer temporary raw
references made obsolete by this wrapper (cut SCCs). Keep a documented raw gap only for an
unavailable higher-layer dependency.

If an inline function-pointer helper lacks an ownership-compatible wrapper, emit one with
the type.

### Porting layout and storage

For `objective: port`, port layout only after every C-side field toucher is gone and no
public C consumer receives the concrete body. A public forward declaration alone does not
block opacification.

Port storage only after no C path allocates or frees it. If C still owns either operation,
retain compatible storage and report the blocker.

---

## Symbol route

### Functions

Emit `pub fn`; use `pub unsafe fn` only when no safe type-level contract can express the
caller obligation. Use typed wrappers for arguments and returns and reconstruct raw
pointers at the FFI call only, in a small documented unsafe block.

Separate moved (exclusively or refcounted), borrowed (immutably or mutably), nullable, scalar and array variants when one signature cannot
express all valid contracts. Prefer generics for methods that take/return type-erased arguments.

Prefer stateless ownership. Carry runtime state only when destruction or cloning requires it.

Bind a method to the type that it implements by emiting it in a `impl T` block on the type;
it takes `&self` or `&mut self` as its first argument. Keep free functions free.

For `wrap`, the ultimate goal is to avoid any unsafe or raw pointer on the exposed public interface,
and keep any raw or unsafe logic internal. Thus, use safe translated dependencies throughout.
Keep a documented raw pointer only for an unavailable higher-layer wrapper.
Update lower-layer raw surfaces when the new safe contract replaces them.

Use a standard-library operation directly when it is equivalent and no C-interoperability
requirement remains.

Lifecycle primitives for typed, type-erased or string handles might have been scheduled in a
worklist, although they implement release/clone/construct strategies/policies emitted in a
previous run; if so do not emit wrappers for them again.

### Globals

Wrap a global as a `'static` borrow, never as an owner. Derive its access discipline from every C access:

- immutable after initialization: a shared handle;
- synchronized by C: the matching safe synchronization (an atomic, or guards handing out
  the shared or exclusive handle under the lock), never discarding a lock's status;
- otherwise mutable: `unsafe` accessors that exclude concurrent access; report it;
- thread-local: a handle borrowed for a closure on the current thread, neither `Send` nor
  `Sync`.

A lock counts only if every access takes it and it rejects same-thread re-entry. While C
consumers reference the symbol, keep its C layout and synchronization protocol.

### Callbacks

Inspect the typedef and all call sites. Emit a callable handle with safe argument and
result wrappers. When call sites use different ownership distributions, emit a distinctly
named safe wrapper for each distribution over the shared C function-pointer type.

Wrap an inline function pointer when no ownership-compatible callable wrapper exists.

### Raw lifetime strategies

When objective is `raw-lifetime` look for releaser, disposer, cloner, and allocator/constructor routines
for type-erased `void` or string handles, and emit generic policies / strategies that call the primitive via FFI,
so that owned string or generic array/singleton handles can bind them to implement RAII. Do not
also expose the primitive as an ordinary safe function.

Emit separate policies for singleton and array handles. 

Home each with the primitive's translation unit.

### Porting symbols

For `port`, translate the implementation to safe idiomatic Rust and preserve observable
behaviour. Re-export it to C according to the conventions while C consumers
remain.

- The raw gateway reconstructs safe wrappers and calls the native function.
- Remove a TU-local export after its last C consumer is removed.
- Guard only replaced C bodies with the path-derived per-file guard.
- Group adjacent guarded bodies when useful; do not guard the whole file.
- In the C fallback branch, declare Rust exports and redirect TU-local names to
  collision-safe exports.
- Wire the file flag and Rust static library through the actual build system; do not
  assume link mechanics.
