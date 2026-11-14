# Goals

This file states what Crustify is for and how it evolves. Every change to Crustify is judged
against these goals, whether it changes its skills, its agents or its tools.

A rule that serves none of these goals is removed. Where two goals are in tension, they are
weighed for the case at hand, and the weighing is stated.

The goals evolve too, from the same evidence as everything else:

- a goal the campaigns keep missing;
- a goal no decision ever cites;
- two goals that keep conflicting the same way; or
- a well-founded change that none of the goals serves.

A change to the goals is proposed as Crustify's `evolution` skill describes. It lands only
with the user's approval.

Each goal names its *fitness*: what a campaign measures to tell how far the goal is met. Each
thing measured is a *measure*. A measure is read from one of two sources, and no run is made
only to take it:

- what the campaign's runs produce anyway: the dashboard, the review reports, the gates and
  the plan; or
- a rerun the campaign's reviews already make.

A *tier* is one of the checks that code meets one after another. An *escape* is a defect
caught by a later tier than the one that read the code first. Later tiers include:

- a module pass after a wave's review;
- a switch;
- a revisit; and
- a ship point's gates.

Worse work could improve some measures. Such a measure is *paired* with the measure that
catches the worse work, which is its *pair*, and neither is read alone. When there are more
escapes, fewer findings is no gain. When the work is redone, cheaper work is no gain.

Some measures are held by no artifact yet. Such a measure is marked **Not taken yet**. Until
it is taken, what it measures is judged, not measured.

Under each goal, **Measure** states a measure, **Paired with** names its pair, and **Not
taken yet** names what no artifact holds yet.

## 1. Safety

No undefined behaviour is reachable from safe Rust. The unsafe code that remains sits in its
regions, and is sound for every input.

### The unsafe surface

- **Measure.** What a deterministic scan counts on each landing:
  - raw pointers and `unsafe fn`s on the public API;
  - unsafe lines and raw dereferences; and
  - unsafe code outside its regions.

  The first two fall as a module goes from wrapped to ported and through its later stages.
  The third is zero throughout.
- **Paired with** soundness, below. Calling an unsound function safe takes an obligation off
  the API, and so lowers this measure.

### Soundness

- **Measure.** The defects a reproducer proves, as the review reports file them by kind.
  These defects are undefined behaviour and contracts that can be broken.
- **Paired with** the escapes among these defects.
- **Not taken yet.** The tier that caught a defect. Also the unsafe sites a review read,
  which the defects are counted against.

## 2. Equivalence

The Rust keeps the C's specified behaviour, not its bugs. The specified behaviour is what
the C's documentation, tests and consumers rely on.

- **Measure.**
  - The target's own tests passing over the Rust at each switch, against their recorded
    baseline.
  - The inputs and states on which the Rust is compared with the C it replaces, with no
    difference left unexplained.
  - The differences made on purpose, each documented and held by a test.
- **Paired with** the differences found after the comparison ended. They are found by a
  review, at a switch, or by a consumer.
- **Not taken yet.** The inputs compared and the deliberate differences, as figures. Each
  run's notes alone hold them.

## 3. Idiomatic Rust

The API a Rust consumer sees is native Rust: ownership, borrowing, errors, iteration and
traits. It is not C's conventions behind a Rust syntax.

- **Measure.** The C forms that Safety's scan still counts on the public API: raw and
  untyped pointers, and obligations handed to callers. Also the ergonomics and idiom
  findings that reviews file, counted per item reviewed.
- **Paired with** the ergonomics and idiom findings that a later tier or a consumer makes on
  an item an earlier review passed. A review that reads less finds less.
- **Not taken yet.** Which tier made a finding.

## 4. Performance

The emitted Rust costs no more than native Rust would. Where tokens and time buy
accuracy, the harness spends them.

### The harness

- **Measure.** Cost and wall time per translated item, reviews and switches included.
- **Paired with** what was redone: batches run again, gates rerun and merges made twice.
- **Paired with** Safety's and Equivalence's measures: cheaper work with more escapes is not
  cheaper.

### The emitted Rust

- **Measure.** The emitted Rust's time and memory against the C it replaces, on the target's
  own workloads.
- **Paired with** Safety's and Equivalence's measures, since a check dropped is time saved.
- **Not taken yet.** The whole measure.
  <!-- TODO: no campaign benchmarks what it ports; which workloads, and at which event,
  is not specified. -->

## 5. Verification

What the agents produce is machine-checked wherever it can be, rather than left to an
agent's judgement. It is checked by types, lints, sanitizers, Miri, schemas, deterministic
tools and compile-time assertions.

