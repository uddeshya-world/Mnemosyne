# eBPF Probe (Linux/WSL)

This directory contains an XDP program and a user-space loader built with Rust and Aya. `xdp_firewall` in `ebpf_program/src/main.rs` returns `XDP_PASS` for every packet. It does not read packet data and does not drop traffic.

## Prerequisites
*   **Linux Interface**: Real Linux kernel required (WSL2 or Native).
*   **Docker**: `Dockerfile` builds the loader. The root compose file does not start it.
*   **Privileges**: eBPF requires `sudo` or `--privileged`.

## How to run on Linux or WSL

The commands below are the steps previously written for a native Linux or WSL checkout. They were not re-run for the documentation cleanup.

1.  **Install Prerequisites**:
    ```bash
    sudo apt update
    sudo apt install -y llvm clang libclang-dev gcc-multilib build-essential git pkg-config libssl-dev
    ```

2.  **Install bpf-linker**:
    ```bash
    cargo install bpf-linker
    ```

3.  **Setup Rust Nightly**:
    ```bash
    rustup toolchain install nightly
    rustup target add bpfel-unknown-none --toolchain nightly
    rustup component add rust-src --toolchain nightly
    ```

4.  **Run the Loader**:
    ```bash
    # Build kernel (requires nightly)
    cargo +nightly build --package ebpf_program --target bpfel-unknown-none -Z build-std=core

    # Run user loader (needs sudo)
    sudo -E cargo run --package user_loader -- --iface eth0
    ```
    *(Note: `-E` preserves env vars if needed)*

## Docker

`Dockerfile` in this directory is a multi-stage build of `user_loader`. The root `docker-compose.yml` does not start that image. No Docker run steps are written down in this file.
