# Translating C to Rust

Point Crustify at your C repository, and it produces Rust in one of two ways:

- **`wrap`** keeps your C and puts a safe Rust API in front of it. You get a bindings
  crate.
- **`port`** replaces your C with safe Rust, one module at a time. The C that remains is
  reached through wrappers until its own module is ported.

To review a crate that already exists, see [Auditing a Rust crate](audit.md).

## Why translate with Crustify

- **You scope it.** Name the modules, or the functions and types, that you want, or give
  it the whole repository. Planner runs decompose that scope into modules and schedule
  them into waves by their dependencies.
- **You do not coordinate the work.** Each wave is divided into batches. A binder or a
  translator takes one batch, in its own Git worktree, and the batches of a wave run in
  parallel. The assistant lands their work, promotes it and repairs what fails.
- **You get consistent code.** Every agent follows one written specification of how each
  kind of C item becomes Rust. Two agents, or two models, therefore make the same choice
  for the same kind of item.
- **You get tests with the code.** Each batch comes with coverage-guided unit tests, tests
  for equivalence with your C, and tests for undefined behavior. They run under Miri,
  ASan, UBSan, TSan, MSan and BorrowSanitizer.
- **Nothing lands that breaks your build.** A batch lands only when its tree passes the
  regression gates. Where a batch changes C, the gates include your own test suite.
- **Someone tries to break it before you do.** Reviewers check what each wave landed
  before its dependents start, for the same objectives as an [audit](audit.md). They file
  a report and a reproducer for each finding, and they fix it when the objectives include
  `fix`.
- **You decide what ships.** `main` advances to what has been integrated only at the ship
  points that you name, and only when you approve.
- **You choose how closely to watch.** Let a campaign run end to end, or have it wait for
  your approval at the points that you name. You can edit its settings while it runs.
- **You see what it costs.** The dashboard records tokens, cost and time for each batch,
  module and campaign, next to coverage and the unsafe surface.

## How to

### 1. Prepare the environment

Use the Docker image, which holds the agent CLIs, CodeQL, bindgen, Miri and the sanitizer
toolchains. [`templates/docker/README.md`](../templates/docker/README.md) describes how to
build it and start a container. Mount the directory the campaign is to work in as
`/target`. It may be empty: Crustify creates the campaign's repository there and fetches
the C.

To run without Docker, install Crustify and its tools as the
[README](../README.md#installation) describes.

### 2. Answer the settings

Fill in
[`templates/translate/CRUSTIFY.template.md`](../templates/translate/CRUSTIFY.template.md),
or let the assistant ask. Six answers are mandatory:

| setting | what it decides |
|---|---|
| `source` | your C repository and the revision to translate |
| `campaign` | `wrap` or `port` |
| `scope` | named modules, named functions and types, the whole repository, or the assistant's choice |
| `translate-agent` | the agent CLI, its model and how it is paid for |
| `review-agent` | whether reviewers check what lands, and with which agent CLI |
| `autonomy` | whether the campaign runs end to end or waits for your approval at named points |

The optional answers cap the batches and the parallelism, select the review objectives and
the sanitizers, configure the target's build and name the points at which the result
ships. Each has a default.

### 3. Start the campaign

Open the translation assistant in the campaign's directory:

```bash
claude --plugin-dir /path/to/crustify --agent crustify:assistant-translate
```

Tell it what you want in plain language, such as "wrap the public API" or "port the
parser". It presents a brief for your approval before it changes anything.

### 4. What the campaign does

1. **Setup.** It creates the campaign's repository, builds your code in each variant
   that the tests run against and records a baseline of your own tests.
2. **Planning.** Planner runs decompose the repository into modules and schedule them
   into waves by their dependencies.
3. **Waves.** Each wave's batches run in parallel. A binder wraps a batch, or a translator
   ports it. Each batch passes its tests and gates before it lands on the wave's branch.
4. **Review.** Reviewers check what the wave landed and file a report and a reproducer
   for each finding. They fix it when the review objectives include `fix`.
5. **Integration.** Once a module's last wave is promoted, the module joins the working
   branch. In a port, this is where the module switches from C to Rust.
6. **Shipping.** At each ship point, the assistant asks whether `main` should advance to
   what has been integrated. It moves `main` only with your approval.

### 5. Read the results

The campaign's repository holds the Rust at its root, the C under `c/` and the campaign's
own state under `crustify/`:

| path | holds |
|---|---|
| `crustify/CRUSTIFY.md` | the settings, which you can edit while the campaign runs |
| `crustify/artifacts/dashboard.md` | progress, coverage, the unsafe surface, and tokens, cost and time |
| `crustify/reviews/` | the review reports and their reproducers |

Work lands on the working branch, `crustify/devel`. `main` is the shipping branch.

### 6. Change course

Edit `crustify/CRUSTIFY.md` to change a setting, such as a model or a batch size. Crustify
rereads it before each module. A later session in the repository resumes the campaign.

## Reference

- [`setup`](../skills/workflows/setup/SKILL.md): how every campaign starts
- [`binding-workflow`](../skills/workflows/binding-workflow/SKILL.md): how a `wrap`
  campaign proceeds
- [`porting-workflow`](../skills/workflows/porting-workflow/SKILL.md): where a `port`
  campaign differs
- [`binding`](../skills/rust/binding/SKILL.md) and
  [`porting`](../skills/rust/porting/SKILL.md): how each C item is handled
