# Build the pinned community sources: the historical public images are no longer pullable.
FROM golang:1.24-bookworm AS server-build
ENV GOFLAGS=-p=2 GOMEMLIMIT=512MiB
RUN git clone --depth 1 --branch RELEASE.2025-04-22T22-12-26Z https://github.com/minio/minio.git /src
WORKDIR /src
RUN test "$(git rev-parse HEAD)" = 0d7408fc9969caf07de6a8c3a84f9fbb10a6739e
RUN CGO_ENABLED=0 go build -trimpath -o /minio .

FROM golang:1.24-bookworm AS client-build
ENV GOFLAGS=-p=2 GOMEMLIMIT=512MiB
RUN git clone --depth 1 --branch RELEASE.2025-04-16T18-13-26Z https://github.com/minio/mc.git /src
WORKDIR /src
RUN test "$(git rev-parse HEAD)" = b00526b153a31b36767991a4f5ce2cced435ee8e
RUN CGO_ENABLED=0 go build -trimpath -o /mc .

FROM python:3.12-slim AS runtime
FROM runtime AS server
COPY --from=server-build /minio /usr/local/bin/minio
ENTRYPOINT ["minio"]
FROM runtime AS client
COPY --from=client-build /mc /usr/local/bin/mc
ENTRYPOINT ["mc"]
