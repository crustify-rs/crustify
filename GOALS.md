# Goals

What Crustify is for, and what every change to it, its skills, its agents and its tools,
is judged against. A rule that serves none of these goals is removed; two goals in tension
are weighed for the case at hand, and the weighing is stated.

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
7. **Incrementality.** Every landing builds and passes its gates, and a consumer's code
   does not change between the stages of what it consumes.
8. **Generality.** The rules hold for any C codebase: what holds for one target alone is
   that target's lesson, not a rule.
9. **Least constraint.** A rule states what must hold and leaves how to the agent, unless
   the how is itself what must hold.
10. **Determinism and attribution.** Every fact a decision rests on can be reproduced, and
    every change traces back to the run, and the revisions, that made it.
