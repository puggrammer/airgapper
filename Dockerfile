# =========================================================
# Stage 1: Builder Stage - Install dependencies and the local package
# This stage runs as root to handle installations easily and efficiently.
# =========================================================

FROM python:3.13-slim AS builder
WORKDIR /app

# Copy local source code and install package
COPY . /app
RUN pip install .


# =========================================================
# Stage 2: Runtime Stage - Minimal image for execution
# This stage runs securely as a non-root user.
# =========================================================

FROM python:3.13-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    maven \
    docker-cli \
    && rm -rf /var/lib/apt/lists/*

# Install Helm
RUN curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-4 | bash
RUN curl -L https://github.com/vmware-labs/distribution-tooling-for-helm/releases/download/v0.4.12/distribution-tooling-for-helm_0.4.12_linux_amd64.tar.gz -o dt.tar.gz \
    && tar -xzf dt.tar.gz \
    && mv dt /usr/local/bin/dt

# Add a non-root user AND create their home directory (-m flag)
# RUN useradd -m user

# Set the working directory and change ownership to new user
WORKDIR /app
# RUN chown -R user:user /app

# Switch to non-root user
# USER user

# Copy executables and libraries from the builder stage into the runtime stage
COPY --from=builder /usr/local/bin/airgapper /usr/local/bin/airgapper
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages

# Install airgapper
#COPY --chown=user:user . /app
#RUN pip install .

# Default entrypoint left blank so wrapper script controls execution
ENTRYPOINT []