# ColdFront Frontend

ColdFront uses [vite](https://vite.dev/) to manage the web assets for the
frontend. vite compiles and bundles the css and javascript into optimized static
assets. vite also includes a dev server for hot reloading during development.

## Required software

1. Install nodejs and npm. Suggest using [volta](https://volta.sh/):

```
$ curl https://get.volta.sh | bash
$ volta install node
```

2. Install packages

```
$ npm install
```

## Building assets

The bundled asses are stored in `./assets`. To re-compile them run:

```
$ npm run build
```

## Developing

By default ColdFront serves the pre-compiled bundled css/js assets from the
static directory `./assets`. When developing you want to serve these assets
using vite dev server which supports [HMR](https://vite.dev/guide/features#hot-module-replacement). 
This is done in two steps:

1. Start the vite dev server:

```
$ npm run dev
```

2. Set the env varible `DJANGO_VITE_DEV_MODE=True` before running ColdFront,
   either via the command line or set it in your `.env` file. For example:

```
$ DEBUG=True DJANGO_VITE_DEV_MODE=True uv run coldfront runserver
```

ColdFront uses [django-vite](https://github.com/MrBin99/django-vite) for integrating vite with django.

ColdFront uses typescript and the entrypoint is `src/coldfront.ts`. All styles
are writting in Sass, see `src/scss/coldfront.scss`.
