---
name: reviewing
description: "How a port is reviewed: for each requirement of the ported code, whether it has been met as fully as it can be, every way it could be met better as a finding, and how findings are fixed. reviewing-reports gives how findings and reproducers are filed. Read before reviewing, briefing a reviewer, or fixing what a review found."
---

# Reviewing

A reviewer is a subagent that wrote none of the code it reviews. For each requirement the
system prompt sets the ported code, it asks: has this requirement been met as fully as it
can be? Every way the code could meet it better is a finding, of the kind named by the
requirement's identifier, filed as [`reviewing-reports`](reports/SKILL.md) describes; what
falls under no requirement is `misc`. A brief may narrow the requirements a review asks
about. The findings are fixed, and review goes on until a reviewer finds no way left to do
better on any requirement. A finding marked fixed is checked by rerunning its reproducer.

A reviewer reads the code itself, and tries to break what it reads: an input, a call
sequence or an interleaving that a contract allows and still reaches undefined behaviour or
a wrong result. What a tool reports shows where to start and cross-checks what the reading
found; it never bounds the review.

## Fixes

Who fixes a finding, its author, its reviewer or another agent, is the agent's choice. A
finding with a reproducer is fixed with a regression test made from it: a UB test that
runs clean under the instrument that caught it, or fails to compile because the fix
removed the safe path to the defect; an equivalence test; or a unit test. A `contracts`
finding is fixed in the contract, or, where the contract can be broken, in the code it
guards. A `tests` finding is fixed by the tests it asks for, with the coverage they add.
