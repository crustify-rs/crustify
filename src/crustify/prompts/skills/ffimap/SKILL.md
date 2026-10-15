# ffimap

- Skill name: ffimap
- Bin path: crustify ffimap
- Description: Deterministic map of a Rust crate's FFI and unsafe surface: a rustc
  driver over HIR and typeck counts unsafe blocks and fns, raw and void pointers by
  position and visibility, FFI calls and wrapper use, and lists where each counter's
  increments are with `--sites`. No model is involved, so two runs over one tree agree
  exactly. Run it with `--help` for its flags and counters.
