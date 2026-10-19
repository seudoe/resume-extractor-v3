#!/usr/bin/env bash
# Push a trimmed copy of the repo to one HF Space (created private if missing), then wait until it is healthy.
# usage: HF_USER=.. HF_TOKEN=.. HF_SPACE=.. scripts/deploy_hf_space.sh
set -euo pipefail
: "${HF_USER:?}" "${HF_TOKEN:?}" "${HF_SPACE:?}"
ID="$HF_USER/$HF_SPACE"
AUTH=(-H "Authorization: Bearer $HF_TOKEN")
SUB=$(echo "$HF_USER-$HF_SPACE" | tr 'A-Z_' 'a-z-')
URL="https://$SUB.hf.space"

# create (private, docker) if missing; 409 = already exists
code=$(curl -s -o /dev/null -w '%{http_code}' "${AUTH[@]}" -H 'content-type: application/json' \
  -d "{\"type\":\"space\",\"name\":\"$HF_SPACE\",\"sdk\":\"docker\",\"private\":true}" https://huggingface.co/api/repos/create)
[[ "$code" == 200 || "$code" == 409 ]] || { echo "create space failed: HTTP $code"; exit 1; }

# only what the Dockerfile COPYs, plus the Space README
T=$(mktemp -d)
cp Dockerfile pyproject.toml uv.lock "$T"/
cp -r src types scripts "$T"/
mkdir -p "$T/models" && cp -r models/adapters models/MODEL_CHECKSUMS.txt "$T/models"/
cp deploy/HF_SPACE_README.md "$T/README.md"
find "$T" -name __pycache__ -prune -exec rm -rf {} +
cd "$T"
git init -q -b main
git -c user.name=ci -c user.email=ci@users.noreply.github.com add -A
git -c user.name=ci -c user.email=ci@users.noreply.github.com commit -q -m "deploy ${GITHUB_SHA:-local}"
git push -q --force "https://$HF_USER:$HF_TOKEN@huggingface.co/spaces/$ID" HEAD:main

# wait for build + start: stage must leave RUNNING (or 2 min pass) and come back as RUNNING with /health ok
echo "pushed to $ID, waiting for $URL"
seen_build=0
for i in $(seq 1 180); do   # 30 min
  stage=$(curl -s "${AUTH[@]}" "https://huggingface.co/api/spaces/$ID/runtime" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("stage",""))' || true)
  [[ "$stage" == *BUILD* || "$stage" == APP_STARTING ]] && seen_build=1
  case "$stage" in *ERROR*|NO_APP_FILE|CONFIG_ERROR) echo "space stage: $stage"; exit 1;; esac
  if [[ "$stage" == RUNNING && ( $seen_build == 1 || $i -gt 12 ) ]]; then
    st=$(curl -s -m 10 "${AUTH[@]}" "$URL/health" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("status",""))' 2>/dev/null || true)
    [[ "$st" == ok ]] && { echo "healthy: $URL"; exit 0; }
  fi
  sleep 10
done
echo "timed out waiting for $URL (stage=$stage)"; exit 1
