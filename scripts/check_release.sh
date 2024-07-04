#!/bin/bash

# Define the regex pattern for the version format
version_pattern="^[0-9]+\.[0-9]+\.[0-9]+$"

# Gathering version sources
pyproject_version=$(grep 'version = ' pyproject.toml | cut -d '"' -f 2);
config_version=$(grep 'VERSION: str = ' app/config.py | cut -d '"' -f 2);

# Check if each version variable matches the pattern
if [[ ! $pyproject_version =~ $version_pattern ]]; then
    echo "pyproject_version '$pyproject_version'does not match the required format."
    exit 1
fi

if [[ ! $config_version =~ $version_pattern ]]; then
    echo "config_version '$config_version' does not match the required format."
    exit 1
fi

# Check if all versions are equivalent
if [[ $pyproject_version != $config_version ]]; then
    echo "Versions are not equivalent."
    exit 1
fi

# If all checks pass
echo "All versions are correctly formatted and equivalent."
exit 0
