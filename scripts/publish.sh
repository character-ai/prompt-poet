#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e
set -o pipefail

SCRIPT_NAME=$0
DIRNAME=$(dirname $(realpath "$0"))
ROOT="${DIRNAME}/.."

(
    cd $ROOT
    source .pp/bin/activate

    # Check if the virtual environment is activated
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        echo "Virtual environment activated: $VIRTUAL_ENV"
    else
        echo "Failed to activate virtual environment"
        exit 1
    fi

    # Remove build artifacts if they exist on filesystem.
    rm -rf dist build *.egg-info

    # Bump the version
    python ./scripts/bump_version.py

    python -m build

    # Upload the package to PyPI
    twine upload dist/*
)
