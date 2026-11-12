---
name: authoring
description: "How Crustify itself is organized: skills, roles, tool skills and the plugin, and where each kind of text goes. Read before changing Crustify or writing a task message for an agent."
---

# Authoring

How Crustify is organized: its skills, its agents and the providers that serve them to an
agent host, and where each kind of text lives. The aim is that every rule is written once,
in the one place its kind belongs, so that changing it changes every agent that follows it,
and no two copies drift apart.

## 1. Layers

Crustify is text in three layers, with one more per run:

| layer | where | voice | holds |
|---|---|---|---|
| skills | `skills/<group>/<name>/SKILL.md` | descriptive, third person | what Crustify's artifacts are and how its work is done: workflows, how-tos, conventions, schemas |
| tool skills | `skills/tools/<tool>/SKILL.md` | descriptive, third person | what each tool is, and how it serves each stage |
| agents | `agents/<agent>.md`, with `agents/common.md`, and the assistant's under `agents/assistant/` | instructive, second person | an agent's identity, inputs, what it owns, its steps and what its role changes in the skill index |
| task messages | `task.md` beside a run's `task.json` | instructive | what one run is given: its inputs, and what it needs beyond its role |

Each artifact's schema, the meaning of its fields, is a skill under `skills/artifacts/`,
and an example of each is given under `templates/`, which the schema cites. The settings,
dashboard and `.gitignore` templates there are what a campaign copies to start. Examples
hold illustrations, not rules.

