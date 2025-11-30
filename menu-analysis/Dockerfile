FROM python:3.13-slim AS base
ARG DEBIAN_FRONTEND=noninteractive

ENV PROJECT_PATH=/menu-analysis

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        tesseract-ocr \
        tesseract-ocr-chi-tra \
        libtesseract-dev

FROM base AS python-base
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        wget

WORKDIR /usr/share/tessdata_full

# 3. Download the "Full" English and Traditional Chinese data
#    (These contain the Legacy components required for OEM 2)
RUN wget -O /usr/share/tessdata_full/eng.traineddata \
    https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata

RUN wget -O /usr/share/tessdata_full/chi_tra.traineddata \
    https://github.com/tesseract-ocr/tessdata/raw/main/chi_tra.traineddata

ENV TESSDATA_PREFIX=/usr/share/tessdata_full

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

ENV TESSDATA_PREFIX=/usr/share/tessdata_full

COPY --from=python-base /usr/share/tessdata_full /usr/share/tessdata_full
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY --from=python-base /root/.cache/uv/ /root/.cache/uv/
COPY --from=python-base ${PROJECT_PATH} ${PROJECT_PATH}


WORKDIR ${PROJECT_PATH}

CMD ["/bin/bash"]

FROM base AS prod

WORKDIR ${PROJECT_PATH}

ENV TESSDATA_PREFIX=/usr/share/tessdata_full

COPY --from=python-base /usr/share/tessdata_full /usr/share/tessdata_full
COPY --from=python-base ${PROJECT_PATH} ${PROJECT_PATH}
COPY . .


CMD [".venv/bin/python", "-m", "src.main"]
