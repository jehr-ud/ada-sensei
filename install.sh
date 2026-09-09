#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${ADA_SENSEI_REPO_URL:-https://github.com/jehr-ud/ada-sensei.git}"
BRANCH="${ADA_SENSEI_BRANCH:-main}"
VENV_DIR="${ADA_SENSEI_VENV:-.venv}"
NEW_VENV=false

if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  echo "error: Python 3.11+ is required" >&2
  exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
  "$PYTHON" -m venv "$VENV_DIR"
  NEW_VENV=true
fi

if [ "$NEW_VENV" = true ] || ! "$VENV_DIR/bin/pip" show ada-sensei >/dev/null 2>&1; then
  "$VENV_DIR/bin/pip" install --upgrade pip
  "$VENV_DIR/bin/pip" install "git+${REPO_URL}@${BRANCH}"
fi

echo "ADA Sensei installed. Verifying default LLM provisioning..."
"$VENV_DIR/bin/python" -c "
from ada_sensei.config import ConfigLoader
from ada_sensei.setup.provision import DefaultModelProvisioner
result = DefaultModelProvisioner(ConfigLoader().load()).provision_if_needed()
print('OK' if result.ok else 'FAILED: ' + (result.error or 'unknown'))
exit(0 if result.ok else 1)
"

echo "Done. Run: $VENV_DIR/bin/ada-sensei --help"