- **Measure.** The line coverage of the ported Rust.
- **Paired with** the share of deliberate faults that the ported Rust's tests catch, since
  code that runs is not code that is checked.
- **Paired with** the gate results that a run reported and that its landed tree does not
  reproduce. A review files these gate results among its reports.
- **Not taken yet.**
  - the seeded faults, which are taken only where a review happens to seed them;
  - the region coverage of the ported Rust; and
  - the states and transitions the tests reach.
  <!-- TODO: seeding faults is not a step of any stage yet. -->

## 6. Maintainability

Established software engineering practice and reuse keep the emitted Rust and the harness
itself maintainable for the long term. Each rule and each piece of code has one place.
Standard libraries and idioms come before new ones.

- **Measure.** What was reused against what was made again:
  - owners, callbacks and lifecycles built from the shared primitives rather than by hand, as
    Safety's scan counts them; and
  - library entities reached through the standard library or an adopted crate rather than a
    new binding, as the plan records each one's route.

  A procedure worked out by hand a second time, and a proposal that repeats another's signal,
  count against this measure.
- **Paired with** Least constraint's measure. Where a rule forces reuse and what is reused
  does not fit, that reuse is counted there.

## 7. Interoperability

C and Rust work together soundly in both directions for as long as both remain. Each reaches
the other through the boundary in its own conventions. The Rust also works with the Rust
ecosystem: the standard library's types and traits, and existing crates where they serve.

- **Measure.**
  - The remaining C's tests passing over the Rust link.
  - The build modes and variants the crate builds and tests in.
  - The kinds of crossing a campaign exercises and passes, in each direction:
    - exports checked against the C declarations they replace;
    - callbacks C makes into Rust and Rust into C; and
    - layouts and storage the remaining C shares.
- **Not taken yet.** The kinds of crossing, as a count.

## 8. Incremental migration without breaking consumers

A codebase moves to Rust one module at a time. Every landing builds and passes its gates. No
consumer breaks: a C or Rust consumer's code does not change as what it consumes is wrapped,
ported or moves through its later stages.

- **Measure.**
  - The items whose API changed or went after their first landing, each with its reason.
  - The landed trees that failed a gate.
  - The target's test baseline, which moves only by the cases carried over.
- **Paired with** Idiomatic Rust's measure of C forms on the public API. An API that never
  changes because it stayed C's breaks no one and serves no one.

### The order

- **Measure.** The batches that met a dependency not yet landed, and waited for it, rewrote
  around it or reached past its wrapper.

  Items land after what they depend on. Where the order cuts a cycle, an item lands after
  the binding of what it depends on. That order is how this goal is met, and Safety's and
  Performance's with it: a consumer written once, over a boundary written once.
- **Not taken yet.** The whole measure.

## 9. Generality

The rules hold for any C codebase. What holds for one target alone is that target's lesson,
not a rule.

- **Measure.** Of what a campaign's evidence taught, the share stated as rules without the
  target's names against the share kept as the target's lessons. Also the rules a second
  target could not follow as written.

## 10. Least constraint

A rule states what must hold. Unless the how is itself what must hold, the rule leaves the
how to the agent.

- **Measure.** Per module, the rules that a run:
  - worked around;
  - rewrote sound code to satisfy; or
  - reported as forcing a worse result.
- **Paired with** what a loosened rule let through: the changes marked as weakening a check,
  and the defects found where a rule was loosened.

## 11. Consistency

One kind of item is translated one way. Items that mean the same in C take the same Rust
pattern, whatever their syntax and whichever agent, batch or campaign translates them. The
pattern is the one the conventions and the how-to skills give them. A departure states its
reason.

A pattern a skill gives is a how that must hold, in Least constraint's terms. A pattern is
given only where translating the same thing two ways costs a consumer or a reviewer. Where
the skills give none, the agent chooses. A choice met twice, where two ways would cost, is
proposed as the pattern rather than left to converge.

- **Measure.** The conventions findings reviews file, per item.
- **Paired with** two measures, since a review that reads less finds less:
  - the items a later batch or review reshaped; and
  - the conventions findings a later tier makes on an item an earlier review passed.
- **Not taken yet.**
  - both paired measures;
  - the departures that state their reason, against the departures a review had to find; and
  - whether an item translated twice took the same shape both times.

## 12. Attribution

Every fact a decision rests on can be reproduced. Every change traces back to the run, and
the revisions, that made it.

- **Measure.** The landed commits, dashboard cells and decisions that trace to a run, its
  session and its revisions, against those that do not. Two examples of those that do not: a
  run without a recorded session, and a figure no rerun of its tool reproduces.
