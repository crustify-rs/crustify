---
name: authoring
description: "How Crustify itself is organized: skills, roles, tool skills and the plugin, and where each kind of text goes. Read before changing Crustify or writing additional instructions for an agent."
---

# Authoring

How Crustify is organized: its skills, its agents and the adapters that serve them to an
agent host, and where each kind of text lives. The aim is that every rule is written once,
in the one place its kind belongs, so that changing it changes every agent that follows it,
and no two copies drift apart.

## 1. Layers

Crustify is text in three layers, with one more per run:

| layer | where | voice | holds |
|---|---|---|---|
| skills | `skills/<group>/<name>/SKILL.md` | descriptive, third person | what Crustify's artifacts are and how its work is done: workflows, how-tos, conventions, schemas |
| tool skills | `skills/tools/<tool>/SKILL.md` | descriptive, third person | what each tool is, and how it serves each stage |
| agents | `agents/<agent>.md`, with `agents/common.md` and the assistant's `agents/assistant-<kind>.md` | instructive, second person | an agent's identity, inputs, what it owns, its steps and its skill index |
| additional instructions | `instructions.md` beside a task's `task.json` | instructive | what one run needs beyond its role |

Each artifact's schema, the meaning of its fields, is a skill under `skills/artifacts/`,
and an example of each is given under `templates/`, which the schema cites. The settings,
dashboard and `.gitignore` templates there are what a campaign copies to start. Examples
hold illustrations, not rules.

