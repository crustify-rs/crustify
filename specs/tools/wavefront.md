# wavefront

- binary: <!-- BIN wavefront -->
- documentation: <!-- DOC wavefront README.md -->, with its `--help` and the documents
  under its `docs/`

Wavefront answers deterministic queries about a C codebase: type and symbol records,
pointer analysis, lifecycle roles, dependency closures and the source inventory, and it
generates objective-neutral, dependency-ordered wave plans. Its own documentation is read
in full before its first command: `docs/scoping.md`, `docs/graph.md` and
`docs/batching.md` describe how it selects, orders and batches; `docs/artifacts/t3.md`
the T3 tables; and `docs/type-lifecycle.md` how a type's lifecycle primitives are
identified.

Wavefront's repo root is the C root, `c/`: it is passed `<workdir>/c` as its
`repo_root`, so that every path it reads and reports is below the C root, as the plan
records them.

A campaign keeps its wavefront state under `crustify/wavefront/`:

- the CodeQL database and its T1/T2 tables, under `codeql/`, and wavefront's `.cache`,
  both gitignored;
- the configurations, under `configs/`: the campaign-wide `wavefront-config.json`, whose
  `impl_files` and `api_headers` are the union of every module's, which every query of
  the bindings and reviews resolves through, which orders the link units and modules,
  and whose graph alone shows the relations between two modules; and one
  `<link-unit>/<module index>/wavefront-config.json` per module, which finds the
  module's dependency edges and its schedule. Every configuration shares
  `../crustify/wavefront`, relative to the C root, as its `state_dir`, and sets
  `"t3_dir": "t3"`;
- the T3 tables, under `t3/`, one campaign-wide pair serving every configuration:
  `chased_casts.csv`, whose `erased_arg` and `erased_field` rows name the type a
  type-erased parameter or field holds and whose `base_derived` rows the base a type is
  reached through, and `type_generators.csv`, the type-minting macros and the shapes they
  mint; and
- the ownership store, `ownership-store.json`, which holds the findings submitted with
  the CLI's `--update`: pointer ownership, access, nullability, cardinality and keepalive,
  and lifecycle roles. A finding submitted once is queried again rather than re-derived.
