#!/bin/sh
# Serve locally (fetch() of data/*.json doesn't work from file://)
cd "$(dirname "$0")" && echo "http://localhost:8000" && python3 -m http.server 8000
