# syntax=docker/dockerfile:1
# Multi-stage build: static musl binaries -> distroless, for linux/amd64 and
# linux/arm64. Target <= 30 MB, the same ceiling the server holds itself to,
# and the size gate in CI fails the job on a regression.
#
# `lto = "fat"` in the workspace profile is LOAD-BEARING for that ceiling, and
# is the reason this build is slow. Measured with the full adapter
# set, tonic and the admin console in the binary: thin LTO produced
# 31.8 MB and failed the gate; fat produced 28.6 MB (munarium-matrix 22.5 ->
# ~20 MB, mxctl 7.2 -> ~6 MB, distroless base ~2 MB). Raising the ceiling was
# the alternative, and a ceiling that moves whenever it is reached is not a
# ceiling. `panic = "abort"` would save more and was rejected: a panic in one
# request would take the process down instead of the connection.
#
# SPDX-License-Identifier: Apache-2.0
#
# Build context is the repository root. The build never needs a database:
# every sqlx query is a runtime-checked string (no `query!` macros), so there
# is no offline data and no prepare step — conformance against a real Postgres
# is the drift net.
#
# Both architectures compile on the BUILDER's CPU (tonistiigi/xx supplies the
# cross linker and target C libraries for aws-lc, ring and sqlite), the same
# recipe as the Munarium Server image, so an arm64 build needs no emulation
# for the compile. `xx-verify --static` proves each binary is static for the
# requested target. build.rs scripts run on the builder, which is why the
# vendored protoc needs nothing extra.
#
# Cache mounts keep dependency artifacts across builds on one builder, one
# target directory per architecture; the binaries are copied OUT of the mount
# inside the same RUN, because a cache mount is not part of the image.

# Include Cargo.lock from the source context in the dependency SBOM.
ARG BUILDKIT_SBOM_SCAN_CONTEXT=true
FROM --platform=$BUILDPLATFORM tonistiigi/xx:1.8.0@sha256:add602d55daca18914838a78221f6bbe4284114b452c86a48f96d59aeb00f5c6 AS cross
FROM --platform=$BUILDPLATFORM rust:1-alpine@sha256:a10e64dd139b7387337c7fbe8aca31b959b57b2fd4c8ae20a02cf1d6ea424dce AS builder
COPY --from=cross / /
# The toolchain the base image ships. Without it, rust-toolchain.toml's
# `stable` would have rustup fetch whatever stable is current at build time.
ENV RUSTUP_TOOLCHAIN=1.98.0
RUN apk add --no-cache musl-dev clang lld
WORKDIR /build
COPY . .
ARG TARGETARCH
ARG TARGETPLATFORM
ARG BUILDKIT_SBOM_SCAN_STAGE=true
RUN xx-apk add --no-cache musl-dev gcc
RUN --mount=type=cache,id=matrix-cargo-registry,target=/usr/local/cargo/registry \
    --mount=type=cache,id=matrix-cargo-git,target=/usr/local/cargo/git \
    --mount=type=cache,id=matrix-target-${TARGETARCH},target=/build/target \
    case "$TARGETARCH" in \
      amd64) target=x86_64-unknown-linux-musl ;; \
      arm64) target=aarch64-unknown-linux-musl ;; \
      *) echo "Unsupported architecture: $TARGETARCH" >&2; exit 1 ;; \
    esac \
 && xx-cargo build --locked --release \
        -p munarium-matrix-server -p munarium-matrix-cli \
 && mkdir -p /out \
 && cp "target/$target/release/munarium-matrix" \
       "target/$target/release/mxctl" /out/ \
 && xx-verify --static /out/munarium-matrix /out/mxctl

FROM gcr.io/distroless/static-debian12:nonroot@sha256:afa5c872c891853ca7fcf1f12c3edb23f7eeef36189728842dd51042ff57f7ab
ARG SOURCE_REVISION="unknown"
ARG BUILD_VERSION="1.2.0"
LABEL org.opencontainers.image.source="https://github.com/iokaio/munarium-matrix" \
      org.opencontainers.image.revision=$SOURCE_REVISION \
      org.opencontainers.image.version=$BUILD_VERSION \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.title="Munarium Matrix"
COPY --from=builder /out/munarium-matrix /munarium-matrix
COPY --from=builder /out/mxctl /mxctl
COPY LICENSE NOTICE THIRD_PARTY_NOTICES.md /usr/share/licenses/munarium-matrix/
USER nonroot
# 8180 REST + /docs + /openapi.json, 9190 ops/metrics, 50151 gRPC.
# No clash with the server's 8080/50051/9090 or the demo BFF on one laptop.
EXPOSE 8180 9190 50151
ENTRYPOINT ["/munarium-matrix"]
