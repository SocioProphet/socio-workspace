#!/usr/bin/env bash
set -euo pipefail

REPO_NAME=${REPO_NAME:-socioprophet}
DEFAULT_BRANCH=${DEFAULT_BRANCH:-main}

if [ ! -d .git ]; then
  git init -b "$DEFAULT_BRANCH"
fi

git add -A
git commit -m "chore(init): SocioProphet monorepo skeleton"

echo "Initialized git repo. To add remote and push:"
echo "  git remote add origin git@github.com:<org-or-user>/${REPO_NAME}.git"
echo "  git push -u origin ${DEFAULT_BRANCH}"
