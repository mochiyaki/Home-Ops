#!/usr/bin/env bash
set -euo pipefail

NODE_VERSION="22.16.0"
if ! command -v node >/dev/null 2>&1; then
  curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" | tar -xJ
  export PATH="$PWD/node-v${NODE_VERSION}-linux-x64/bin:$PATH"
fi

python -m pip install -r requirements.txt
cd frontend
npm ci
npm run build
