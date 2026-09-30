# Mandatory questions

## Campaign

1. **Which repository and revision should this campaign use?** (`id: source`)
   - Answer: `https://gitlab.gnome.org/GNOME/libxml2.git`, `v2.15.3`
     (`c94eb0210183b9d7cb43f8e7fddc6be55843ef49`)

2. **Should this campaign port the C implementation to Rust, or create safe
   Rust wrappers?** (`id: objective`)
   - Answer: `wrap`

3. **What should this campaign target: a named subset of subsystems, or a named
   subset of functions and types, or the whole target repo? You can define them
   now or we can brainstorm them during the live session. You can also let the
   orchestrator decide.** (`id: scope`)
   - Answer: the whole target, as seven sub-campaigns run in this order. Unless noted,
     derive each one's implementation paths from the declaration inventory and cover
     the whole subsystem.
     - `public-api-types`: the whole published type and callback closure of
       `include/libxml/`, in dependency order;
     - `xml-writer`: `include/libxml/xmlwriter.h`;
     - `dtd-validation`: `include/libxml/valid.h`;
     - `xpath-internals`: `include/libxml/xpathInternals.h`;
     - `catalog-resolution`: `include/libxml/catalog.h`;
     - `sax2`: `include/libxml/SAX2.h`;
     - `public-api-remainder`: everything in `include/libxml/` not completed by the
       earlier sub-campaigns.

4. **Which model and billing should do the translation work?**
   (`id: translate-agent`)
   - Answer: ask me, showing the supported providers and models; `api` billing

5. **Do you want agentic review after translated work lands? If so, which
   model and billing should perform each review?** (`id: review-agent`)
   - Answer: `no`

6. **Should I run fully autonomously end to end?** (`id: autonomy`)
   - Answer: `no`

# Optional questions

Unanswered optional questions use their defaults.

## Campaign execution

7. **Should the campaign use the default batching and parallelism settings, or
   customize them?** (`id: workload`)
   - Answer: defaults except `max-types: 1`; parallelism is orchestrator's choice

8. **What batch caps should review agents use? We recommend the same caps as
   translation by default.** (`id: review-workload`)
   - Answer: not applicable

## Autonomy (if question 6 is answered `no`)

9. **Should I wait for your approval before starting the setup phase?** (`id: gates.setup`)
   - Answer: `no`; Phase 1 is pre-approved
10. **Should I wait for your approval before starting the translation phase?**
    (`id: gates.translation`)
    - Answer: `no`
11. **Should I wait for your approval between sub-campaigns?** (`id: gates.sub-campaign`)
    - Answer: `yes`; never promote a sub-campaign branch without approval
12. **Should I wait for your approval before starting review passes?** (`id: gates.review`)
    - Answer: `not applicable`

# Benchmark recording questions

13. **Where and in what format should results be recorded?** (`id: results`)
    - Answer: `/target/crustify/results.md`, standard template

# Additional instructions

## Why this target

The historical safe-FFI measurement found that `libxml` 0.3.21 safely covered
113 of 1,649 exported functions. The uncovered surface included the XML writer
(81 functions), DTD validation (71), XPath internals (117), catalog resolution
(37), and SAX2 (36). At v2.15.3, `xmlunicode.h` is fully deprecated and empty;
do not treat it as a sub-campaign. The current tag has 1,416 `XMLPUBFUN`
declarations after deprecation removal.

Libxml2's global memory management is documented as not thread-safe. Generated
wrappers inherit that C-library property; do not claim otherwise.

## Setup

Run Phase 1 end to end. Pre-authored `build.json` and `wavefront-config.json` sit beside
this task in `/opt/crustify/examples/crustify/libxml2/` and may be copied from there.
Emit `subsystems.json` after the campaign-wide oracle target is populated, mirroring
`include/libxml/` in its subsystems and verifying that grouping against the real
inventory. Record the test baseline and CodeQL provenance in the campaign record during
setup. The toolchain is already installed.

Before translation, report the API-only types, symbols and files and the
out-of-tree imported type floor. A large out-of-tree share indicates a scope
error because libxml2 vendors no dependencies.

## Selection and recording

The orchestrator owns internal wave construction and reports each dry-run plan before
spending.

Record coverage using safe functions in call position with documentation
comments stripped, so it remains comparable to the 113/1,649 baseline. After
each sub-campaign, record token-derived cost, the sub-campaign branch's diff, and the
deterministic `crustify scan-unsafe <workdir>` scan over the selected names.
