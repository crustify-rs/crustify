# Evolution record

Every change to Crustify and its tools that landed, and whether it held, as the
`evolution` skill's Record section describes. One entry per change, newest last. A status
is `watched`, `recurred`, with the evidence, or `confirmed`, with the campaign that
confirmed it; a change with `test` or `none` as its recurrence signal has no status.

| change | from | landed as | signal answered | recurrence signal | status |
|---|---|---|---|---|---|
| an item wrapped ahead is held by one batch across the campaign | a read of the spec, no campaign | crustify `93674e1`, `66e2ae8` | two modules running at once could each bind the same unlanded item | a module integration that conflicts on one item bound twice, or a review finding of a duplicate binding | watched |
| a holder that outlives its agent is ended by its pid | a read of the spec, no campaign | crustify `af5dc69` | ending a stalled subagent left its landing lock held | a wave whose landings wait on a lock whose holder's agent has ended | watched |
| a fix that unblocks a run is landed or asked for at once | a read of the spec, no campaign | crustify `37683f4` | a blocked run had no path to its fix under the default autonomy | a run that works around a tool's defect, or stays failed until a module's end for want of an approval | watched |
| every run records the revisions it launched under | a read of the spec, no campaign | crustify `ac9c126` | `revisions` was optional, so a run's rules could not be told | a `task.json` without `revisions` | watched |
