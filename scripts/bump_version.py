"""Bump version of package."""

import os

# Get the current directory of the setup.py script
here = os.path.abspath(os.path.dirname(__file__))
root = os.path.normpath(os.path.join(here, ".."))


def bump_version(version: str) -> str:
    """Bump the patch version of the package."""
    major, minor, patch = map(int, version.split("."))
    patch += 1
    return f"{major}.{minor}.{patch}"


with open(os.path.join(root, "VERSION")) as version_file:
    current_version = version_file.read().strip()

new_version = bump_version(current_version)

with open(os.path.join(root, "VERSION"), "w") as version_file:
    version_file.write(new_version + "\n")

print(f"Bumped version from {current_version} to {new_version}")
