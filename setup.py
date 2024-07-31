"""Setup file for the Prompt Poet (PP) package."""

import os

from setuptools import find_packages, setup

# Get the current directory of the setup.py script
here = os.path.abspath(os.path.dirname(__file__))

# Read the version from the VERSION file.
with open(os.path.join(here, "VERSION")) as version_file:
    version = version_file.read().strip()

setup(
    name="prompt_poet",
    version=version,
    packages=find_packages(include=["prompt_poet", "prompt_poet.*"]),
    include_package_data=True,
    package_data={"prompt_poet": ["examples/*.yml.j2"]},
    install_requires=[
        "jinja2>=3.0.0",
        "PyYaml>=6.0.0",
        "cachetools==5.3.3",
        "tiktoken==0.7.0",
    ],
    author="James Groeneveld",
    author_email="james@character.ai",
    description="Streamlines and simplifies prompt design for both developers and non-technical users with a low code approach.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/character-ai/prompt-poet",
    python_requires=">=3.10",
    license="MIT",
)
