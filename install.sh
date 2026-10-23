#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${ADA_SENSEI_REPO_URL:-https://github.com/jehr-ud/ada-sensei.git}"
BRANCH="${ADA_SENSEI_BRANCH:-main}"

INSTALL_DIR="${ADA_SENSEI_HOME:-$HOME/.local/share/ada-sensei}"
VENV_DIR="$INSTALL_DIR/venv"
BIN_DIR="$HOME/.local/bin"
LAUNCHER="$BIN_DIR/ada-sensei"

echo "Installing Ada-Sensei..."

# 1. Check dependencies
if ! command -v git >/dev/null 2>&1; then
    echo "Error: Git is required." >&2
    exit 1
fi

if command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
else
    echo "Error: Python 3.11+ is required." >&2
    exit 1
fi

"$PYTHON" -c '
import sys
if sys.version_info < (3, 11):
    raise SystemExit("Error: Python 3.11 or newer is required.")
'

# 2. Create a permanent virtual environment
mkdir -p "$INSTALL_DIR" "$BIN_DIR"

if [ ! -x "$VENV_DIR/bin/python" ]; then
    "$PYTHON" -m venv "$VENV_DIR"
fi

# 3. Install or update Ada-Sensei
"$VENV_DIR/bin/python" -m pip install --upgrade pip

"$VENV_DIR/bin/python" -m pip install --upgrade \
    "git+${REPO_URL}@${BRANCH}"

# 4. Verify the installed package resources
"$VENV_DIR/bin/python" - <<'PY'
from pathlib import Path
import ada_sensei

package_dir = Path(ada_sensei.__file__).parent
styles = package_dir / "cli" / "tui" / "styles.tcss"

if not styles.is_file():
    raise SystemExit(
        f"Installation error: missing UI stylesheet: {styles}\n"
        "Check the project's Python package configuration."
    )

print("UI resources verified.")
PY

# 5. Create a global command
cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
exec "$VENV_DIR/bin/ada-sensei" "\$@"
EOF

chmod +x "$LAUNCHER"

# 6. Add the command directory to PATH with priority
SHELL_NAME="$(basename "${SHELL:-bash}")"
case "$SHELL_NAME" in
    zsh)  PROFILE="$HOME/.zshrc" ;;
    bash) PROFILE="$HOME/.bashrc" ;;
    *)    PROFILE="" ;;
esac

if [ -n "$PROFILE" ]; then
    touch "$PROFILE"
    if ! grep -Fq 'export PATH="$HOME/.local/bin:$PATH"' "$PROFILE"; then
        printf '\nexport PATH="$HOME/.local/bin:$PATH"\n' >> "$PROFILE"
    fi
fi

# 7. Warn about other ada-sensei commands that would shadow this install
SHADOW=""
IFS=: read -r -a PATH_DIRS <<< "$PATH"
for DIR in "${PATH_DIRS[@]}"; do
    if [ "$DIR" = "$BIN_DIR" ]; then
        break
    fi
    if [ -x "$DIR/ada-sensei" ]; then
        SHADOW="$DIR/ada-sensei"
        break
    fi
done

if [ -n "$SHADOW" ]; then
    echo ""
    echo "Warning: another ada-sensei command found before $BIN_DIR:" >&2
    echo "  $SHADOW" >&2
    echo "It may be an outdated installation and cause runtime errors." >&2
    echo "Remove it or put $BIN_DIR first in your PATH." >&2
fi

echo ""
echo "Ada-Sensei installation completed."
echo "Command: $LAUNCHER"
echo "Restart your terminal or run:"
echo '  export PATH="$HOME/.local/bin:$PATH"'
echo ""
echo "Then run: ada-sensei"