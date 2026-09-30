# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Layout

This folder is a single git repo. Each project lives in its own sub-folder with its own `pyproject.toml`, `uv.lock` and `.venv` (and its own `.gitignore`). Work inside the relevant project folder and read its `CLAUDE.md`.

- `lambda-image-snowflake-connector-template/` – Template for an AWS Lambda container image that queries Snowflake with `snowflake-connector-python`.
