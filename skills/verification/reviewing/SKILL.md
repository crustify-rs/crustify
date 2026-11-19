---
name: reviewing
description: "How a port is reviewed: for each objective, whether the code meets it as fully as it can, and every way it could do better as a finding; the kinds of finding and how each is fixed. reviewing-reports gives how findings and reproducers are filed. Read before reviewing, briefing a reviewer, or fixing what a review found."
---

# Reviewing

A reviewer is a subagent that wrote none of the code it reviews. It takes each of the
port's objectives in turn and asks of the code: is this objective met as fully as it can
be? Every way the code could meet it better is a finding, filed under its kind as
[`reviewing-reports`](reports/SKILL.md) describes. The findings are fixed, and review goes
on until a reviewer finds no way left to do better on any objective. A
finding marked fixed is checked by rerunning its reproducer.

A reviewer reads the code itself. What a tool reports shows where to start and
cross-checks what the reading found; it never bounds the review.

## 1. Kinds

Each kind asks one question of the code. A brief may narrow the kinds; without that, a
review asks every one that applies. A tool may add kinds of its own.

### 1.1 Interoperability (`interop`)

Do the rest of the codebase, its tests and its programs work on the Rust as they did on
the C, through the same headers and ABI, sharing memory where the C did? Could the
exports or the Rust API change less when the rest of the C is ported later?

### 1.2 Unsafety (`unsafety`)

Is the unsafe code as small as it can be? Unsafe annotations and raw pointers on the
public API that safe, idiomatic variants could replace, and unsafe code inside that a safe
construct, or an [`ffibox`](../../tools/ffibox/SKILL.md) primitive, could replace.

### 1.3 Contracts (`contracts`)

Is every safety contract correct and complete?

- the `# Safety` obligation of a public entry point that must stay unsafe: a caller who
  honours it can still reach undefined behaviour, or it asks for more than the
  implementation needs;
- the `// SAFETY:` justification of an `unsafe` block: the invariant it claims does not
  hold on every path that reaches the block, or no comment justifies the block; and
- an obligation stated on code C calls, such as a callback, which no Rust caller can
  honour because C chooses the arguments: what Rust can test is refused in Rust, in front
  of the C, instead.

A contract is tested by trying to break it: an input, a call sequence or an interleaving
that honours the obligation, or reaches the block through safe code, and still violates
what the `unsafe` relies on.

### 1.4 Undefined behaviour (`ub`)

Is the code free of undefined behaviour, reached from the safe public API, from the unsafe
public API within its `# Safety` obligations, or from C through an export within the C
declaration's contract?

### 1.5 Equivalence (`equiv`)

Where the C is well defined, does the Rust behave the same? A divergence is a defect only
when it is unintended: one that corrects a C defect on purpose, and says so, is no
finding.

### 1.6 Functional correctness (`functional`)

Does the code do what the library is meant to do, in its public API and its internals?
The specification is, from the most authoritative: the formats and standards the library
implements, its documentation, what its test suites assert, and its maintainers' stated
intent. A finding cites what the behaviour departs from. Where the C departs from it too,
the defect is not copied into the Rust, and the finding records the C's. A leak, a
deadlock or a panic on valid input departs from nearly every specification.

### 1.7 Performance (`perf`)

Is the code as fast as it can be, and at least as fast as the C, on representative
workloads? A finding names the workload, the measurement and the cause where the reviewer
can find it.

### 1.8 Ergonomics (`ergonomics`)

Is the public Rust API as easy to use as it can be: its names, its conversions, its
iterators, builders or defaults where the C takes long argument lists, and the standard
traits its types implement?

### 1.9 Idiom (`idiom`)

Does the implementation use Rust's own means rather than transliterate its C: iterators
where index loops stand, `Result` and `?` where status codes stand, ownership where
lengths and releases are carried by hand?

### 1.10 Tests (`tests`)

Do the tests show what [`testing`](../testing/SKILL.md) lists, as thoroughly as they can?
Paths, states and transitions they leave unreached, measured by coverage; assertions too
weak to fail when the code is wrong; and C test cases none carries over.

### 1.11 Anchors (`anchors`)

Does every public item that stands in for a C item carry its anchor and alias, naming the
right item, as [`anchors`](../../rust/anchors/SKILL.md) describes?

### 1.12 Misc (`misc`)

Anything else the port could do better.

## 2. Fixes

Who fixes a finding, its author, its reviewer or another agent, is the agent's choice. A
finding with a reproducer is fixed with a regression test made from it: a UB test that
runs clean under the instrument that caught it, or fails to compile because the fix
removed the safe path to the defect; an equivalence test; or a unit test. A `contracts`
finding is fixed in the contract, or, where the contract can be broken, in the code it
guards. A `tests` finding is fixed by the tests it asks for, with the coverage they add.
