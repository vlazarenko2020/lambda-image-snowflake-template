# lambda-image-snowflake-connector-template

Template for an AWS Lambda **container image** (Python 3.14, built with uv) that connects to Snowflake with `snowflake-connector-python`. Copy it, change the query and settings, and deploy. See `__HOW_TO_RUN_LOCALLY.txt` to run it.

## uv setup

The project is managed with [uv](https://docs.astral.sh/uv/).

**Installed uv:** 0.11.23, standalone install at `~/.local/bin/uv`. To install it on another machine:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv self update          # later upgrades (standalone install only)
```

**Python:** uv-managed CPython 3.14 (`~/.local/share/uv/python/`), chosen by `.python-version` (`3.14`). uv downloads it automatically if missing; it can also be fetched with `uv python install 3.14`.

**Project files**

| File | Purpose |
|---|---|
| `pyproject.toml` | Name, `requires-python = ">=3.14,<3.15"`, and the one dependency `snowflake-connector-python` |
| `uv.lock` | Exact resolved versions of every package; commit it |
| `.python-version` | Python version uv uses for the project |
| `.venv/` | Virtual environment created by uv; not committed (in `.gitignore`) |

**How the project was set up**

```bash
uv init                                # pyproject.toml, .python-version, README.md (uv also created a main.py stub, since deleted)
uv add snowflake-connector-python      # adds the dependency, creates .venv and uv.lock
```

The Python requirement was later moved from 3.12 to 3.14 by editing `requires-python` and `.python-version` and running `uv lock && uv sync`.

**Everyday commands**

```bash
uv sync                    # create/update .venv from uv.lock
uv run main-1.py           # run inside the venv, no manual activation
uv add <package>           # add a dependency (updates pyproject.toml and uv.lock)
uv remove <package>
uv lock --upgrade          # refresh locked versions
```

**Docker:** the `Dockerfile` copies in the uv binary and installs the locked, non-dev dependencies from `uv.lock` into the Lambda image's own Python (`uv export --frozen --no-dev` then `uv pip install --system`). Keep the Python version in `pyproject.toml`, `.python-version` and the `FROM public.ecr.aws/lambda/python:<version>` tag identical.
