<!-- SKILL -->

Translators build the safe crates on ffibox; read its documentation so you can judge
their landings.

---

### For Phase 2: Translation

#### 5. Accounting

##### Static safety scan

ffibox ships its seam names in `seams.txt`, at the root of its checkout next to the
README this skill points at. Add it to every `crustify scan-unsafe --seams` list, beside
crustify's own `docs/translate/seams.txt`, so ffibox's conversions (`as_ptr`,
`from_raw`, `into_raw`, ...) and lifecycle hooks (`c_drop`, `c_dup`, ...) count as seam
rather than smell.
