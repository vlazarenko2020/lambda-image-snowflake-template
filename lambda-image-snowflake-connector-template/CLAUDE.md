# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Template for an AWS Lambda (Python 3.14, container image) that connects to Snowflake and, as the example query, prints the first 10 rows of `<SNOW_DATABASE>.<SNOW_SCHEMA>.customers` (defaults `BR_DB.BR_ORDERS`). Managed with uv. There are no tests or linter configured.

`__HOW_TO_RUN_LOCALLY.txt` has the full local setup, env var table and troubleshooting.

## Commands

```bash
uv sync                       # install from uv.lock
./main-0.sh                   # local run: `uv run main-1.py`; needs SNOW_CONNECTION exported (e.g. in ~/.bashrc)
SNOW_CONNECTION=other SNOW_DATABASE=X SNOW_SCHEMA=Y ./main-0.sh
docker build -t lambda-image-snowflake-connector-template . # Lambda image
snow connection test -c <<your-snowflake-connection-name>>
```

`main-1.py` is the local entry point (calls `lambda_handler("", "")`).

## Architecture

Call flow: `main-1.py` → `lambda_function.lambda_handler` → `Modules.f_connect_to_snow()` / `Modules.f_run_snowflake_sql()`.

- `z_config.py` runs at import time and picks one of two auth modes from env vars:
  - **Local:** `SNOW_CONNECTION` names a profile in `~/.snowflake/connections.toml`.
  - **Lambda:** `SNOW_ACCOUNT` / `SNOW_USER` / `SNOW_PASS` (it calls `exit()` if they are missing and `SNOW_CONNECTION` is unset).
  - Optional overrides `SNOW_WAREHOUSE` and `SNOW_ROLE` (unset: the profile's values apply), and `SNOW_DATABASE` / `SNOW_SCHEMA` (default `BR_DB` / `BR_ORDERS`, which override the profile's).
- `Modules/__init__.py` re-exports `Modules/Layer_1.py` via `import *`.
- `Layer_1.f_connect_to_snow()` uses `connect(connection_name=...)` in profile mode. `f_key_pair_overrides()` is needed because the `snow` CLI profile uses `private_key_path` while the Python connector wants `private_key_file`, and the connector does not read the key passphrase from the environment (it takes `PRIVATE_KEY_PASSPHRASE` or `SNOWSQL_PRIVATE_KEY_PASSPHRASE`).
- `Layer_1.f_run_snowflake_sql()` prints all returned columns and returns a success bool; it only catches `ProgrammingError`.
- Table `BR_DB.BR_ORDERS.customers` (customer_id, first_name, last_name, email, address VARIANT, create_at, binary_score) holds 1000 synthetic rows created for testing.

## Docker

`Dockerfile` is based on `public.ecr.aws/lambda/python:3.14`. It copies in the `uv` binary, runs `uv export --frozen --no-dev` and `uv pip install --system` into `/var/lang`, then copies `lambda_function.py`, `z_config.py` and `Modules/`. Keep `requires-python` (`>=3.14,<3.15`), `.python-version` and the image tag on the same Python version. Lambda uses the env-var mode; profiles and the passphrase variable do not exist there.

## Conventions and gotchas

- Style: helper functions and their parameters are prefixed `f_`; files use `# ----` divider lines.
- Never put credentials in the repo or print them. Local secrets live in the `~/.snowflake` profile and the passphrase env var; `.gitignore` excludes `.env*` and `log/`.
- Prefer a least-privilege role (not `SYSADMIN`) in the connection profile and for the Lambda.
