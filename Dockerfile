# syntax=docker/dockerfile:1
# Multi-stage build: static musl binaries -> distroless. Target <= 30 MB, the
# same ceiling the server holds itself to, and the size gate in CI fails the
# job on a regression.
#
# `lto = "fat"` in the workspace profile is LOAD-BEARING for that ceiling, and
# is the reason this build is slow. Measured 2026-08-30 with nine engine
# adapters, tonic and the admin console in the binary: thin LTO produced
# 31.8 MB and failed the gate; fat produced 28.6 MB (munarium-matrix 22.5 ->
# ~20 MB, mxctl 7.2 -> ~6 MB, distroless base ~2 MB). Raising the ceiling was
# the alternative, and a ceiling that moves whenever it is reached is not a
# ceiling. `panic = "abort"` would save more and was rejected: a panic in one
# request would take the process down instead of the connection.
#
# Build context is matrix/. The build never needs a database: every sqlx query
# is a runtime-checked string (no `query!` macros), so there is no offline data
# and no prepare step — conformance against a real Postgres is the drift net.
#
# Cache mounts keep dependency artifacts across builds on one builder; the
# binaries are copied OUT of the mount inside the same RUN, because a cache
# mount is not part of the image.

FROM rust:1-alpine AS builder
RUN apk add --no-cache musl-dev \
 && rustup target add x86_64-unknown-linux-musl
WORKDIR /build
COPY . .
RUN --mount=type=cache,id=matrix-cargo-registry,target=/usr/local/cargo/registry \
    --mount=type=cache,id=matrix-cargo-git,target=/usr/local/cargo/git \
    --mount=type=cache,id=matrix-target,target=/build/target \
    cargo build --release --target x86_64-unknown-linux-musl \
        -p munarium-matrix-server -p munarium-matrix-cli \
 && mkdir -p /out \
 && cp target/x86_64-unknown-linux-musl/release/munarium-matrix \
       target/x86_64-unknown-linux-musl/release/mxctl /out/

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=builder /out/munarium-matrix /munarium-matrix
COPY --from=builder /out/mxctl /mxctl
USER nonroot
# 8180 REST + /docs + /openapi.json, 9190 ops/metrics.
# No clash with the server's 8080/50051/9090 or the demo BFF on one laptop.
EXPOSE 8180 9190 50151
ENTRYPOINT ["/munarium-matrix"]
