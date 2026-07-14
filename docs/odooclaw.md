# OdooClaw integration

This template can optionally scaffold an
[OdooClaw](https://github.com/nicolasramos/odooclaw) deployment alongside the
standard Doodba stack. OdooClaw is an AI agent framework that connects to
Odoo via XML-RPC and exposes its capabilities through the Model Context
Protocol (MCP).

## What gets generated

When `use_odooclaw=true` is answered during `copier copy`, the template adds:

- An `odooclaw` service in `devel.yaml` and `prod.yaml`, using the pre-built
  image `docker.io/nicolasramos/odooclaw:latest`.
- A `redis:7-alpine` service for the OdooClaw job store.
- A named volume `odooclaw_data` for the OdooClaw workspace.
- A `odooclaw/config/config.json` file with sane defaults.
- Two helper scripts under `scripts/`:
  - `setup-odooclaw.sh` — validates the generated configuration.
  - `smoke-test-odooclaw.sh` — basic health check for the gateway.
- A `repos.yaml` entry for `nicolasramos/odoo-addons`, which fetches the
  `mail_bot_odooclaw` Odoo module from the matching `{{ odoo_version }}` branch.
- Extra environment variables under `.docker/odoo.env` (DB name, deterministic
  Odoo target DB/filter, admin password, webhook port, redis URL, job store backend).

## Requirements

- Odoo version between **16.0 and 18.0** inclusive. Older or newer versions
  are not wired up because the `mail_bot_odooclaw` module is only maintained
  for those releases at the moment.
- An API key for the LLM provider of your choice (OpenAI by default, but
  Anthropic and local Ollama are supported). Put it in `.docker/odoo.env`
  as `OPENAI_API_KEY` (or the equivalent for the provider you selected).
- Docker Compose v2 (preferred) or v1. v1 still works because the services
  are added inline; the template no longer relies on the `include:`
  directive that v1 does not understand.

## After generation

1. Review `.docker/odoo.env` and fill in your API keys. The template adds the
   OdooClaw env block at the bottom of the file; it is safe to leave the
   default production database name, DB filter, target DB and admin password
   that come from the `.copier-answers.yml` values. In development, the
   `devel.yaml` service overrides the target database to `devel` so OdooClaw
   talks to the same DB as the local Odoo service.
2. Run `invoke start` (or `docker compose up -d`) to bring the stack up.
3. Optionally run `scripts/smoke-test-odooclaw.sh` to confirm the gateway is
   reachable on port `18790`.

## Updating an existing project

If you enable OdooClaw in a project that was already generated with an older
version of this template, run `copier update`. The migration in
`migrations.py:add_odooclaw` will:

- Add the `odoo-addons` entry to `odoo/custom/src/repos.yaml`.
- Create `odooclaw/config/config.json` if it does not yet exist.
- Append the OdooClaw env block to `.docker/odoo.env`.

The inline service definitions in `devel.yaml` and `prod.yaml` are
re-rendered by Copier on update when those files can be updated cleanly. If
your project has heavily customized compose files and Copier reports a
conflict, keep your local changes and copy the generated `odooclaw`/`redis`
service blocks manually from a fresh render for the same Odoo version.

## Notes for production

- The default Docker image tag is `:latest`. Pin to a specific tag in your
  `.copier-answers.yml` (or override `ODOOCLAW_IMAGE` in `.docker/odoo.env`)
  before deploying to production.
- The webhook port `18790` is exposed on the host in both devel and prod.
  In a real production deployment, put OdooClaw behind a reverse proxy
  (Traefik is already configured by this template) and remove the
  `ports:` mapping from `prod.yaml`.
- OdooClaw stores job state in Redis (`ODOOCLAW_JOB_STORE=redis`) and in
  Odoo itself (`ODOOCLAW_JOB_STORE=odoo`); the default is `odoo` to keep
  the surface area minimal.
