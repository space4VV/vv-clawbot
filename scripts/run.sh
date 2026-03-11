#!/usr/bin/env bash
# Run vv-clawbot using uv.
set -e
cd "$(dirname "$0")/.."
exec uv run vv-clawbot
