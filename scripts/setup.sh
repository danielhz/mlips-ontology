#!/bin/bash
set -e

# Install Rust toolchain (user-level)
if ! command -v cargo &> /dev/null; then
    echo "Installing Rust toolchain..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
fi

# Build
echo "Building onto-server..."
cargo build --release

echo ""
echo "Setup complete. Run with:"
echo "  ./target/release/onto-server"
