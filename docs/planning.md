# Planning

Planning turns a campaign's settings and the target's build into the plan its agents
execute: the subsystem decomposition, `crustify/artifacts/subsystems.json`, which also
orders the campaign's link units and subsystems, one
`crustify/artifacts/<link-unit>/<subsystem>/schedule.json` per subsystem with its waves
and batches, and the planning artifacts of the enabled skills.

A plan is bounded by the campaign's settings in `crustify/CRUSTIFY.md`: its `campaign`
(port or wrap), `scope`, `target-config` and `workload` answers. A feature the target is
configured without is out of scope. The plan derives from the builds recorded in
`crustify/artifacts/build.json` and the linker outputs of those builds; planning changes
neither the build nor the Rust tree.

## Runs

A campaign is planned by one or more planner runs, one after another on the campaign
branch, each in one commit. Each run brings the committed plan up to date, so a later
run checks what the earlier ones decided, and the branch history records every planning
decision and its revisions. A run that corrects an earlier decision files a report on it, as
[`reviewing.md`](reviewing.md#plan-corrections) describes.

## Subsystem decomposition

`subsystems.json` follows [`artifacts/subsystems.md`](artifacts/subsystems.md); its layout
example is [`templates/subsystems.json`](../templates/subsystems.json).

Link units are identified from the actual linker outputs. The decomposition covers the
selected target and its complete imported producer closure. Every translation unit
belongs to exactly one subsystem; a header may be shared by several. A subsystem's
`api_headers` are the headers the build installs, listed with the subsystem that
implements them.

Each subsystem carries one objective:

- `port`: project-specific behaviour or invariants, implemented in Rust;
- `wrap`: generic facilities, kept behind a safe Rust API over the C.

A mixed subsystem is split, so that its project-specific code and its generic facilities
carry separate objectives. In a wrap campaign every subsystem is `wrap`. In a port
campaign the project-specific subsystems are `port`, and those with Rust-native
alternatives stay `wrap`, so that their Rust consumers stay interoperable with the
remaining C during an incremental translation, until they can be nativized. A subsystem's
`rust_native_equivalent` lists the established Rust crates or `std` facilities that could
replace it outright, in descending order of fit, each checked for its semantics,
platform support, performance and licensing.

Each consumer-to-producer relation is one `imported_deps` record, with its
`outgoing_edges`, its `incoming_edges` and the item kinds consumed across them, in-tree
destinations apart from out-of-tree libraries. The record keeps the graph as it is,
cycles included.

## Order

`subsystems.json` lists the campaign's link units and subsystems in execution order,
bottom-up by their dependency relations, each with its `index`. The order is a DAG cut
from the graph of link units and subsystems, as
[`artifacts/subsystems.md`](artifacts/subsystems.md) describes: within each strongly
connected component, the member the most other members depend on comes first, and the
edges between tied members break ties.

The plan holds only the link units and subsystems the campaign's scope includes, without
those that this campaign, before it was resumed, or a previous campaign completed. The
raw-lifetime discoveries for `void` and `string` are the only synthetic subsystems:
campaign leaves listed first in the first link unit, with only their `index` and `name`.
They run first.

## Waves and batches

Each subsystem's `schedule.json` follows [`artifacts/schedule.md`](artifacts/schedule.md);
its layout example is [`templates/schedule.json`](../templates/schedule.json). It holds only
that subsystem's waves, and the raw-lifetime subsystems have one too. Waves execute
sequentially, bottom-up, producers before consumers; the batches of a wave execute in
parallel, up to the campaign's parallelism, and the `workload` caps bound each batch.

A batch entry is a `task.json` without the run fields the orchestrator adds when it
launches the batch (`base_branch`, `model` and `billing`):
[`artifacts/task.md`](artifacts/task.md) gives its format, routing and the raw-lifetime
rule. Each item's `home` follows the [conventions](conventions.md).

Raw and typed lifecycle primitives stay in the schedules as free symbols, although the
raw-lifetime subsystems and the type batches discover them on the fly; their binders
skip them.

In a wrap campaign every batch is `wrap`. In a port campaign:

- a selected symbol is `port` from the start;
- a selected type is `wrap` while C depends on its layout, then `port` once nothing in C
  does, as [Porting types](#porting-types) describes; and
- a dependency outside the selected migration set is `wrap`.

### Porting types

A selected type is scheduled twice: a `wrap` batch where the DAG places it, and a `port`
batch once its layout leaves C, when no C code that remains after a wave depends on it.
Its C users are:

- code that touches a field: reads or writes it, or takes its address;
- code that depends on the layout without naming a field: `sizeof`, `_Alignof` or
  `offsetof` on the type (`sizeof *p`, and macros such as `container_of`, included); a
  value of the type, as a local, a parameter or return, a global, a copy or a compound
  literal; pointer arithmetic or indexing on a pointer to it; and
- another struct, or an array, that embeds it by value and so carries its layout.

No tool lists the second and third kinds: they are found in the source, in every
function that mentions the type, its globals and the struct fields declared with it,
macro expansions included.

The `port` batch goes in the first wave after the one that ports the type's last C user.
A type keeps only its `wrap` batch, and its C layout, while a C user stays: one outside
the selected migration set, an embedding struct that stays C, or a definition in an
installed header, whose concrete body every public C consumer receives.
