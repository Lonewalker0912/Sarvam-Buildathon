#!/usr/bin/env bash
# Deploy to a Hugging Face Space. Usage: ./deploy_hf.sh <hf-username>/<space-name>
# The Space needs a README with Space settings at the top, so we build a
# separate upload folder instead of changing the GitHub README.
set -euo pipefail
SPACE="${1:?Usage: ./deploy_hf.sh <hf-username>/<space-name>}"
HF=".venv/bin/hf"
OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT

cp app.py pipeline.py requirements.txt packages.txt "$OUT"/
cp -r docs "$OUT"/
{
  cat <<YAML
---
title: Generational Kitchen Wealth
emoji: 🍲
colorFrom: yellow
colorTo: red
sdk: gradio
sdk_version: $(.venv/bin/pip show gradio | awk '/^Version/{print $2}')
python_version: "3.12"
app_file: app.py
pinned: false
short_description: Family recipes, passed down in the voice that taught them
---

YAML
  cat README.md
} > "$OUT/README.md"

$HF repos create "$SPACE" --repo-type space --space-sdk gradio --exist-ok
$HF upload "$SPACE" "$OUT" . --repo-type space --commit-message "Deploy from GitHub $(git rev-parse --short HEAD)"
echo "Deployed: https://huggingface.co/spaces/$SPACE"
