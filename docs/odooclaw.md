<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
<summary>Table of contents</summary>

- [OdooClaw AI agent](#odooclaw-ai-agent)
  - [What was generated](#what-was-generated)
  - [First-time setup](#first-time-setup)
  - [How it works](#how-it-works)
  - [Changing the provider or model](#changing-the-provider-or-model)
  - [Disabling](#disabling)
  - [Docs](#docs)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# OdooClaw AI agent

This project was generated with `use_odooclaw: true`, which wires
[OdooClaw](https://github.com/nicolasramos/odooclaw) — a fully local AI agent that
answers `@OdooClaw` mentions in Odoo Discuss — into your Doodba stack.

## What was generated

| Piece                                  | Where                                                                                 |
| -------------------------------------- | ------------------------------------------------------------------------------------- |
| Gateway source (compose build context) | `odooclaw/` (populated by `scripts/setup-odooclaw.sh`)                                |
| Gateway config                         | `odooclaw/config/config.json`                                                         |
| Secrets/env                            | `.docker/odooclaw.env`                                                                |
| Compose services (`odooclaw`, `redis`) | inline in `devel.yaml` / `prod.yaml`                                                  |
| Odoo module repo                       | `odoo/custom/src/repos.yaml` (`nicolasramos/odoo-addons`, branch = your Odoo version) |
| Bootstrap / smoke test                 | `scripts/setup-odooclaw.sh`, `scripts/smoke-test-odooclaw.sh`                         |

## First-time setup

1. **Fetch the gateway source** (the compose file builds the `odooclaw` image from
   `./odooclaw`, it is not published as a Docker image):

   ```bash
   scripts/setup-odooclaw.sh
   ```

2. **Set secrets** in `.docker/odooclaw.env` (never commit this file):

   - `ODOOCLAW_LLM_API_KEY` — your provider API key (not needed for a keyless local
     Ollama).
   - `ODOOCLAW_ODOO_USERNAME` / `ODOOCLAW_ODOO_PASSWORD` — an Odoo user the `odoo-mcp`
     tools can use. A dedicated technical user is recommended.

3. **Start the stack**:

   ```bash
   docker compose -f devel.yaml build odooclaw
   docker compose -f devel.yaml up -d
   ```

4. **Install the Odoo module**: in Odoo, Apps → search "OdooClaw" → install
   `mail_bot_odooclaw` (plus the area modules you want: `_account`, `_crm`, `_expense`,
   `_fleet` — available on the 18.0 branch).

5. **Smoke test**:

   ```bash
   scripts/smoke-test-odooclaw.sh devel.yaml
   ```

6. **Chat**: open a DM in Discuss and type `@OdooClaw hello`.

## How it works

```
DM in Odoo → mail_bot_odooclaw (overrides message_post)
           → POST http://odooclaw:18790/webhook/odoo (async)
           → OdooClaw agent + odoo-mcp tools (respect the user's permissions)
           → reply posted back to the same Discuss conversation
```

The database the agent talks to is pinned per environment by
`ODOOCLAW_CHANNELS_ODOO_TARGET_DB` (`devel` in `devel.yaml`, `{{ postgres_dbname }}` in
`prod.yaml`), so the agent never resolves the wrong DB.

## Changing the provider or model

`odooclaw_provider` / `odooclaw_model` are copier answers. Change them with:

```bash
copier copy --defaults -d odooclaw_provider=ollama -d odooclaw_model=llama3 . <new-dir>
# or edit .copier-answers.yml and run: copier copy --defaults ...
```

## Disabling

Set `use_odooclaw: false` in `.copier-answers.yml` and run `copier update`. The
migration removes the generated OdooClaw files and services. Your `odooclaw/` gateway
clone and local secrets in `.docker/odooclaw.env` are left untouched for you to review
and delete.

## Docs

Upstream documentation lives in
<https://github.com/nicolasramos/odooclaw/tree/main/odooclaw/docs>, including
`GUIDE_DOODBA_SETUP_EN.md` and `GUIA_DOODBA_PUESTA_EN_MARCHA_ES.md`.
