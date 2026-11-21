#!/usr/bin/env bash
# Push LeakFusion to a Hugging Face Docker Space (free CPU tier).
#
# Usage:   deploy/push_to_hf.sh <hf-username>/<space-name>
# Needs:   git, git-lfs, rsync, and a Hugging Face write token
#          (git will prompt: username = your HF username, password = the token).
#          The 5 model files must already be in leakfusion/models/.
set -euo pipefail

SPACE="${1:?usage: $0 <hf-username>/<space-name>}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -r "$WORK"' EXIT

for f in calibration.json cusum_config.json stage3_features_schema.json \
         stage3_severity_xgb.joblib stage3_zone_rf.joblib; do
  [[ -f "$REPO_ROOT/leakfusion/models/$f" ]] || {
    echo "Missing leakfusion/models/$f — download the models first (see README.md)." >&2
    exit 1
  }
done

echo "Cloning https://huggingface.co/spaces/$SPACE ..."
git clone "https://huggingface.co/spaces/$SPACE" "$WORK/space"
cd "$WORK/space"
git lfs install --local
git lfs track "*.joblib" "*.parquet"

# Mirror only what the container needs.
rsync -a --delete \
  --exclude '.git' --exclude '.gitattributes' \
  --exclude '__pycache__' --exclude 'node_modules' --exclude 'web/dist' \
  --exclude 'leakfusion/tests' --exclude 'leakfusion/data/*.parquet' \
  --include 'Dockerfile' --include '.dockerignore' --include 'requirements-api.txt' \
  --include 'leakfusion/***' --include 'web/***' \
  --include 'syn-engine/' --include 'syn-engine/src/***' \
  --exclude '*' \
  "$REPO_ROOT/" ./
cp "$REPO_ROOT/deploy/hf-space/README.md" ./README.md

git add -A
if git diff --cached --quiet; then
  echo "Nothing changed; Space is already up to date."
  exit 0
fi
git commit -m "Deploy LeakFusion $(cd "$REPO_ROOT" && git rev-parse --short HEAD)"
git push
echo "Pushed. Build logs: https://huggingface.co/spaces/$SPACE?logs=build"
