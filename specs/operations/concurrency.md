# Concurrency

How a campaign's work shares the host it runs on: how much of it runs at once, and how
the builds, tests and gates inside it are parallelized. What runs in which order is
[scheduling](../planning/scheduling.md)'s; this spec describes only how much of what may run is in
flight.

## 1. Principle

Concurrency is maximized given the resources and the parallel workloads that share them,
without lengthening the latency of any unit of work. The resources are the host's cores,
memory, disk and I/O, and the providers' request rates. The parallel workloads are
everything that runs on the host at once: the campaign's agents, the agents of its side
campaigns and of other campaigns on the same host, the shared rebuilds of the target's
variants, and the gates each agent runs.

Concurrency is therefore decided when work starts, from the state of the host at that
moment, and revised as that state changes. No committed artifact fixes it.

## 2. Agents

An agent spends most of its time waiting on its model, and only part of it building and
testing. More agents can be in flight than the host has cores; what bounds them is how
much of their building and testing overlaps, the memory and disk each one's tree takes, and
the rate the provider allows.

The number of agents in flight follows from those, for each wave as it starts and again as
its batches land or fail. A `parallelism` number in the settings is a cap on it; the
default, `assistant's choice`, sets none. When the waves of several modules, campaigns,
or of a campaign and its side campaigns, run at once, they share the host as one workload.

One unit of work may be given priority over another by suspending the other's agents, with
every process of their trees, and resuming them once the first has finished. A suspended
agent keeps its state; its interval then includes the suspension, and its record says so.

## 3. Jobs

Each build, test run and gate takes its parallelism when it starts, from the jobs already
running on the host: the job count of a build, the threads of a test binary, and the
number of gate invocations run side by side, such as Miri's or BSan's one per test binary.
The jobs of every workload on the host add up to about its core count: a workload that
runs alone takes the whole host, and one among many takes its share.

The jobs actually running are the measure, not the load average alone, which lags them and
counts what waits on I/O. Memory bounds a job count as well as cores do: a link or a
sanitized test binary can need more memory than a core's share.

The parallelism is given to each command through its environment, so that no command
carries it: `MAKEFLAGS=-j<n>` for Make, `CMAKE_BUILD_PARALLEL_LEVEL=<n>` for CMake,
`CARGO_BUILD_JOBS=<n>` for Cargo, and `RUST_TEST_THREADS=<n>` for Rust tests, or the build
system's own equivalent.

## 4. Artifacts

`crustify/artifacts/build.json`'s commands carry no job count. A job count does not change
what a build produces, so it is no part of a variant: adding or removing one does not
change the variant, and does not raise the file's `version`. The settings' `parallelism`,
when set, is the only number a campaign records, and it is a cap.
