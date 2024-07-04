#!/bin/bash

# Define the regex pattern for the version format
version_pattern="^[0-9]+\.[0-9]+\.[0-9]+$"
release_pattern="^release[s]?/v.+"

# Determining if this is a release
target_name=$1
echo $target_name

if [[ $target_name =~ $release_pattern ]]; then
    is_release=true
else
    is_release=false
fi

# Gathering version sources
target_version=$(echo $target_name | cut -d 'v' -f 2);
echo $target_version

pyproject_version=$(grep 'version = ' pyproject.toml | cut -d '"' -f 2);
config_version=$(grep 'VERSION: str = ' app/config.py | cut -d '"' -f 2);

# Check if each version variable matches the pattern
if [[ $is_release = true && ! $target_version =~ $version_pattern ]]; then
    echo "target_version '$target_version' does not match the required format."
    exit 1
fi

if [[ ! $pyproject_version =~ $version_pattern ]]; then
    echo "pyproject_version '$pyproject_version'does not match the required format."
    exit 1
fi

if [[ ! $config_version =~ $version_pattern ]]; then
    echo "config_version '$config_version' does not match the required format."
    exit 1
fi

# Check if all versions are equivalent
if [[
    ( $pyproject_version != $config_version ) ||
    ( $is_release == true && ( $target_version != $pyproject_version || $target_version != $config_version ))
]]; then
    echo "Versions are not equivalent."
    exit 1
fi

# If all checks pass
echo "All versions are correctly formatted and equivalent."
exit 0
