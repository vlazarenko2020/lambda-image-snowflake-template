#!/bin/bash
#
# Local run using a named profile from ~/.snowflake/connections.toml.
# SNOW_CONNECTION must already be exported (e.g. in ~/.bashrc).
# No credentials here. Optionally set SNOW_DATABASE / SNOW_SCHEMA.

PY_PROG='main-1.py'
cd "$(dirname "$0")" || exit 1

uv run ${PY_PROG}
