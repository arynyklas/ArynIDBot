# syntax=docker/dockerfile:1

# debian:trixie-slim (multi-arch index digest). Same Debian release as the
# runtime image: uv picks wheels (cryptg, pymongo) for this glibc, and
# ldconfig is copied over.
FROM debian:trixie-slim@sha256:a29215f6a35e51e22adffa17f89e9d2ef06214e64a2bad10d765c46aea49f11f AS builder

COPY --from=ghcr.io/astral-sh/uv:0.13.1@sha256:4a1f3666816dafadd20ceb71eac9a7d56d7ef30279f7d64048519ab901ada336 /uv /bin/uv

# The interpreter is uv's standalone CPython for .python-version (uv fails on a
# mismatch), installed under /python, which the runtime stage copies as is.
# Byte-compile now: the bot cannot write `__pycache__` at run time.
ENV UV_PYTHON_INSTALL_DIR=/python \
    UV_PYTHON_PREFERENCE=only-managed \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=.python-version,target=.python-version \
    uv sync --locked --no-default-groups --no-install-project

COPY src src
RUN /app/.venv/bin/python -m compileall -q src && mkdir /state

# gcr.io/distroless/cc-debian13:latest (multi-arch index digest): glibc and
# libssl, no shell.
FROM gcr.io/distroless/cc-debian13:latest@sha256:159783207c2cd44c2aa5715961d13c8612368ac9bd450f887e3f08fc8ea461e3

# Telethon loads libssl through ctypes.util.find_library(), which parses
# `ldconfig -p`; this image has neither ldconfig nor its cache.
COPY --from=builder /usr/sbin/ldconfig /sbin/ldconfig
RUN ["/sbin/ldconfig"]

COPY --from=builder /python /python
COPY --from=builder /app /app

WORKDIR /app

# The session and the log are all the bot writes; volumes go over these two
# directories and a fresh named volume inherits this owner and mode. Code and
# dependencies stay root's, read-only to the bot.
COPY --from=builder --chown=10001:10001 --chmod=0700 /state /app/sessions
COPY --from=builder --chown=10001:10001 --chmod=0700 /state /app/logs

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1

USER 10001:10001

# Python turns SIGINT into a clean stop at any point, also while the bot is
# still connecting; PID 1 ignores SIGTERM until the bot installs its handler.
STOPSIGNAL SIGINT

ENTRYPOINT ["python", "-m", "src.main"]
