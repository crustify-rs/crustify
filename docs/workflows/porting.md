# Porting workflow

How a `port` campaign proceeds. It follows the [binding workflow](binding.md) throughout;
this document gives only where it differs. How each item is ported is
[`../porting.md`](../porting.md).

## 1. Batches

A port campaign's schedule mixes both kinds of batch, as [`../planning.md`](../planning.md)'s
Waves and batches section describes: a selected symbol is `port` from the start, a
selected type is `wrap` while C depends on its layout and `port` once nothing in C does,
and a dependency outside the selected migration set stays `wrap`. Each batch runs the agent
its objective names, in the same waves.

## 2. Builds

A `port` batch changes the compiled target: it guards the C bodies it replaces and links
the Rust exports in their place. Its gates therefore include the C build and baseline,
with the Rust feature off and on, as [`../testing.md`](../testing.md)'s Regressions
section describes, and the shared variants are rebuilt once it lands.

## 3. Scope

The unit of a port is a module: its scope is whole modules, the foundational ones
included. Porting a few named items without their module is not described.
