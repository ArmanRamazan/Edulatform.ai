# Build stage
FROM rust:1.88-slim AS builder
WORKDIR /app

COPY Cargo.toml Cargo.lock ./

# Create dummy main.rs to cache dependency compilation
RUN mkdir src && echo 'fn main() {}' > src/main.rs
RUN cargo build --release && rm -rf src

# Copy real source and rebuild (only changed files recompile)
COPY src/ src/
RUN touch src/main.rs && cargo build --release

# Runtime stage — minimal image without Rust toolchain
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y ca-certificates curl && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/target/release/embedding-orchestrator /usr/local/bin/

EXPOSE 8009
CMD ["embedding-orchestrator"]
