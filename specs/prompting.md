# Prompting

How Crustify's agent prompts are composed, and where each kind of text lives. The aim is
that every rule is written once, in the one place its kind belongs, so that changing it
changes every agent that follows it, and no two copies drift apart.

## 1. Layers

An agent's system prompt is assembled from three layers and one task-specific section:

| layer | where | voice | holds |
|---|---|---|---|
| specs | `specs/` and its `workflows/`, `planning/`, `rust/` (with `rust/items/`), `verification/`, `operations/` and `artifacts/` | descriptive, third person | what Crustify's artifacts are and how its work is done: workflows, how-tos, conventions, schemas |
| tool specs | `specs/tools/` | descriptive, third person | what each tool is, and how it serves the work each spec describes |
| prompts | `src/crustify/prompts/<role>.md`, and the assistant's `assistant/<campaign>.md` | instructive, second person | a role's identity, inputs, what it owns, its steps and stage-specific guidelines |
| additional instructions | `instructions.md` beside a task's `task.json` | instructive | what one run needs beyond its role |

Each artifact's schema, the meaning of its fields, is described under `specs/artifacts/`,
and an example of each is given under `templates/`, which the schema cites. The settings,
dashboard and `.gitignore` templates there are what a campaign copies to start. Examples
hold illustrations, not rules.

### 1.1 Specs

A spec, or document, describes. It states what an artifact holds, how a decision is made, what a
procedure produces and when each of its steps happens, never what an agent should do, and
never who does a step: which role owns which step is the prompts'. It does not name the
tools that serve it either: a document reads the same whether or not a tool is installed,
so a statement such as "each unit's lifecycle role is established while planning" belongs
in a document, and the wavefront command that records it belongs in wavefront's tool spec.

Two kinds of document describe how work is done. A how-to, such as `items/binding.md` or
`items/porting.md`, describes how one item is handled; the item how-tos sit under
`specs/rust/items/`. A workflow, under `specs/workflows/`,
describes how one kind of campaign proceeds from its settings to its results:
`setup.md`, which every campaign shares, and one document per kind of campaign
(`binding.md`, `porting.md`, `audit.md`). A workflow names the how-tos and the layout
rather than restating them.

Every document's sections are numbered. A reference to a section names it, with or without
its number ("testing.md's Coverage section", "layout § Lifecycle › Waves"), so that a
renumbering never silently points a reference at another section.

A prompt that needs a document includes it whole, with an `<!-- INCLUDE specs/<path> -->`
marker, in the prompt's opening Specs section, where the document's own title introduces
it. An included document
rides in the system prompt, which a long run cannot compact away, and an agent cannot skip
reading it the way it can skip a file it is pointed at. Each document is included by every
role that follows it, and by no role that does not: the reviewer includes the binding and
porting how-tos it reviews against, the planner the conventions its homes follow.

The schemas under `specs/artifacts/` are documents too. They are included where a role
emits or reads the artifact, and are otherwise cited by path, as are their examples.

### 1.2 Prompts

A prompt instructs. It holds what is specific to its role: the role's place among the
agents, its inputs, its workflow steps, and the guidelines that apply to one step or
stage. Where a step follows a document, the prompt names the document's section rather
than restating it ("as the scheduling spec's Order section describes"); where a step
adds to it, the prompt states only the addition.

A prompt states what its role owns by naming the document sections it carries out ("you
create and purge every level of layout's Lifecycle section"), and adds only what the
documents leave to the role: the commands it runs, the judgements it makes, the cases it
must not handle itself.

A prompt is ordered from what every run shares to what one run holds, because a provider
caches a prompt's prefix: two requests reuse the cache up to their first difference. It
opens with its Specs section, the documents it includes, in one order across every role,
the documents most roles include first, so that roles running at once share the longest
prefix: `identity.md`, then every tool's header, which every role carries, then the
documents, each followed by every tool spec that augments it. Its role's own text follows,
with its How the specs apply section, which says what each document is to the role, and
names no value of one run: an integration branch or a batch id is "the one your inputs name". Its `## Inputs`
section, the only one formatted with the run's values, and its `## Additional
instructions` section close it.

A prompt carries an `<!-- INSTRUCTIONS -->` marker in its `## Additional instructions`
section, which a task's instructions file fills, and which states that those instructions
take precedence where they conflict with the rest of the prompt.

The assistant has one prompt for every kind of campaign, `assistant.md`, which carries a
`<!-- CAMPAIGN -->` marker. When the assistant starts, the marker is filled with the
campaign kind's file, `assistant/translate.md` for a port or wrap campaign or
`assistant/audit.md` for an audit. The file holds three parts, which go where the shared
prompt's markers place them: the documents only that kind includes, which close its Specs
section; what the assistant owns in that kind of campaign and its steps; and how those
documents apply, which close its How the specs apply section.

### 1.3 Tool specs

A tool is one program an agent reaches for: wavefront, ffimap, ffibox. Its specs sit under
`specs/tools/`, written as every spec is, descriptively and without naming roles:

- `<tool>/<tool>.md`, its header: what the tool is, which documentation of its own is
  read in full before its first use, and what holds in every use of it. The tool itself is
  installed, on the agent's `PATH` or in its build, by the time an agent runs; and
- `<tool>/<spec path>`, how the tool serves the spec at that path, `<spec path>` mirroring
  the spec tree: `wavefront/rust/items/binding.md` augments `rust/items/binding.md`. It
  opens with `# <tool> › <spec path>`, and each of its sections is named after the section
  of that spec it augments, stating only what the tool adds to it.

Every prompt includes every tool's header, in its Specs section, and each document it
includes is followed by every tool spec that augments it, so that two roles that include a
document share its text and its tools' uses. A tool spec that is missing includes as nothing: a tool is ablated by deleting
its header, and one of its uses by deleting that augmentation.

## 2. Placement

| text | goes in |
|---|---|
| what an artifact's fields mean | its schema under `specs/artifacts/` |
| what an artifact looks like | its example under `templates/` |
| how a kind of work is done, independent of tools | the document for that work |
| how a kind of campaign proceeds, step by step | its workflow under `specs/workflows/`, with the steps every campaign shares in `setup.md` |
| a convention every role follows | `specs/rust/conventions.md` |
| what one role does, in which steps, and which steps it owns | that role's prompt |
| what the assistant does in one kind of campaign | `src/crustify/prompts/assistant/<kind>.md` |
| how a tool serves a spec | `specs/tools/<tool>/<spec path>` |
| what a tool is, and what holds in every use of it | `specs/tools/<tool>/<tool>.md` |
| what one run needs beyond its role | that task's `instructions.md` |

A rule that two roles share goes in a document both include, not in both prompts. A
rule that names a tool goes in the tool's spec, not in a document. A change to a rule is
made where the rule lives; text that restates it elsewhere is removed rather than kept in
step.
