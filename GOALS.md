# Goals

What Crustify is for, how it evolves, and what every change to it, its skills, its agents and its tools,
is judged against. A rule that serves none of these goals is removed; two goals in tension
are weighed for the case at hand, and the weighing is stated.

The goals evolve too, from the same evidence as everything else: a goal the campaigns keep
missing, one no decision ever cites, two that keep conflicting the same way, or a
well-founded change that none of them serves. A change to them is proposed as Crustify's
`evolution` skill describes, and lands only with the user's approval.

Each goal names its fitness: what a campaign measures to tell how far the goal is met, read
from what its runs produce anyway, the dashboard, the review reports, the gates and the
plan, without a run made only to take it. A measure that worse work could improve is paired
with the one that catches it, and neither is read alone: fewer findings is no gain when
more escape, nor cheaper work when it is redone. A measure no campaign takes yet says so;
until it is taken, its goal is judged, not measured.

1. **Safety.** No undefined behaviour is reachable from safe Rust, and the unsafe code that
   remains sits in its regions, sound for every input.
   - *Fitness, the unsafe surface:* what a deterministic scan counts on each landing: raw
     pointers and `unsafe fn`s on the public API, unsafe lines, raw dereferences, and unsafe
     code outside its regions. It falls as a module goes from wrapped to ported and through
     its later stages, and the last is zero.
   - *Fitness, soundness:* the defects a reproducer proves, undefined behaviour and
     contracts that can be broken, per unsafe site reviewed. Paired with the escapes among
     them: those a later tier caught than the one that read the code first, a module pass
     after a wave's review, a switch, a revisit, a ship point's gates.
2. **Equivalence.** The Rust keeps the C's specified behaviour, not its bugs: what the C's
   documentation, tests and consumers rely on.
   - *Fitness:* the inputs and states on which the Rust is compared with the C it
     replaces, with no difference left unexplained; the target's own tests passing over
     the Rust at each switch, against their recorded baseline; and the differences made on
     purpose, each documented and held by a test. Paired with the differences found after
     the comparison ended: by a review, at a switch, or by a consumer.
3. **Idiomatic Rust.** The API a Rust consumer sees is native Rust: ownership, borrowing,
   errors, iteration and traits, not C's conventions behind a Rust syntax.
   - *Fitness:* the ergonomics and idiom findings reviews file, per item reviewed, and the
     C forms the scan still counts on the public API: raw and untyped pointers, and
     obligations handed to callers.
4. **Performance.** The emitted Rust costs no more than native Rust would, and the harness
   spends tokens and time where they buy accuracy.
   - *Fitness, the harness:* cost and wall time per translated item, reviews and switches
     included, read beside what was redone, batches run again, gates rerun and merges made
     twice, and never apart from Safety's and Equivalence's measures.
   - *Fitness, the emitted Rust:* its time and memory against the C it replaces, on the
     target's own workloads. Not taken yet.
     <!-- TODO: no campaign benchmarks what it ports; which workloads, and at which event,
     is not specified. -->
5. **Verification.** What the agents produce is machine-checked wherever it can be, by
   types, lints, sanitizers, Miri, schemas, deterministic tools and compile-time
   assertions, rather than left to an agent's judgement.
   - *Fitness:* the coverage of the ported Rust, by lines and regions, and the states and
     transitions its tests reach. Paired with the share of deliberate faults those tests
     catch, since code that runs is not code that is checked, which is taken only where a
     review seeds them, and with the gate results a run reported that its landed tree does
     not reproduce.
     <!-- TODO: seeding faults is not a step of any stage yet. -->
6. **Maintainability.** Established software engineering practice and reuse keep the
   emitted Rust and the harness itself maintainable for the long term: one place for each
   rule and each piece of code, standard libraries and idioms before new ones.
   - *Fitness:* what was reused against what was made again: owners, callbacks and
     lifecycles built from the shared primitives rather than by hand, as the scan counts
     them; library entities reached through the standard library or an adopted crate
     rather than a new binding; and the rules, lessons and scripts a module took as they
     were. A procedure worked out by hand a second time, and a proposal that repeats
     another's signal, count against it.
7. **Interoperability.** C and Rust work together soundly in both directions for as long
   as both remain, each reaching the other through the boundary in its own conventions,
   and the Rust works with the Rust ecosystem: the standard library's types and traits,
   and existing crates where they serve.
   - *Fitness:* the kinds of crossing a campaign exercises and passes, in each direction:
     exports checked against the C declarations they replace, callbacks C makes into Rust
     and Rust into C, layouts and storage the remaining C shares, the build modes and
     variants the crate builds and tests in, and the remaining C's tests over the Rust
     link.
8. **Incremental migration without breaking consumers.** A codebase moves to Rust one
   module at a time, every landing builds and passes its gates, and no consumer breaks: a
   C or Rust consumer's code does not change as what it consumes is wrapped, ported or
   moves through its later stages.
   - *Fitness:* the items whose API changed or went after their first landing, each with
     its reason; the landed trees that failed a gate; the target's test baseline, which
     moves only by the cases carried over; and the batches that met a dependency not yet
     landed, and waited for it, rewrote around it or reached past its wrapper.
9. **Generality.** The rules hold for any C codebase: what holds for one target alone is
   that target's lesson, not a rule.
   - *Fitness:* of what a campaign's evidence taught, the share stated as rules without
     the target's names against the share kept as its lessons, and the rules a second
     target could not follow as written.
10. **Least constraint.** A rule states what must hold and leaves how to the agent, unless
    the how is itself what must hold.
    - *Fitness:* the rules a run worked around, rewrote sound code to satisfy, or reported
      as forcing a worse result, per module.
11. **Determinism.** One kind of item is translated one way: the same C shape takes the
    same Rust pattern, the one the conventions and the how-to skills give it, whichever
    agent, batch or campaign translates it, and a departure states its reason.
    - *Fitness:* how often one kind of item takes one pattern: the conventions findings
      per item, the items a later batch or review reshaped, and, where an item was
      translated twice, whether both runs gave it the same shape. Paired with the
      departures: those that state their reason against those a review had to find.
12. **Attribution.** Every fact a decision rests on can be reproduced, and every change
    traces back to the run, and the revisions, that made it.
    - *Fitness:* the landed commits, dashboard cells and decisions that trace to a run, its
      session and its revisions, against those that do not: a run without a recorded
      session, a figure no rerun of its tool reproduces.
