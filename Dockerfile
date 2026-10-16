# Must match .python-version, which uv reads below: it fails on a mismatch.
ARG PYTHON_VERSION=3.13

FROM python:${PYTHON_VERSION}-slim-trixie AS builder

COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /bin/uv

# Byte-compile now: the bot cannot write `__pycache__` at run time. Build with
# the image's own Python, the one the final stage runs.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=.python-version,target=.python-version \
    uv sync --locked --no-default-groups --no-install-project

FROM python:${PYTHON_VERSION}-slim-trixie

WORKDIR /app

# The session and the log are all the bot writes; volumes go over these two
# directories. Code and dependencies stay root's, read-only to the bot.
RUN groupadd --gid 10001 bot \
    && useradd --uid 10001 --gid bot --no-create-home --no-log-init bot \
    && install -d -o bot -g bot -m 700 sessions logs

COPY --from=builder /app/.venv .venv
COPY src src

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1

USER 10001:10001

# Python turns SIGINT into a clean stop at any point, also while the bot is
# still connecting; PID 1 ignores SIGTERM until the bot installs its handler.
STOPSIGNAL SIGINT

ENTRYPOINT ["python", "-m", "src.main"]
