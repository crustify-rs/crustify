# Auditing a crate with Crustify

Crustify's auditor audits a Rust crate that binds a C library or ports one. It looks for
the defects that the crate's project does not know about yet, and it shows each one with
evidence that you can run yourself. It posts nothing: you decide what to report.

This page describes what an audit offers, how to run one on your own crate, and how to
read its results. The auditor's system prompt is [`agents/audit.md`](../agents/audit.md).

## What an audit offers

### Objectives

An audit checks the crate against a list of objectives. Each objective has an identifier,
and the auditor files each finding under the identifier of the objective that the crate
does not meet.

| Identifier | The crate meets the objective if … |
|---|---|
| `ub` | no use of the safe API can cause undefined behavior |
| `contracts` | every unsafe function documents the conditions under which calling it is sound, those conditions suffice, and every unsafe block says why its conditions hold |
| `unsafety` | no unsafe code exists where safe code can do the same work |
| `equiv` | a caller of the crate observes what a caller of the C observes: the same results, errors, output and side effects |
| `correct` | it does what its specification intends, also where the C departs from that specification |
| `ergo` | the API is hard to misuse, and the C's conventions do not leak through it |
| `idiom` | behind the API, the code uses Rust's own means where they fit |
| `api` | a caller can reach every capability of the C through the safe API, and the API does not expose the crate's internals |
| `compat` | where the crate exposes an API for C, C code that uses it as documented cannot break the Rust's invariants |
| `tests` | the tests exercise every behavior that a caller can reach, and the unsafe code in particular |
| `perf` | a caller pays no significant cost over calling the C directly |
| `misc` | it has no defect of a kind that this list does not name |

You choose the objectives in scope, and you can add your own. If the auditor notices a
defect under an objective out of scope, it lists the defect in the report but does not
file it as a finding.

### Evidence

Every finding has evidence. The auditor uses the strongest kind that the defect allows:

1. **A reproducer**, if the defect can be triggered: a program that triggers it through
   the affected API, with the command that runs it and its output.
2. **A witness**, if the defect cannot be triggered but can be measured: a change or a
   measurement that shows the shortfall, with its output.
3. **A review**, if the defect is a matter of judgement: an agent that did not find the
   defect tries to refute it, and fails.

A reproducer does not do what the finding says the code allows. For example, a reproducer
for a defect of the safe API uses no unsafe code. This way, a maintainer can accept the
finding without trusting the agent.

The auditor confirms undefined behavior with the instruments that the environment
provides: AddressSanitizer, LeakSanitizer, MemorySanitizer, ThreadSanitizer,
UndefinedBehaviorSanitizer (for the C code), Miri and BorrowSanitizer.

### Known defects

Before it reproduces a suspected defect, the auditor searches the issues and pull requests
of the crate's project and of the C library's project. If a report or a fix there
describes the same root cause, the defect is known: the auditor records the link and
writes no reproducer for it. This keeps the budget for defects that nobody has reported.

### A target

By default, an audit is not done before it has 25 findings of unknown defects that meet
the bar. Known defects do not count toward the target. You can ask for more or fewer.

The target is there because agents stop early. Without one, an agent can restate the
issues from the project's tracker, judge the crate covered, and stop after a few minutes
with most of the budget unspent. A target that known defects could meet would allow the
same stop.

### Modes

Two modes are off by default. Turn them on in your request:

- **fix**: the auditor patches each finding with the smallest change in the crate's own
  style, turns the reproducer into a regression test, and runs it again.
- **disclose**: the auditor writes a disclosure draft beside each finding, from
  [`templates/disclosure.md`](../templates/disclosure.md). You send the draft.

### Autonomy

- **Autonomous**: the auditor works until the audit is done, without asking anything
  more.
- **Supervised**: the auditor stops after each round of search and triage, shows the
  findings so far and the budget spent, and continues when you say so.

## Requirements

