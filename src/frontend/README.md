# ColdFront Frontend

ColdFront's frontend is built using [Tailwind](https://tailwindcss.com/),
[daisyUI](https://daisyui.com/), [Alpine.js](https://alpinejs.dev/), and [htmx](https://htmx.org/).

[Bun](https://bun.com/) is used to compile/bundle the static web assets. 

## Required software

1. Install bun. [Install docs here](https://bun.com/docs/installation):

```
$ curl -fsSL https://bun.com/install | bash
$ bun --version
```

2. Install packages

```
$ bun install
```

## Building assets

The bundled asses are stored in `../coldfront/static/bundles`. To re-compile them run:

```
$ bun run build
```

## Developing

By default ColdFront serves the pre-compiled bundled css/js assets from the
static directory `../coldfront/static/bundles`. When developing you want these
to be dynamically re-built anytime changes are made. This is done in two steps:

1. Start bun in dev mode:

```
$ bun run dev
```

2. Run the ColdFront dev server:

```
$ DEBUG=True uv run coldfront runserver
```

ColdFront uses typescript and the entrypoint is `src/coldfront.ts`. Tailwind CSS styles
are defined in `src/styles/coldfront.css`.