The layers are plain Markdown, so that any agent reads them as files. An adapter, under
`adapters/<host>/`, serves them to one agent host in its own format, as
[Adapters](#4-adapters) describes; the layers name no host.

### 1.1 Skills

A skill describes. It states what an artifact holds, how a decision is made, what a
procedure produces and when each of its steps happens, never what an agent should do, and
never who does a step: which agent owns which step is the agents'. It does not name the
tools that serve it either: a skill reads the same whether or not a tool is installed, so
a statement such as "each unit's lifecycle role is established while planning" belongs in
a skill, and the wavefront command that records it belongs in wavefront's tool skill.

Skills are grouped by the part of the work they describe: `workflows/`, `planning/`,
`rust/`, `verification/`, `operations/`, `artifacts/`, `tools/` and `crustify/`. A skill's
name is unique across the groups, since agents invoke it by name. Two kinds of skill
describe how work is done. A how-to, such as `binding` or `porting`, describes how one item
is handled. A workflow, under `workflows/`, describes how one kind of campaign proceeds
from its settings to its results: `setup`, which every campaign shares, and one per kind of
campaign (`binding-workflow`, `porting-workflow`, `audit-workflow`). A workflow names the
how-tos and the layout rather than restating them.

A skill opens with frontmatter that gives its `name` and its `description`. The
description is all an agent sees of the skill before it reads it, so it says what the skill
covers and before which step it is read. A skill stays under about 4,500 tokens, so that a
host that brings an invoked skill back after compacting an agent's context brings it back
whole; one that outgrows that is split at a section that another step needs on its own.

Every skill's sections are numbered. A reference to a section names it, with or without its
number ("testing's Coverage section", "layout § Lifecycle › Waves"), so that a renumbering
never silently points a reference at another section. A skill links another by its
relative path, with the other's name as the link's text.

### 1.2 Agents

An agent instructs. Its file holds what is specific to it: its place among the agents, its
inputs, its workflow steps, and the guidelines that apply to one step or stage. Where a step
follows a skill, the agent names the skill's section rather than restating it ("as the
`scheduling` skill's Order section describes"); where a step adds to it, the agent states
only the addition.

An agent states what it owns by naming the skill sections it carries out ("you create and
purge every level of the `layout` skill's Lifecycle section"), and adds only what the
skills leave to it: the commands it runs, the judgements it makes, the cases it must not
handle itself.

Every agent's prompt opens with `agents/common.md`: the identity every commit takes, and
how skills and tool skills are read. Its own text follows, and closes with three sections:
`## Skills`, its skill index, which names each skill it follows with the step it is read
before; `## Inputs`, what its task message names; and `## Additional instructions`, which
says that a run's instructions file takes precedence where it conflicts with the rest. An
agent's file names no value of one run: an integration branch or a batch id is "the one
your task message names". `{crustify_root}` stands for the path of Crustify's checkout,
which an adapter fills.

The assistant has one file for every kind of campaign, `agents/assistant.md`, with a
`<!-- CAMPAIGN -->` marker and a `<!-- CAMPAIGN SKILLS -->` marker, which take the campaign
kind's file, `agents/assistant-translate.md` for a port or wrap campaign or
`agents/assistant-audit.md` for an audit: what the assistant owns in that kind of campaign
and its steps, and, after its `<!-- SKILLS -->` marker, the skills only that kind follows.

### 1.3 Tool skills

A tool is one program an agent reaches for: wavefront, ffimap, ffibox. Each has one skill,
`skills/tools/<tool>/SKILL.md`, written as every skill is, descriptively and without naming
agents. It opens with what the tool is, which documentation of its own is read in full
before its first use, and what holds in every use of it; one section per stage follows,
each subsection named after the skill section it adds to ("Scheduling › Order") and
stating only what the tool adds there. Its description names the stages and steps it
serves.

Every agent reads every tool skill its host offers before its first step, as
`agents/common.md` says, so that no other skill names a tool. A tool is removed by deleting
its skill.

## 2. Placement

| text | goes in |
|---|---|
| what an artifact's fields mean | its schema skill under `skills/artifacts/` |
| what an artifact looks like | its example under `templates/` |
| how a kind of work is done, independent of tools | the skill for that work |
| how a kind of campaign proceeds, step by step | its workflow skill under `skills/workflows/`, with the steps every campaign shares in `setup` |
| a convention every agent follows | `conventions` |
| what one agent does, in which steps, and which steps it owns | that agent's file under `agents/` |
| what every agent holds | `agents/common.md` |
| what the assistant does in one kind of campaign | `agents/assistant-<kind>.md` |
| what a tool is, and how it serves each stage | its tool skill |
| how one host is served the layers | its adapter under `adapters/<host>/` |
| what one run needs beyond its role | that task's `instructions.md` |

A rule that two agents share goes in a skill both read, not in both agents. A rule that
names a tool goes in the tool's skill. A change to a rule is made where the rule lives;
text that restates it elsewhere is removed rather than kept in step.

## 3. Runs

A stage's agent runs with its file as its system prompt and its task as its first message:
the task message names what its `## Inputs` section lists and its instructions file, if
any. Its file is the same for every run of the stage, so that runs at once share their
whole system prompt in the provider's cache.

The assistant is served its file as an agent host allows: as a skill it reads at the start
of every session in a campaign's repository, and again after every compaction.

## 4. Adapters

An adapter serves the layers to one agent host, in that host's format, and holds nothing
the layers do not: every file it carries is generated from them or wires them in.

The Claude Code adapter, `adapters/claude/`, makes Crustify's checkout a plugin, whose
manifest is `.claude-plugin/plugin.json`:

- the skills, by their group directories, invoked as `crustify:<name>`;
- `agents/<stage>.md`, one plugin agent per stage, `crustify:<stage>`: its frontmatter
  names it and gives the description the assistant routes a run by, and its body is
  `agents/common.md` and the stage's file;
- `skills/assistant-<kind>/`, the assistant's file composed for each campaign kind, as a
  skill;
- `hooks.json`: a `SessionStart` hook which, in a campaign's repository, tells the session
  to read the assistant's skill for the campaign's kind, at startup and after every
  compaction, and a `SubagentStop` hook which copies each stage agent's transcript into
  Crustify's home; and
- `compose.py`, which generates the agents and the assistant's skills from `agents/`
  (`compose.py build`), and runs the hooks.

The generated files are committed, and regenerated whenever `agents/` changes.
