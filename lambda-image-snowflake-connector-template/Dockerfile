FROM public.ecr.aws/lambda/python:3.14

# uv binary from the official image (only used at build time)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install into the Lambda image's own Python (/var/lang), not a venv
ENV UV_PYTHON=/var/lang/bin/python \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1

# Install locked, non-dev dependencies. Copying only the manifests first
# keeps this layer cached until pyproject.toml / uv.lock change.
COPY pyproject.toml uv.lock ${LAMBDA_TASK_ROOT}/
RUN cd ${LAMBDA_TASK_ROOT} \
    && uv export --frozen --no-dev --no-hashes --no-emit-project -o /tmp/requirements.txt \
    && uv pip install --system -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

# Copy function code
COPY lambda_function.py z_config.py ${LAMBDA_TASK_ROOT}/
COPY Modules/*.py ${LAMBDA_TASK_ROOT}/Modules/

# Handler: <module>.<function>
CMD [ "lambda_function.lambda_handler" ]
