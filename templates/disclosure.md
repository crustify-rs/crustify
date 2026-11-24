<!--
The draft of a disclosure, saved as `disclosure.md` beside its finding. The header is
for the user and stays with the audit. The user sends only the body, below the `---`
line. Remove these comments from the draft.
-->

status: <to file | do not file: <reason> | reported: <url of the upstream issue> | fixed: <url of the change that fixed it>>
severity: <high | medium | low>: <what goes wrong, and what use of the API reaches it>
channel: <where the project asks for reports of this kind>
upstream: <latest release>: <shows the defect or not>; <tip of the default branch>: <shows the defect or not>

<!--
status    The only record of what happened to the disclosure. Update it when the user
          says what they sent.
severity  high: memory corruption, a data race, or an out-of-bounds access, reached by
          ordinary use of the safe API or by input from outside the program.
          medium: undefined behavior that only unusual use reaches, or that goes through
          an unsafe API whose documented obligations the caller met.
          low: undefined behavior that only an aliasing model reports, with no effect
          observed on current compilers; and every finding that is not undefined behavior.
          The audit's report lists the same severity.
channel   Take it from the project's SECURITY.md, its issue templates, and its
          contributing guide.
upstream  The revisions on which the evidence was run again.

If the defect is already reported or fixed upstream, write the header only.
Write the body for the project's maintainers, in the format that the project asks for.
Keep it under 300 words, unless a longer body is justified.
-->

---

# <the defect, in one line>

<What goes wrong, where, and why. Cite the source lines.>

## Reproduce

<The revision and the configuration. The command. The output to expect.>

## Fix

<The one change that removes the defect.>

Found by [Crustify](https://github.com/crustify-rs/crustify), an experimental UB/soundness
auditing agent developed at UC Berkeley and running on `<llm>`, then manually reviewed and
independently reproduced.
