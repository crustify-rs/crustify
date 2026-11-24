# Templates

- [`STATUS.md`](STATUS.md): the format of a port's `.crustify/STATUS.md`, which Crustify's
  system prompt describes.
- [`disclosure.md`](disclosure.md): the format of an audit's disclosure draft, which sits
  beside its finding as `disclosure.md`.
- [`docker/`](docker): the environment a port runs in, [`Dockerfile`](docker/Dockerfile),
  with the mounts, build arguments and environment variables that go with it in
  [`docker/README.md`](docker/README.md). It starts nothing: the container idles, and
  Crustify is opened inside it.
