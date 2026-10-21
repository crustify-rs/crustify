# Prompting

How Crustify's agent prompts are composed, and where each kind of text lives. The aim is
that every rule is written once, in the one place its kind belongs, so that changing it
changes every agent that follows it, and no two copies drift apart.

## 1. Layers

An agent's system prompt is assembled from three layers and one task-specific section:

| layer | where | voice | holds |
|---|---|---|---|
| documents | `docs/`, `docs/workflows/`, `docs/artifacts/` | descriptive, third person | what Crustify's artifacts are and how its work is done: workflows, how-tos, conventions, schemas |
| prompts | `src/crustify/prompts/<role>.md`, and the assistant's `assistant/<campaign>.md` | instructive, second person | a role's identity, inputs, what it owns, its steps and stage-specific guidelines |
| skills | `src/crustify/prompts/skills/<skill>/` | instructive, second person | how one tool serves the work: its metadata, and per role, how that role uses it |
| additional instructions | `instructions.md` beside a task's `task.json` | instructive | what one run needs beyond its role |

Each artifact's schema, the meaning of its fields, is described under `docs/artifacts/`,
and an example of each is given under `templates/`, which the schema cites. The settings,
dashboard and `.gitignore` templates there are what a campaign copies to start. Examples
hold illustrations, not rules.

### 1.1 Documents

A document describes. It states what an artifact holds, how a decision is made, what a
procedure produces and when each of its steps happens, never what an agent should do, and
never who does a step: which role owns which step is the prompts'. It does not name the
tools that serve it either: a document reads the same whether or not a skill is installed,
so a statement such as "each unit's lifecycle role is established while planning" belongs
in a document, and the wavefront command that records it belongs in wavefront's skill.

Two kinds of document describe how work is done. A how-to, such as `binding.md` or
`porting.md`, describes how one item is handled. A workflow, under `docs/workflows/`,
describes how one kind of campaign proceeds from its settings to its results:
`setup.md`, which every campaign shares, and one document per kind of campaign
(`binding.md`, `porting.md`, `audit.md`). A workflow names the how-tos and the layout
rather than restating them.

Every document's sections are numbered. A reference to a section names it, with or without
its number ("testing.md's Coverage section", "layout § Lifecycle › Waves"), so that a
renumbering never silently points a reference at another section.

A prompt that needs a document includes it whole, with an `<!-- INCLUDE docs/<path> -->`
marker, introduced by one sentence saying what the document covers. An included document
rides in the system prompt, which a long run cannot compact away, and an agent cannot skip
reading it the way it can skip a file it is pointed at. Each document is included by every
role that follows it, and by no role that does not: the reviewer includes the binding and
porting how-tos it reviews against, the planner the conventions its homes follow.

The schemas under `docs/artifacts/` are documents too. They are included where a role
emits or reads the artifact, and are otherwise cited by path, as are their examples.

### 1.2 Prompts

A prompt instructs. It holds what is specific to its role: the role's place among the
agents, its inputs, its workflow steps, and the guidelines that apply to one step or
stage. Where a step follows a document, the prompt names the document's section rather
than restating it ("as the planning instructions' Order section describes"); where a step
adds to it, the prompt states only the addition.

A prompt states what its role owns by naming the document sections it carries out ("you
create and purge every level of layout's Lifecycle section"), and adds only what the
documents leave to the role: the commands it runs, the judgements it makes, the cases it
must not handle itself.

A prompt carries an `<!-- INSTRUCTIONS -->` marker in its `## Additional instructions`
section, which a task's instructions file fills, and which states that those instructions
take precedence where they conflict with the rest of the prompt. It carries a
`<!-- SKILLS -->` marker where the skill index belongs relative to its task.

The assistant has one prompt for every kind of campaign, `assistant.md`, which carries a
`<!-- CAMPAIGN -->` marker. When the assistant starts, the marker is filled with the
campaign kind's file, `assistant/translate.md` for a port or wrap campaign or
`assistant/audit.md` for an audit: what the assistant owns in that kind of campaign, its
steps, and the workflows and documents that kind includes. The assistant's skills keep one
file per campaign kind, `<kind>-assistant.md`, since a tool can serve the kinds
differently.

### 1.3 Skills

A skill is one tool an agent reaches for on demand. Its directory holds:

- `SKILL.md`, the generic header: the skill's name, description, binary and the document
  it points to, which the skill index lists for every role that carries the skill. The
  description is the routing signal; the agent reads the skill's document in full when
  the description matches its work; and
- one `<role>.md` per role that carries the skill, with a single `<!-- SKILL -->` anchor,
  holding that role's guidance for the tool. Each section augments one section of the
  role's documents or workflow, named as `<document> › <section>`, where a workflow is
  named `workflows/<name>`, or `For <step>`, and states only what the tool adds to it.

A skill is present in a role's prompt exactly when its files are on disk: deleting a
role's file removes the skill from that role, and deleting the directory removes it from
every role. The skill index rides in the system prompt; the tool's own documentation is
read on demand.

## 2. Placement

| text | goes in |
|---|---|
| what an artifact's fields mean | its schema under `docs/artifacts/` |
| what an artifact looks like | its example under `templates/` |
| how a kind of work is done, independent of tools | the document for that work |
| how a kind of campaign proceeds, step by step | its workflow under `docs/workflows/`, with the steps every campaign shares in `setup.md` |
| a convention every role follows | `docs/conventions.md` |
| what one role does, in which steps, and which steps it owns | that role's prompt |
| what the assistant does in one kind of campaign | `src/crustify/prompts/assistant/<kind>.md` |
| how a tool serves a step or a section | the tool's skill, in the file of each role that uses it |
| what a tool is and when to reach for it | the tool's `SKILL.md` |
| what one run needs beyond its role | that task's `instructions.md` |

A rule that two roles share goes in a document both include, not in both prompts. A
rule that names a tool goes in the tool's skill, not in a document. A change to a rule is
made where the rule lives; text that restates it elsewhere is removed rather than kept in
step.
