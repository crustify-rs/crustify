# Goals

What Crustify is for, how it evolves, and what every change to it, its skills, its agents and its tools,
is judged against. A rule that serves none of these goals is removed; two goals in tension
are weighed for the case at hand, and the weighing is stated.

The goals evolve too, from the same evidence as everything else: a goal the campaigns keep
missing, one no decision ever cites, two that keep conflicting the same way, or a
well-founded change that none of them serves. A change to them is proposed as Crustify's
`evolution` skill describes, and lands only with the user's approval.

1. **Safety.** No undefined behaviour is reachable from safe Rust, and the unsafe code that
   remains sits in its regions, sound for every input.
2. **Fidelity.** The Rust keeps the C's specified behaviour, not its bugs: what the C's
   documentation, tests and consumers rely on.
3. **Idiomatic Rust.** The API a Rust consumer sees is native Rust: ownership, borrowing,
   errors, iteration and traits, not C's conventions behind a Rust syntax.
4. **Performance.** The emitted Rust costs no more than native Rust would, and the harness
   spends tokens and time where they buy accuracy.
5. **Verification.** What the agents produce is machine-checked wherever it can be, by
   types, lints, sanitizers, Miri, schemas, deterministic tools and compile-time
   assertions, rather than left to an agent's judgement.
6. **Maintainability.** Established software engineering practice and reuse keep the
   emitted Rust and the harness itself maintainable for the long term: one place for each
   rule and each piece of code, standard libraries and idioms before new ones.
7. **Interoperability.** C and Rust work together soundly in both directions for as long
   as both remain, each reaching the other through the boundary in its own conventions,
   and the Rust works with the Rust ecosystem: the standard library's types and traits,
   and existing crates where they serve.
8. **Incremental migration without breaking consumers.** A codebase moves to Rust one
   module at a time, every landing builds and passes its gates, and no consumer breaks: a
   C or Rust consumer's code does not change as what it consumes is wrapped, ported or
   moves through its later stages.
9. **Generality.** The rules hold for any C codebase: what holds for one target alone is
   that target's lesson, not a rule.
10. **Least constraint.** A rule states what must hold and leaves how to the agent, unless
    the how is itself what must hold.
11. **Determinism and attribution.** Every fact a decision rests on can be reproduced, and
    every change traces back to the run, and the revisions, that made it.
