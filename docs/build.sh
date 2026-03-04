#!/bin/sh

mkdir build

touch build/.nojekyll  # Disable jekyll to keep files starting with underscores

uv run --group docs sphinx-build -b html ./api-docs ./build/api-docs
uv run --group docs sphinx-build -b html ./library-docs ./build/library-docs
