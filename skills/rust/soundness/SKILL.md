---
name: soundness
description: "The patterns by which safe Rust over C has reached undefined behaviour in Crustify's campaigns, each with what prevents it and which check catches it, and how the catalogue grows from proven findings. Read before analysing, binding or porting any item, before writing its UB tests, and when reviewing for UB or contracts."
---

# Soundness patterns

The ways a binding or a port of C has let safe Rust reach undefined behaviour, or met a
memory-safety defect of the C that it had to keep out of its safe API. Every pattern here
has a proven finding of a campaign behind it: the catalogue records what went wrong, not
what could. An item's analysis asks of each pattern whether the item can meet it, and a
review for UB or contracts reads the item against the same list, so that a defect one
module met is not met again in the next.

## 1. Patterns

Each pattern has an id, which a finding's report names. What prevents a pattern is stated
as what the Rust does; [`binding`](../binding/SKILL.md) and [`porting`](../porting/SKILL.md)
give the routes that do it.

### 1.1 Values the C trusts

| id | pattern | what prevents it | caught by |
|---|---|---|---|
| `unchecked-arithmetic` | The C computes with a value a safe caller controls and does not check it: a signed overflow, a shift, a size that wraps with its header, a zero divisor. | The Rust checks the value's range before the call, sizes past `isize::MAX` included, and refuses what the C would compute wrongly. | UBSan, review |
| `diverging-precheck` | A check in Rust repeats the C's parsing or evaluation and differs from what the C then computes. | The Rust validates the exact value the C will use, or computes the result itself and hands the C only that. | UBSan |
| `degenerate-input` | The C reads out of bounds on an input its own validation accepts, such as an empty string beside others or a null pointer for a string. | Every wrapper that can route the input to that reader refuses or normalises it, the indirect routes included. | ASan |
| `variant-mismatch` | A tagged, variable-size value of another variant than its container expects is passed on, and the C sizes its buffers by the container's. | The Rust compares the value's variant with the container's before any call that looks it up or formats it. | ASan |

### 1.2 Memory and ownership

| id | pattern | what prevents it | caught by |
|---|---|---|---|
| `size-known-to-c` | Only the C knows an object's true size or layout: an opaque type, a pointer a tag types, a base struct its callbacks read past, an array sized by a count. Rust builds it too small or types it wrongly. | Such an object is allocated through the C alone, a tagged pointer is typed only where its tag is vouched for, and an object whose callbacks read more than Rust built is refused. | ASan, review |
| `hidden-dependency` | A handle, a lent pointer or a callback outlives something it depends on without showing it: a parent it points back to, a global the program may close, lent memory the C copied into a second slot. | The handle's lifetime is tied to that owner, or it keeps the owner alive; a pointer the C stores is bounded by its longest-lived reader. | ASan, Miri, review |
| `failure-leaves-state` | A failure path of the C, most often a failed allocation, leaves an object uninitialised, freed, wrongly sized or half written and still returns, sometimes reporting success. | The Rust trusts nothing the C leaves after a failure: it validates outputs again, does not reuse the object, and composes the operation itself where the C's error path is unsafe. | ASan, UBSan, review |
| `allocator-rule` | The binding vouches for a rule of alignment or allocation that some build or allocator of the C does not keep: the maximum alignment, a zero-size resize, who may free whose storage. | It vouches only for what every configured allocator guarantees, and checks alignment at each constructor that copies. | Miri, UBSan, review |
| `adoption-condition` | An adoption takes ownership without stating when the C owns the storage: a sentinel pointer at zero capacity, one element listed twice, a buffer a pool still tracks. | The contract states the exact condition, and the Rust checks it before the owner can free or resize. | ASan, review |
| `count-wrap` | A reference count the C does not check wraps once safe Rust can leak clones, and the object is freed early. | A count that can wrap within a process's lifetime is checked before each increment, and the clone fails or aborts before it wraps. | Miri, review |
| `uninitialised-as-data` | Memory the C leaves unwritten is exposed as initialised Rust data, or the argument that the C writes it is false on some path. | The Rust views it as uninitialised until every path of the C is shown to write it; an export takes raw pointers and builds no reference over memory its caller may have left unwritten. | Miri, review |
| `aliasing-at-the-boundary` | A pointer the C keeps is derived from a borrow that a later reborrow ends, or Rust holds a reference over memory the C still writes or shares. | Every pointer the C keeps is derived from the original raw pointer, and a reference is handed out only over a span no C writer or co-owner reaches. | Miri, BSan, review |

### 1.3 Threads and callbacks

| id | pattern | what prevents it | caught by |
|---|---|---|---|
| `unsynchronised-global` | The C reads and writes global state, or initialises it lazily on first use, without synchronisation, so that safe calls on unrelated objects race. | The Rust initialises or serialises that state before any safe call reaches it. | TSan, review |
| `assumed-locking` | A `Send` or `Sync` proof assumes the C object's own locking covers every access, but a path skips the lock, reads after releasing it, or the object has none. | Thread safety is derived from every reader and writer of each field. | review |
| `callback-state` | A trampoline mishandles a panic, a refusal or a re-entry: a stored panic goes stale or a nested call drops it, a drop panics, the C goes on after a refusal, or the callback runs under a lock of the C. | A stored panic or stop belongs to one outermost call of the C, no drop panics, and a stop is promised only where the C can be stopped. | review |

A `# Safety` contract or a `// SAFETY:` proof that is wrong in a way no pattern above names
is still a finding: a contract is derived again from every safe method that relies on it
whenever one is added.

## 2. Findings

A finding of the `ub` or `contracts` objective names its pattern, or `new`, as
[`reviewing`](../../verification/reviewing/SKILL.md)'s Reports section describes. A
sanitizer's false positive is no finding and names none.

A finding of a known pattern means that its statement did not let the analysis recognise
the case, or that what prevents it was not enough. A finding that is `new` is a pattern the
catalogue lacks.

## 3. Evolution

The catalogue changes only from findings a reproducer proves, as
[`evolution`](../../crustify/evolution/SKILL.md) describes:

- a `new` finding is proposed as a pattern once it is stated without the target's names,
  with the finding as its evidence; one that can only be stated in the target's names is
  that campaign's lesson;
- a pattern whose findings recur has its statement or its prevention sharpened, from the
  findings that escaped it; and
- a pattern no campaign has met since it was written stays: its absence is what the
  catalogue is for.

What tells whether the catalogue works is the count of findings of known patterns, over
the modules integrated since a pattern was written, taken together: it falls against the
modules before, or the catalogue is not what prevents them. One module alone tells nothing,
since modules differ. The unsafe sites the reviews read, which the count would be taken
against, are not recorded yet. The count of `new` findings tells how much of what goes wrong
the catalogue does not hold yet.
