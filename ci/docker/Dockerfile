# Build from the repository root: docker build -f ci/docker/Dockerfile -t stm32-gdbtest-ci:local .
# BASE_IMAGE may point to a mirror of the same Ubuntu 24.04 image; the default is pinned by digest.
ARG BASE_IMAGE=ubuntu:24.04@sha256:008173c23f95b170204355c12626cb5a965d779a7e1283b09e9cffbb1bf33ca3
FROM ${BASE_IMAGE}

# OS packages receive Ubuntu updates; exact installed versions are recorded below.
RUN test "$(dpkg --print-architecture)" = amd64 \
    && apt-get -o Acquire::Retries=3 -o APT::Update::Error-Mode=any update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates clang-format curl git python3 unzip xz-utils libexpat1 libgmp10 \
    && rm -rf /var/lib/apt/lists/*

COPY ci/dependencies.lock.json /opt/stm32-gdbtest-ci/dependencies.lock.json
COPY ci/docker/install.py /opt/stm32-gdbtest-ci/install.py
RUN python3 /opt/stm32-gdbtest-ci/install.py archives
RUN python3 /opt/stm32-gdbtest-ci/install.py sources

COPY ci/docker/entrypoint.sh /usr/local/bin/stm32-gdbtest-env
COPY ci/docker/verify.py /opt/stm32-gdbtest-ci/verify.py
RUN chmod +x /usr/local/bin/stm32-gdbtest-env \
    && dpkg-query -W > /opt/stm32-gdbtest-ci/packages.txt

ENV STM32CUBE_REPOSITORY=/opt/STM32Cube/Repository \
    AT32_SDK_ROOT=/opt/Artery/AT32F403A_407_Firmware_Library_V2.0.9 \
    CHECK_SPEC=/opt/demo-stm32-skills/embedded-tech-spec/scripts/check_spec.py \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/stm32-gdbtest-env"]
CMD ["python3", "/opt/stm32-gdbtest-ci/verify.py"]

RUN /usr/local/bin/stm32-gdbtest-env python3 /opt/stm32-gdbtest-ci/verify.py
