#!/bin/sh

# Tests to ensure we don't really break something:
# Oops we don't have any yet...

# pre-commit run --all --all-files || exit 1
# pytest || exit 1

umask 000
rm -rf build dist
git ls-tree --full-tree --name-only -r HEAD | xargs chmod ugo+r

uv build --sdist --wheel || exit 1

uv publish  || exit 1

VERSION=$(uv pip show django-find-view | grep 'Version: ' | cut -f 2 -d ' ' | tr -d '\n') || exit 1

git tag $VERSION || exit 1
git push || exit 1
git push --tags || exit 1
