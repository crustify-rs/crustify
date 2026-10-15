# Generating safe bindings

How a scheduled C item becomes a safe Rust binding.
A binding keeps the C implementation and puts a safe Rust API in front of it.

## Item analysis

Each item is analysed from its source declarations and definitions, its dependency closure,
its callers, its field touchers and its existing Rust consumers. For every pointer field,
argument and return, every code path that stores, transfers, clones, retains or frees it is
inspected.

The analysis establishes:

- ownership and transfer direction;
- shared or mutable access;
- nullability;
- scalar, array, or other cardinality;
- type erasure and known element types;
- borrow and keepalive relationships; and
- construction, clone, and destruction paths.

Observed behaviour overrides names and comments. A distinction the analysis establishes is
preserved in Rust rather than flattened into a copy of an ambiguous C signature, and the
findings shape every binding that follows.

## Macros

A C macro is never published as an independent Rust API.

- A symbol alias is bound by calling the underlying symbol's safe wrapper.
- A function-like macro is bound through an existing shim, or the smallest shim it needs,
  which is then bound and wrapped.
- A constant macro is used through its generated binding.
- A type-generating macro follows the type route.

## Safe boundary

Any ABI or layout C still observes is preserved, and imported entities remain C-owned.

Rust consumers use safe APIs. Raw operations are confined to:

- wrapped-layout projection;
- wrapped FFI calls; and
- operations whose caller obligation cannot be represented in Rust types.

SCC cuts and unavailable higher-layer dependencies remain narrow documented raw seams until
a safe dependency becomes available, which then replaces them. Every unsafe block carries
the safety comment the conventions specify.

---

## Type route

### Surface

A binding's surface is the fields and lifecycle primitives the public API publishes.
Releasers, field disposers, cloners, constructors, casts and pointer-field semantics are
identified before a representation is chosen.

### Safe layout

A type is bound as a safe layout over the raw type and its handles, as the conventions
describe.

A synthetic type generator is bound as:

- a generic wrapper for a homogeneous family converging on the generator;
- an alias of a dominant concrete instance to the generator with its element wrapper; and
- specializations only for behaviour that differs from the generic surface.

### Lifecycle

Every ownership variant the analysis supports has a representation. Lifecycle and clone
strategies are stateless, layout-compatible and statically selected when the state is
recoverable from the object; runtime state is carried only when construction, destruction
or cloning needs external data.

A type's constructor and init routines are bound with its lifecycle policy, so that where
possible it is exported as a safe function returning the fully-formed object. An argument
whose type is not yet wrapped remains a narrow documented raw seam, which the run wrapping
that type replaces.

C lifecycle primitives are kept while C can allocate or free the storage.

Promoting construction-phase storage into an owner is unsafe, so it is encapsulated in the
type's safe constructor: consumers of the public API never call `assume_init` in their own
unsafe blocks.

Lifecycle routines are also scheduled as free symbols; the symbol route skips those a type
run already emitted.

### Field accessors

Each accessor follows from the ownership, mutability, nullability, cardinality and lifetime
findings, and every pointer-derived result is tied to the state that keeps it alive.

Fields are projected with `addr_of!`, `addr_of_mut!`, `&raw const` or `&raw mut`, never
with `&(*p).field` or `&mut (*p).field`; access follows the conventions.

Each kind of field is expressed as follows:

- An owned-reference field has a replacement setter that drops the old owner, an owning
  getter that leaves the field valid, and a shared borrowed getter.
- A by-value wrapped field has a shared or mutable handle over the projected place.
- A stored borrow without an expressible lifetime has an unsafe setter whose caller
  contract carries the referent-lifetime obligation.
- Statically known owned and borrowed cases have distinct wrapper forms, with a shared
  trait where useful.
- A runtime ownership flag has separately checked owned and borrowed operations.
- A union and its discriminator become a tagged Rust enum when the mapping is valid.
- Scalar and array variants have separate typed forms.
- A type-erased field takes a generic element type when it is known, and the discovered
  untyped lifetime strategy otherwise.
- `Send` and `Sync` are implemented only with a specific synchronization or immutability
  proof.

Translated dependent types and callbacks are used through their safe wrappers, and strings,
arrays and erased owners through real release strategies. A lower-layer temporary raw
reference this wrapper makes obsolete (a cut SCC) is replaced; a documented raw gap remains
only for an unavailable higher-layer dependency.

An inline function-pointer helper without an ownership-compatible wrapper gets one,
emitted with the type.

---

## Symbol route

### Functions

A function is bound as a `pub fn`; it is a `pub unsafe fn` only when no safe type-level
contract can express its caller obligation. Arguments and returns use typed wrappers, and
raw pointers are reconstructed only at the FFI call, in a small documented unsafe block.

Moved (exclusively or refcounted), borrowed (immutably or mutably), nullable, scalar and
array variants are separate functions when one signature cannot express every valid
contract. A function taking or returning type-erased arguments is generic.

Ownership is stateless; runtime state is carried only when destruction or cloning requires
it.

A method is emitted in an `impl T` block on the type it implements, taking `&self` or
`&mut self` as its first argument. A free function stays free.

The exposed public interface carries no unsafe and no raw pointer: raw and unsafe logic
stays internal, behind safe translated dependencies. A documented raw pointer remains only
for an unavailable higher-layer wrapper, and a lower-layer raw surface is updated when the
new safe contract replaces it.

Lifecycle primitives for typed, type-erased or string handles may be scheduled as symbols
although a previous run already emitted the release, clone or construct strategy that calls
them; they get no second wrapper.

### Globals

A global is bound as a `'static` borrow, never as an owner. Its access discipline follows
from every C access:

- immutable after initialization: a shared handle;
- synchronized by C: the matching safe synchronization (an atomic, or guards handing out
  the shared or exclusive handle under the lock), never discarding a lock's status;
- otherwise mutable: `unsafe` accessors that exclude concurrent access, reported as such;
- thread-local: a handle borrowed for a closure on the current thread, neither `Send` nor
  `Sync`.

A lock counts only if every access takes it and it rejects same-thread re-entry. While C
consumers reference the symbol, its C layout and synchronization protocol are kept.

### Callbacks

A callback is bound from its typedef and all of its call sites as a callable handle with
safe argument and result wrappers. When call sites use different ownership distributions,
each distribution has its own distinctly named safe wrapper over the shared C
function-pointer type.

An inline function pointer is wrapped when no ownership-compatible callable wrapper exists.

### Raw lifetime strategies

A `raw-lifetime` worklist discovers the releaser, disposer, cloner and allocator or
constructor routines for type-erased `void` or string handles. Each becomes a generic
policy or strategy that calls the primitive via FFI, so that owned string and generic
array or singleton handles bind it to implement RAII. The primitive itself is not also
exposed as an ordinary safe function.

Singleton and array handles have separate policies, each homed with its primitive's
translation unit.
