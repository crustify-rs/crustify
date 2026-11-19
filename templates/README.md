# Templates

- [`STATUS.md`](STATUS.md) and [`DEPS.md`](DEPS.md): the formats of a port's
  `crustify/STATUS.md` and `crustify/DEPS.md`, which Crustify's system prompt describes.
- [`docker/`](docker): the environment a port runs in, [`Dockerfile`](docker/Dockerfile),
  with the mounts, build arguments and environment variables that go with it in
  [`docker/README.md`](docker/README.md). It starts nothing: the container idles, and
  Crustify is opened inside it.
