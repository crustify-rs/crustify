# Templates

Two kinds of campaign, one image, one directory of templates each.

| directory | campaign | settings template | dashboard template |
|---|---|---|---|
| [`translate/`](translate) | translate C to Rust, or wrap it | [`CRUSTIFY.template.md`](translate/CRUSTIFY.template.md) | [`dashboard.template.md`](translate/dashboard.template.md) |
| [`audit/`](audit) | hunt UB in an existing Rust crate with reviewers | [`CRUSTIFY.template.md`](audit/CRUSTIFY.template.md) | [`dashboard.template.md`](audit/dashboard.template.md) |

Copy a settings template to answer the assistant's questions up front.

[`gitignore`](gitignore) seeds a campaign's `crustify/.gitignore`. The files beside it
are examples of the campaign's artifacts, whose fields are described under
[`skills/artifacts/`](../skills/artifacts): [`build.json`](build.json),
[`modules.json`](modules.json), [`dependencies.json`](dependencies.json), the out-of-tree
libraries the target uses, and [`schedule.json`](schedule.json), the campaign's waves and
batches.

[`docker/`](docker) holds the environment either campaign runs in:
[`Dockerfile`](docker/Dockerfile) and the mounts, build arguments and environment
variables that go with it, in [`docker/README.md`](docker/README.md). It starts nothing:
the container idles, and Crustify's assistant is opened inside it.
