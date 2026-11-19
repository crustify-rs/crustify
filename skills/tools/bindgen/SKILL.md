---
name: bindgen
description: "bindgen, which generates Rust declarations of C functions, types and constants from the C's headers. Read before the Rust first calls C or reads one of its types."
---

# bindgen

bindgen generates the raw Rust declarations of C functions, struct layouts and constants
from the C's headers, so that they follow the headers as they change instead of being
written by hand. Where the generated bindings live and how they are built is the agent's
choice. Read its user guide, at https://rust-lang.github.io/rust-bindgen/, and its
`--help` wherever you need them.
