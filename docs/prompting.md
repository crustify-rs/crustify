# Prompting

How Crustify's agent prompts are composed, and where each kind of text lives. The aim is
that every rule is written once, in the one place its kind belongs, so that changing it
changes every agent that follows it, and no two copies drift apart.

## Layers

An agent's system prompt is assembled from three layers and one task-specific section:

| layer | where | voice | holds |
|---|---|---|---|
| documents | `docs/`, `docs/artifacts/` | descriptive, third person | what Crustify's artifacts are and how its work is done: workflows, how-tos, conventions, schemas |
| prompts | `src/crustify/prompts/<role>.md` | instructive, second person | a role's identity, inputs, steps and stage-specific guidelines |
| skills | `src/crustify/prompts/skills/<skill>/` | instructive, second person | how one tool serves the work: its metadata, and per role, how that role uses it |
| additional instructions | `instructions.md` beside a task's `task.json` | instructive | what one run needs beyond its role |

Each artifact's schema, the meaning of its fields, is described under `docs/artifacts/`,
and an example of each is given under `templates/`, which the schema cites. The settings,
dashboard and `.gitignore` templates there are what a campaign copies to start. Examples
hold illustrations, not rules.

### Documents

A document describes. It states what an artifact holds, how a decision is made and what a
procedure produces, never what an agent should do. It does not name the tools that serve
it: a document reads the same whether or not a skill is installed, so a statement such as
"the planner establishes each unit's lifecycle role" belongs in a document, and the
wavefront command that records it belongs in wavefront's skill.

A prompt that needs a document includes it whole, with an `<!-- INCLUDE docs/<path> -->`
marker, introduced by one sentence saying what the document covers. An included document
rides in the system prompt, which a long run cannot compact away, and an agent cannot skip
reading it the way it can skip a file it is pointed at. Each document is included by every
role that follows it, and by no role that does not: the reviewer includes the binding and
porting how-tos it reviews against, the planner the conventions its homes follow.

The schemas under `docs/artifacts/` are documents too. They are included where a role
emits or reads the artifact, and are otherwise cited by path, as are their examples.

### Prompts

A prompt instructs. It holds what is specific to its role: the role's place among the
agents, its inputs, its workflow steps, and the guidelines that apply to one step or
stage. Where a step follows a document, the prompt names the document's section rather
than restating it ("as the planning instructions' Order section describes"); where a step
adds to it, the prompt states only the addition.

A prompt carries an `<!-- INSTRUCTIONS -->` marker in its `## Additional instructions`
section, which a task's instructions file fills, and which states that those instructions
take precedence where they conflict with the rest of the prompt. It carries a
`<!-- SKILLS -->` marker where the skill index belongs relative to its task.

### Skills

A skill is one tool an agent reaches for on demand. Its directory holds:

- `SKILL.md`, the generic header: the skill's name, description, binary and the document
  it points to, which the skill index lists for every role that carries the skill. The
  description is the routing signal; the agent reads the skill's document in full when
  the description matches its work; and
- one `<role>.md` per role that carries the skill, with a single `<!-- SKILL -->` anchor,
  holding that role's guidance for the tool. Each section augments one section of the
  role's documents or workflow, named as `<document> › <section>` or
  `For <step>`, and states only what the tool adds to it.

A skill is present in a role's prompt exactly when its files are on disk: deleting a
role's file removes the skill from that role, and deleting the directory removes it from
every role. The skill index rides in the system prompt; the tool's own documentation is
read on demand.

## Placement

| text | goes in |
|---|---|
| what an artifact's fields mean | its schema under `docs/artifacts/` |
| what an artifact looks like | its example under `templates/` |
| how a kind of work is done, independent of tools | the document for that work |
| a convention every role follows | `docs/conventions.md` |
| what one role does, in which steps | that role's prompt |
| how a tool serves a step or a section | the tool's skill, in the file of each role that uses it |
| what a tool is and when to reach for it | the tool's `SKILL.md` |
| what one run needs beyond its role | that task's `instructions.md` |

A rule that two roles share goes in a document both include, not in both prompts. A
rule that names a tool goes in the tool's skill, not in a document. A change to a rule is
made where the rule lives; text that restates it elsewhere is removed rather than kept in
step.