- 64-bit Linux.
- Claude Code. For another harness, see [Other harnesses](#other-harnesses).
- A checkout of the crate at the revision to audit.
- The instruments, for the C code and the Rust code alike. The Docker image of
  [`templates/docker/`](../templates/docker/README.md) has all of them, including Miri,
  the sanitizer toolchains and BorrowSanitizer. Use it unless your machine already has
  them, because the auditor can only show undefined behavior that an available
  instrument checks.

## Run an audit

### In Docker

Build the image once, from the root of the Crustify checkout:

```sh
docker build -f templates/docker/Dockerfile -t crustify .
```

Start a container for the crate, with its checkout at `/target`:

```sh
docker run -d --init --name crustify-audit-mycrate \
    --security-opt seccomp=unconfined \
    -e ANTHROPIC_API_KEY \
    -v /absolute/path/to/mycrate:/target \
    -v crustify-audit-mycrate-work:/work \
    crustify
```

ThreadSanitizer needs `--security-opt seccomp=unconfined`: the default seccomp profile
blocks the call it uses to turn off address randomization.

Open the auditor in the crate's checkout:

```sh
docker exec -it -w /target crustify-audit-mycrate \
    claude --plugin-dir /opt/crustify --agent crustify:audit
```

### Without Docker

Open the auditor in the crate's checkout:

```sh
cd /path/to/mycrate
claude --plugin-dir /path/to/crustify --agent crustify:audit
```

### Other harnesses

[`providers/generic/compose.py`](../providers/generic/compose.py) prints the auditor's
prompt, with an index of the skills, for any harness that can run shell commands, edit
files and spawn subagents:

```sh
python3 /path/to/crustify/providers/generic/compose.py audit
```

The Codex installer sets up the porting agent only.

## Write the request

Name the audit in your first message. If you leave out the objectives, the autonomy or the
level of evidence, the auditor asks for them before it starts. If it cannot ask, it audits
against every objective, works autonomously, and says so in the report.

A request can name:

- **The crate and its revision**, and the parts out of scope, such as a `-sys` crate or a
  vendored C library.
- **The objectives in scope.**
- **The build configuration**: features and targets. Without one, the auditor builds the
  broadest configuration that the machine supports.
- **The budget**, in dollars and wall-clock time.
- **The level of evidence** that you require.
- **The modes**: `fix`, `disclose`, or neither.
- **The target**, if 25 does not fit the crate.
- **Other constraints**, such as reading the network but posting nothing.

For example:

```text
The crate in /target is mycrate at 1a2b3c4, a binding to libfoo. Audit the mycrate crate
only: mycrate-sys and the vendored libfoo are out of scope, except as they explain a
defect in mycrate.

Objectives: ub, contracts and equiv. Configuration: --features "full", and no other
feature. Evidence: a reproducer wherever the defect can be triggered, with the output of
a sanitizer or Miri for undefined behavior. Turn on disclose.

Budget: $50 and 4 hours of wall-clock time, subagents included. Work autonomously. You
may read anything on the network, but post nothing. In the report, also list every suspected
defect that you considered and what became of it.
```

## Read the results

The auditor writes its files under `.crustify/` in the crate's checkout:

```text
.crustify/
├── reviews/
│   ├── REPORT-<date>.md      the audit's report; a later audit adds its own
│   └── <id>/                 one directory per objective: ub, contracts, equiv, …
│       └── <slug>/           one finding: its report, its evidence and, under disclose, disclosure.md
└── tmp/                      scratch builds and downloads; git ignores this directory
```

The report summarizes the audit: its findings, and the defects that the auditor noticed
outside the scope. If you also want every suspected defect and what became of it, ask for
that in the request.

Each `disclosure.md` starts with a header for you: the status of the disclosure, the
severity, the channel that the project asks for, and whether the latest release and the
tip of the default branch show the defect. You send only the body below the `---` line.
Update the status when you send it.

## Before you report a finding

Check each finding yourself before you report it:

1. Rerun its reproducer on a clean checkout, in the configuration that the finding names.
2. Check that the reproducer meets the documented obligations of every unsafe API that it
   calls.
3. Search the project's issues once more, since the project may have changed during the
   audit.
4. Send the report through the channel that the project asks for: a security advisory
   for a defect that an attacker can reach, an issue otherwise.

Agents' findings are almost always real, but agents do not always confirm a finding with
an instrument, and a finding can claim more reach or severity than its evidence shows.

## Tips

- **Name every objective that matters to you.** A narrow scope narrows the search as well
  as the filing.
- **Keep the target, and raise it for a large crate.** The target is what makes an audit
  go on after the obvious defects.
- **Run more than one audit.** Independent audits of the same crate find different
  defects. The auditor divides its own search among subagents for the same reason.
- **Ask for instrument output.** Without that request, agents seldom confirm undefined
  behavior with a sanitizer or Miri.
- **Read the findings under `contracts` closely.** Agents find few incomplete
  contracts, even when asked, and they tend to rate them lower than a person would.

## Limits

- An instrument shows undefined behavior only where it checks for it. Aliasing violations
  across the boundary between Rust and C need BorrowSanitizer, which requires the C
  library to be built from source and linked statically.
- A finding under `equiv` rests on an assertion against the C library. The auditor shows
  a divergence only where the C is the reference.
- A review is weaker evidence than a reproducer. Treat a finding that rests on a review as
  a lead to confirm.