The layers are plain Markdown, so that any agent reads them as files. A provider, under
`providers/<host>/`, serves them to one agent host in its own format, as
[Providers](#4-providers) describes; the layers name no host.

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
The parts sit in sub-directories of the skill's own, `skills/<group>/<skill>/<part>/SKILL.md`,
each named `<skill>-<part>`, and the skill's own `SKILL.md` keeps what they share: `binding`
and `porting` keep their boundaries, and their `-types` and `-symbols` parts their routes.

A skill's directory may also hold a script the skill describes, with its tests beside it,
standard library only, so that it runs wherever the skill is read: `usage` holds
`crustify-usage`.

A skill or an agent says what a step does and which program does it, never the program's
command lines, flags or options, which change with the program: the program's own `--help`
and documentation give them, and the text sends its reader there. A command appears only
where its exact form is what must hold, and a procedure of several commands that must run
exactly so is a script beside its skill, documented by its own `--help`.

Every skill's sections are numbered. A reference to a section names it, with or without its
number ("testing-builds' Coverage section", "layout § Lifecycle › Waves"), so that a renumbering
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

Every agent's prompt opens with `agents/common.md`: that every commit takes the identity
[`versioning`](../../operations/versioning/SKILL.md)'s Identity section gives, that a task
message's instructions take precedence over the rest of the prompt, but where a skill or a
role says a task message adds to a check and never relaxes it, and how skills and
tool skills are read. Every agent sees every skill, with its description:
its host lists them, or, for a host that does not, the provider fills the index of every
skill at common's `<!-- SKILL INDEX -->` marker from the skills' names and descriptions, so
that each description is written once.

The agent's own file follows, in three sections, every agent alike:

- `## Role`: who the agent is, its place among the agents, what it owns and what it leaves
  to others;
- `## Workflow`: its steps, each naming the skills it follows. A skill the description
  already sends the agent to before a step needs no mention; a step names a skill where
  only part of it applies to the agent, or where the agent follows it only in some runs;
  and
- `## Inputs`: what its task message names.

An agent's file names no value of one run: an integration branch or a batch id is "the one
your task message names". `{crustify_root}` stands for the path of Crustify's checkout,
which a provider fills.

The assistant has one file for every kind of campaign, `agents/assistant/assistant.md`, with a
`<!-- CAMPAIGN ROLE -->` marker at the end of its Role and a `<!-- CAMPAIGN WORKFLOW -->`
marker as its Workflow, which take the campaign kind's file,
`agents/assistant/translate.md` for a port or wrap campaign or `agents/assistant/audit.md`
for an audit: its `### Campaign` section, what the assistant owns in that kind of campaign,
and, after its `<!-- WORKFLOW -->` marker, its steps.

### 1.3 Tool skills

A tool is one program an agent reaches for: wavefront, ffimap, ffibox. Each has one skill,
`skills/tools/<tool>/SKILL.md`, written as every skill is, descriptively and without naming
agents. It states what a campaign uses the tool for, where the tool's state sits in a
campaign, and how the tool's output becomes Crustify's artifacts and decisions. How the
tool works, its configuration, tables, commands and what they mean, is its own
documentation's, which the skill cites by document rather than restating, so that the two
never drift; a fact that documentation lacks is added to it, on a branch of the tool's
repository, not to the skill.

A tool skill opens with what the tool is, which documentation of its own is read in full
before its first use, and what holds in every use of it; one section per stage follows,
each subsection named after the skill section it adds to ("Scheduling › Order"), stating
only what the tool adds there and naming the documents of the tool that stage reads. Its
description names the stages and steps it serves.

An agent reads a tool's skill before the first step of its work that the skill's
description names, as `agents/common.md` says, and no other skill names a tool: the
description alone brings an agent to the tool, so it names every stage and step the tool
serves. A tool is removed by deleting its skill.

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
| what the assistant does in one kind of campaign | `agents/assistant/<kind>.md` |
| what a tool is, and how it serves each stage | its tool skill |
| how one host is served the layers | its provider under `providers/<host>/` |
| what one run needs beyond its role | its task message, `task.md` |
| what Crustify is for, which every change is judged against | `GOALS.md`, at Crustify's root |
| how Crustify repairs and improves itself | [`evolution`](../evolution/SKILL.md) |
| which changes landed, and whether each held | `EVOLUTION.md`, at Crustify's root |
| a rule that holds for one target alone | that campaign's `crustify/LESSONS.md` |

A rule that two agents share goes in a skill both read, not in both agents. A rule that
names a tool goes in the tool's skill. A change to a rule is made where the rule lives;
text that restates it elsewhere is removed rather than kept in step.

## 3. Runs

A stage's agent runs with its file as its system prompt and its task as its first message:
the task message names what its `## Inputs` section lists and the instructions its run
needs beyond its role, if any. Its file is the same for every run of the stage, so that runs at once share their
whole system prompt in the provider's cache. The assistant runs the same way, as the main
agent of a session in a campaign's repository, with its file and its campaign kind's as
its system prompt.

## 4. Providers

A provider serves the layers to one agent host, in that host's format, and holds nothing
the layers do not: every file it carries is generated from them, wires them in, or carries
what its host needs of its own.

The generic provider, `providers/generic/`, composes each agent's prompt for any host:
`compose.py <agent> [<kind>]` prints `agents/common.md`, with the skill index filled, and
the agent's file, the assistant's with its campaign kind's. A host without a provider of
its own takes that prompt as its agent's instructions, and reads each skill's `SKILL.md`
by its path. The other providers compose through it.

The Claude Code provider, `providers/claude/`, makes Crustify's checkout a plugin, whose
manifest is `.claude-plugin/plugin.json`:

- the skills, by their group directories and the directory of each part of a split skill,
  which the manifest lists on its own since Claude Code scans a listed directory one level
  deep, invoked as `crustify:<name>`;
- `agents/`, one plugin agent per stage, `crustify:<stage>`, and one assistant per campaign
  kind, `crustify:assistant-translate` and `crustify:assistant-audit`. A plugin agent's
  body replaces Claude Code's own system prompt, so each body opens with that prompt,
  `system-prompt.md`, followed by the generic provider's prompt without the skill index,
  since Claude Code lists the plugin's skills to every agent. Each agent's
  frontmatter gives the description the assistant routes a run by;
- `system-prompt.md`, Claude Code's own system prompt, captured from a real request by
  `dump-system-prompt.py`, less its one project's `# Memory` section, and dumped again
  when Claude Code is upgraded;
- `spawn.py`, which launches a stage run as a Claude Code process of its own, since Claude
  Code refuses a subagent's writes of report files, and copies its transcript into
  Crustify's home; the assistants' prompts end with how they launch through it;
- `hooks.json`: a `SubagentStop` hook, `transcripts.py`, which copies each stage agent's
  transcript into Crustify's home, for a stage run a host launches as a subagent; and
- `compose.py`, which generates the agents (`compose.py build`).

The generated files are committed, and regenerated whenever `agents/` or
`system-prompt.md` changes.
