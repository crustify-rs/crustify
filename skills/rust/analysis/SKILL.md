---
name: analysis
description: "How a scheduled C item is analysed before it is bound or ported: what is inspected, what the analysis establishes and how its findings shape the Rust. Read before binding or porting any item, and when reviewing either."
---

# Item analysis

How a scheduled C item is analysed before it is bound or ported. The analysis is the same
for both: what it establishes shapes the binding or port that follows.

## 1. Scope

Each item is analysed from its source declarations and definitions, its dependency closure,
its callers, its field touchers and its existing Rust consumers. For every pointer field,
argument and return, every code path that stores, transfers, clones, retains or frees it is
inspected.

## 2. Findings

The analysis establishes:

- ownership and transfer direction;
- shared or mutable access;
- nullability;
- scalar, array, or other cardinality;
- type erasure and known element types;
- borrow and keepalive relationships; and
- construction, clone, and destruction paths.

Observed behaviour overrides names and comments. A distinction the analysis establishes is
preserved in Rust rather than flattened into a copy of an ambiguous C signature.
