---
name: reviewing
description: "How a port is reviewed: for each requirement of the ported code, whether it has been met as fully as it can be, every way it could be met better as a finding, the evidence each carries, and how findings are fixed. Read before reviewing, briefing a reviewer, or fixing what a review found."
---

# Reviewing

A reviewer is a subagent that wrote none of the code it reviews. For each requirement the
system prompt sets the ported code, it asks: has this requirement been met as fully as it
can be? Every way the code could meet it better is a finding, of the kind named by the
requirement's identifier, filed at `.crustify/reviews/<kind>/<slug>/`, as
[`layout`](../../operations/layout/SKILL.md) places it; what falls under no requirement is
`misc`. A brief may narrow the requirements a review asks
about. The findings are fixed, and review goes on until a reviewer finds no way left to do
better on any requirement. A finding marked fixed is checked by rerunning its reproducer.

## Evidence

A finding's directory holds `finding.md`, which says what falls short, where, and why, and
the evidence for it. The evidence is a reproducer wherever one is possible: a test, a
program or a measurement that shows the shortfall from a clean checkout, with the command
that runs it and the output it gave, such as a sanitizer's or Miri's report, a failing
assertion or the numbers. The reproducer sits beside `finding.md`. Where no reproducer is
possible, the evidence is prose: the argument from the code, step by step, and why no
reproducer could show it. A later review updates `finding.md` in place: whether the
finding still holds, and the commit that fixed it.

## Fixes

Who fixes a finding, its author, its reviewer or another agent, is the agent's choice. A
finding with a reproducer is fixed with a regression test made from it: a UB test that
runs clean under the instrument that caught it, or fails to compile because the fix
removed the safe path to the defect; an equivalence test; or a unit test. A `contracts`
finding is fixed in the contract, or, where the contract can be broken, in the code it
guards. A `tests` finding is fixed by the tests it asks for, with the coverage they add.
