<!-- SKILL -->

Invoke only `crustify <workdir> audit unsafe`; never invoke
`crustify <workdir> audit ub`. That one is a campaign phase the orchestrator
gates, not a translator's to start.

## Completion

The following step augments your completion sequence.

### 1. Static safety scan

Seed the scan with the exact scheduled C type and symbol names and request
JSON:

```bash
crustify <workdir> audit unsafe --name <batch names...> --json
```

Type entries expose raw-pointer and raw-deref sites plus manual
`Deref`/`DerefMut` and materialized shared/mutable slice sites; symbol entries
expose declaration/body raw-pointer sites and body dereferences.

Treat every site as an investigation lead, not a verdict. Fix unsafe wrapper
bypasses and unsound references; retain a required FFI seam with a safety
comment rather than removing it.
