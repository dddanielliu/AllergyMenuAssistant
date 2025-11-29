FROM python:3.14-slim AS base
ARG DEBIAN_FRONTEND=noninteractive

ENV PROJECT_PATH=/menu-analysis

FROM base AS python-base
ARG DEBIAN_FRONTEND=noninteractive


WORKDIR ${PROJECT_PATH}

RUN --mount=from=ghcr.io/astral-sh/uv:latest,source=/uv,target=/bin/uv \
    --mount=type=bind,source=pyproject.toml,target=${PROJECT_PATH}/pyproject.toml,ro \
    --mount=type=bind,source=uv.lock,target=${PROJECT_PATH}/uv.lock,ro \
    --mount=type=bind,source=.python-version,target=${PROJECT_PATH}/.python-version,ro \
    uv sync --frozen --no-install-project --no-install-workspace --no-dev

COPY --exclude=*.py --exclude=*.md src/ ${PROJECT_PATH}/src

RUN --mount=from=ghcr.io/astral-sh/uv:latest,source=/uv,target=/bin/uv \
    --mount=type=bind,source=pyproject.toml,target=${PROJECT_PATH}/pyproject.toml,ro \
    --mount=type=bind,source=uv.lock,target=${PROJECT_PATH}/uv.lock,ro \
    --mount=type=bind,source=.python-version,target=${PROJECT_PATH}/.python-version,ro \
    uv sync --locked --no-dev

FROM base AS dev
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        vim tmux git

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY --from=python-base /root/.cache/uv/ /root/.cache/uv/
COPY --from=python-base ${PROJECT_PATH} ${PROJECT_PATH}

WORKDIR ${PROJECT_PATH}

CMD ["/bin/bash"]

FROM base AS prod

COPY . .

CMD ["/bin/bash"]