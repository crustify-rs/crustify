---
name: porting-symbols
description: "How a scheduled C symbol is reimplemented in safe Rust, porting's symbol route: functions and their exports, globals, function pointers, static inline functions and macros, each with its later stages. Read before porting any symbol, and when reviewing ports."
---

# Porting symbols

How a scheduled C symbol is reimplemented in safe Rust: the symbol route, which follows
[`porting`](../SKILL.md)'s FFI boundary section and starts from
[`binding-symbols`](../../binding/symbols/SKILL.md)'s; the types it reaches are
[`porting-types`](../types/SKILL.md)'s.

A ported symbol's implementation is translated to safe, idiomatic Rust with its observable
behaviour preserved.

## 1. Functions

A ported function takes the safe API [`binding-symbols`](../../binding/symbols/SKILL.md)'s Functions
section gives a function, or keeps its wrapper's, as [`porting`](../SKILL.md)'s FFI boundary section describes.

A function that remaining C calls or takes the address of is exported, as
[`porting`](../SKILL.md)'s FFI boundary section describes. Its gateway undoes what the safe API converted,
so that its C callers see what the C function did: it rebuilds the safe arguments from the
C ones, writes the out-parameters and buffers through the pointers C passed, and reports a
failure through the function's C error convention, its return and the error state the C
function set, `errno` included, which the Rust behind it never sets. A panic is caught at
the gateway and reported as a failure, or aborts where the function cannot fail: none
unwinds into C. A variadic function's export cannot be defined on stable Rust, so a shim
keeps its C signature, as [`bindgen`](../../bindgen/SKILL.md)'s shims are compiled, and calls
a fixed-arity export with the arguments it formats or unpacks. Its later stage, `port/unexport`, removes the
export, with the raw binding and the allowlist entry that reach it, once no remaining C
references it.

A lifecycle routine's port reimplements it behind the policy its type's port or wrap
wrote, which it repoints at the Rust routine, and writes no API of its own, as `binding-types`'
Lifecycle section has the symbol route skip what a type batch emitted. The last of its
type's own module's memory users to be ported moves its storage to Rust's allocator,
unless C of other modules still allocates or frees it raw, which leaves that move to its
`port/memory`.

## 2. Globals

A ported global takes the safe API [`binding-symbols`](../../binding/symbols/SKILL.md)'s
Globals section gives a global, or keeps its wrapper's. A global that remaining C accesses
is exported, as a function is, and keeps the C layout and the synchronization protocol
those accesses rely on while it is. Its later stage, `port/unexport`, removes the export, as
a function's does, and its storage then takes a native form, as state moved out of C does.
A thread-local one cannot be defined for C on stable Rust, so a shim keeps its C definition,
as [`bindgen`](../../bindgen/SKILL.md)'s shims are compiled, until that stage. A global no
remaining C accesses is native from its port.

## 3. Function pointers

A ported function pointer keeps the safe callable type
[`binding-symbols`](../../binding/symbols/SKILL.md)'s Function pointers section gives it, which is its API from its port: its Rust consumers, and
the ported code that calls it, use that type alone. While remaining C calls a function
pointer of its type or supplies one, its C form stays beneath it: the function-pointer type
of its raw binding, the trampolines through which a Rust closure reaches the C that calls
it, and the `unsafe` constructor through which a C function reaches Rust, passed to an
export, whose gateway builds the C variant from the function and the context it receives,
or stored where C wrote it. Its later stage, `port/unexport`, removes that C form, with the
raw binding and the allowlist entry that reach it, once no remaining C references it, as
[`scheduling`](../../../planning/scheduling/SKILL.md)'s Later stages section times it. A
function pointer no remaining C calls or supplies by its port is native in its
implementation too: its closure or trait alone.

## 4. Static inline functions

A `static inline` function a header defines is internal API of the module the
decomposition gives it, and is ported as its other functions are. Its C callers expand its
body in their own TUs, so an export alone does not reach them: at the module's
integration, the header's definition is replaced by its prototype, and the remaining C
calls the Rust module's export, under the function's bare name, where it inlined the body.
<!-- TODO: cross-language LTO (`-Clinker-plugin-lto`, with a clang whose LLVM matches
rustc's) would inline the export back into its C callers. -->

## 5. Macros

A macro takes the Rust form [`binding-symbols`](../../binding/symbols/SKILL.md)'s Macros section gives it,
which reaches the Rust items its expansion uses once they are ported. A macro a TU defines
goes with its TU. A macro a header defines, internal or public API that another module's C
may expand, also stays in its header for the remaining C, unexported, and its C and Rust
forms are not linked, beyond the Rust form's annotation. It keeps expanding where remaining C
invokes it, until its header goes with the last C file that includes it, as
[`porting-workflow`](../../../workflows/porting-workflow/SKILL.md)'s Principles section
describes: a type generator keeps minting the instances its remaining invocations define,
and what an expansion calls or accesses is reached as any remaining C reaches it, a
function or global Rust owns through its export, a type through its C layout. An
expansion site is a use by the function that holds it, so it holds back the later stages
of what it reaches, as [`scheduling`](../../../planning/scheduling/SKILL.md)'s Later stages
section counts its users.
