---
name: binding-symbols
description: "How a scheduled C symbol becomes a safe Rust binding, binding's symbol route: functions and what their signatures carry, globals, function pointers, macros and lifecycle strategies. Read before binding any symbol, and when reviewing bindings."
---

# Binding symbols

How a scheduled C symbol becomes a safe Rust binding: the symbol route, which follows
[`binding`](../SKILL.md)'s Safe boundary section and reaches the types
[`binding-types`](../types/SKILL.md) binds. [`porting`](../../porting/SKILL.md)'s Symbol route starts from it.

## 1. Functions

A function is bound as a `pub fn`; it is a `pub unsafe fn` only when no safe type-level
contract can express its caller obligation. Its FFI call, and the raw pointers it
reconstructs for it, sit in its module's `ffi_import` region, as the
[conventions](../../conventions/SKILL.md)' Unsafe regions section describes.

Its signature follows the analysis's findings, each argument and return taking the safe
form of what it names:

- **Out-parameters.** A pointer the function only writes through, to hand back a result,
  is part of the return, several of them a tuple, present only in the outcome in which the
  function writes it.
- **Buffers.** A pointer and the count that bounds it are one slice, the count taken from
  it; a buffer the function fills returns the part it filled.
- **Strings.** A NUL-terminated string the function borrows for the call is a borrowed C
  string, or the Rust string or path type of the encoding the analysis establishes,
  converted at the call, an interior NUL rejected before it. A returned string is a borrow
  tied to what keeps it alive, or an owner over its releaser where the caller frees it.
- **Nullability.** A nullable pointer is an `Option`.
- **Errors.** A function that can fail returns a `Result`, its failure read from the error
  convention the analysis establishes: a status return, a sentinel return, or error state
  the library keeps beside the call, read immediately after it, before another call into
  the library can replace it. A return that reports only success is not returned, and an
  outcome its C callers treat as ordinary, such as an exhausted iteration or an absent
  entry, is part of the success value. Each error convention has one error type, carrying
  what the convention reports, `errno`'s being `std::io::Error`.
- **Variadics.** A variadic function is bound through fixed-arity forms: one that formats
  its arguments takes the formatted message, passed to a `"%s"` format, and any other is
  one function per argument list its callers use. A `va_list` function is reached only
  through its variadic sibling.

A `static inline` function a header defines is bound as an exported one is: it is
allowlisted, and called through the raw binding generated for it, as
[`bindgen`](../../bindgen/SKILL.md)'s Generation section describes. The exception is a short
one whose whole implementation is in the header, which may be ported instead, to save the
cost of an FFI call, unless what it does depends on the build's features or configuration.
A reimplementation is a port, as [`porting`](../../porting/SKILL.md) describes, and is
annotated `Replaces`, as the [conventions](../../conventions/SKILL.md)' Anchors section describes.

Moved (exclusively or refcounted), borrowed (immutably or mutably), nullable, scalar and
array variants are separate functions when one signature cannot express every valid
contract. A function taking or returning type-erased arguments is generic.

A method is emitted in an `impl T` block on the type it implements, taking `&self` or
`&mut self` as its first argument. A free function stays free.

## 2. Globals

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

## 3. Function pointers

A function pointer is bound from its declaration and every site that calls it or supplies
it, a function assigned to it or passed as it. One a typedef declares is named after its
typedef; one written inline is named after the site that declares it, the field,
parameter, return or global, as the [conventions](../../conventions/SKILL.md)' Naming
section describes, so that two inline pointers of one signature in one file are two items
when their sites differ.
<!-- TODO: wavefront keys an inline function pointer by its signature and home file, so
the sites of one signature in one file are one item; it has yet to key them by declaring
site, a local's or a cast's folded into the site whose value it carries. -->

It is bound to a safe callable type that holds either of its implementations:

- a Rust closure, which C reaches through a trampoline of the C signature and the context
  C passes back to it; and
- a C function, with its context, which Rust calls: made only inside the crate, through an
  `unsafe` constructor whose contract states what the C that supplies it guarantees, the
  function's validity and its context's lifetime and threads, and safe to call, its
  arguments and result converted as a function's binding converts them.

A function pointer that crosses the boundary gets both, whichever direction its uses take
today, since a port turns the C that calls or supplies it into Rust, as
[`porting`](../../porting/SKILL.md)'s Function pointers section describes, and its safe API
does not change then. Its consumers see only the safe form, its closures taking and
returning safe types: a closure borrowed for the call, `impl FnMut(…)`, where C keeps it
for the call that receives it; an owned closure, released with its context, where C keeps
it until it releases it; and a trait, for a struct of function pointers a library calls
into, which Rust types and the C implementation implement alike. A function pointer read
from C, such as a field's getter returns, is the callable type, never the raw pointer.
How long C keeps it is a finding of the analysis.

Its trampoline is a panic barrier, which maps a panic to the C's error convention, and it
refuses a re-entrant call, which would alias an `FnMut` closure, unless the analysis shows
that C re-enters it, which takes an `Fn` closure instead. A function pointer C calls from
another thread takes a `Send` closure, and a `Sync` one when C may call it from several at
once. Three cases shape the type further:

- one without a context parameter carries no captured state: its Rust implementation is a
  closure without captures, each closure type its own trampoline, or a plain function;
- one C reads as absent when null, where it uses a default or calls nothing, is an
  `Option` of the callable type; and
- one C compares with a known function, such as its default implementation, keeps in its C
  variant the pointer it was made from, so that the comparison still holds.

When its sites hand ownership across differently, each distribution has its own distinctly
named callable type over the one C function-pointer type.

## 4. Macros

A C macro is bound to a Rust form of its own:

- a type-generating macro, to one generic type, through [`binding-types`](../types/SKILL.md),
  its instances aliases of it;
- a constant macro, to a `const`, defined from its generated binding;
- a symbol alias, through the safe wrapper of the symbol it names; and
- a macro that implements logic, to a function, `#[inline]`, or `const` where its body
  computes on its arguments alone, which reimplements the body and reaches C only for the
  symbols its expansion uses, through their safe wrappers, and for the fields it accesses,
  through their accessors. A `macro_rules!` takes its place only where a function cannot
  express it: control flow that leaves its caller, token pasting or stringification, an
  argument used as a place, or one evaluated lazily or more than once.

A macro whose expansion depends on the build's configuration, which the Rust does not see,
is the exception: it is reached through a shim, `crustify_<NAME>`, bound and wrapped.

## 5. Lifecycle strategies

The foundational modules hold the allocator or constructor, releaser, disposer and
cloner routines of type-erased `void` and string handles, each with the lifecycle role
established while planning. In a batch of a foundational module, which its task's `module` names
and `modules.json` marks `foundational`, an item with a lifecycle role becomes a generic
policy or strategy that calls the primitive via FFI, so that owned string and generic
array or singleton handles bind it to implement RAII. The primitive itself is not also
exposed as an ordinary safe function. The module's other items follow their route.

Singleton and array handles have separate policies, each in its primitive's home. A
family's allocator, releaser and cloner form one policy and share a batch.
