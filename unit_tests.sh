#!/bin/bash
set -xeuo pipefail
pytest -sxv "$@"
