#!/usr/bin/env bash
# Build and start Brown Creative Studio on the VPS. Run from the repository on
# the server, after `git pull`:
#
#   deploy/deploy.sh
#
# It refuses to deploy code that users could not get the source of (AGPL-3.0
# section 13): the working tree must be clean and the commit must already be on
# the public fork (the `origin` remote). Then it builds the images with that
# commit baked in, runs the deploy checks inside the new image, and only then
# replaces the running containers. See docs/fork/deployment.md.
set -euo pipefail

cd "$(dirname "$0")/.."

compose=(docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.studio.yml)

if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
    echo "deploy: refusing to deploy uncommitted changes; the Source code link could not show them." >&2
    git status --short --untracked-files=no >&2
    exit 1
fi

SOURCE_COMMIT="$(git rev-parse HEAD)"
export SOURCE_COMMIT

git fetch --quiet origin
if ! git branch --remotes --contains "$SOURCE_COMMIT" | grep -q '^ *origin/'; then
    echo "deploy: commit $SOURCE_COMMIT is not on the public fork yet. Push it first." >&2
    exit 1
fi

echo "deploy: building $SOURCE_COMMIT"
"${compose[@]}" build

echo "deploy: running deploy checks in the new image"
"${compose[@]}" run --rm --no-deps app python manage.py check --deploy --fail-level ERROR

echo "deploy: starting"
"${compose[@]}" up -d --remove-orphans
"${compose[@]}" ps
