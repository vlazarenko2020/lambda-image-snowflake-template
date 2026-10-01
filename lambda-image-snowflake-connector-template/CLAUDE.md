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

- `Modules/Layer_z_config.py` runs at import time (imported by `Layer_1.py` as `.Layer_z_config` and by `lambda_function.py` as `Modules.Layer_z_config`). `z_does_code_run_in_lambda` (true when `AWS_LAMBDA_FUNCTION_NAME` is set) tells Lambda from CLI. `f_process_error_and_exit()` reports config problems: it raises `RuntimeError` in Lambda (visible in CloudWatch) and prints + `exit()`s on the CLI. `SNOW_CONNECTION` set in Lambda is an error (no `~/.snowflake` there). It picks one of three auth modes from env vars (first match wins):
  - **Local (CLI only):** `SNOW_CONNECTION` names a profile in `~/.snowflake/connections.toml`.
  - **Parameter Store (preferred for Lambda):** `PARAMETER_STORE_ENTRIES_PREFIX_FOR_SNOWFLAKE_CONNECTION` (e.g. `/snowflake/TEST/`). `f_read_ssm_parameters()` reads every parameter directly under it with decryption: `snowflake_account`, `snowflake_user`, `snowflake_private_key` (SecureString, PEM text), `snowflake_private_key_passphrase` (SecureString, only if encrypted), optional `snowflake_warehouse` / `snowflake_role` / `snowflake_database` / `snowflake_schema`. Parameter Store wins over the plain env vars for the connection values; for the optional overrides the env var wins. Needs `ssm:GetParametersByPath` (+ `kms:Decrypt` for a customer managed key). `boto3` is a declared dependency; AWS errors print a how-to-fix message and `exit()`. Ignored in profile mode.
  - **Lambda env vars (key-pair, service user; no password mode):** `SNOW_ACCOUNT`, `SNOW_USER`, and one of `SNOW_PRIVATE_KEY_PATH` (file) / `SNOW_PRIVATE_KEY` (PEM text), plus `SNOW_PRIVATE_KEY_PASSPHRASE` if the key is encrypted (`PRIVATE_KEY_PASSPHRASE` / `SNOWSQL_PRIVATE_KEY_PASSPHRASE` also accepted). It lists every missing variable and calls `exit()` if the set is incomplete and `SNOW_CONNECTION` is unset.
  - Optional overrides `SNOW_WAREHOUSE` and `SNOW_ROLE` (unset: the profile's values apply), and `SNOW_DATABASE` / `SNOW_SCHEMA` (default `BR_DB` / `BR_ORDERS`, which override the profile's).
- `Modules/__init__.py` re-exports `Modules/Layer_1.py` via `import *`.
- `Layer_1.f_connect_to_snow()` uses `connect(connection_name=...)` in profile mode. `f_key_pair_overrides()` is needed because the `snow` CLI profile uses `private_key_path` while the Python connector wants `private_key_file`, and the connector does not read the key passphrase from the environment (it takes `PRIVATE_KEY_PASSPHRASE` or `SNOWSQL_PRIVATE_KEY_PASSPHRASE`). In env-var mode it passes `private_key_file` + `private_key_file_pwd` for a key path, or loads the PEM text with `cryptography` and passes DER bytes as `private_key` (literal `\n` in the PEM is converted to newlines).
- `Layer_1.f_run_snowflake_sql()` prints all returned columns and returns a success bool; it only catches `ProgrammingError`.
- Table `BR_DB.BR_ORDERS.customers` (customer_id, first_name, last_name, email, address VARIANT, create_at, binary_score) holds 1000 synthetic rows created for testing.

## Docker

`Dockerfile` is based on `public.ecr.aws/lambda/python:3.14`. It copies in the `uv` binary, runs `uv export --frozen --no-dev` and `uv pip install --system` into `/var/lang`, then copies `lambda_function.py` and `Modules/` (which includes `Layer_z_config.py`). Keep `requires-python` (`>=3.14,<3.15`), `.python-version` and the image tag on the same Python version. Lambda uses the env-var mode; profiles and the passphrase variable do not exist there.

## Conventions and gotchas

- Style: helper functions and their parameters are prefixed `f_`; files use `# ----` divider lines.
- Never put credentials in the repo or print them. Local secrets live in the `~/.snowflake` profile and the passphrase env var; `.gitignore` excludes `.env*` and `log/`.
- Prefer a least-privilege role (not `SYSADMIN`) in the connection profile and for the Lambda.
